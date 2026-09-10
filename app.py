from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import threading
import time
import uuid
import webbrowser
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
import uvicorn
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


APP_NAME = "AssistentBuyer"
APP_VERSION = "1.0"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def resource_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def executable_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def choose_data_dir() -> Path:
    override = os.getenv("ASSISTENTBUYER_DATA_DIR")
    if override:
        p = Path(override).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p

    # Portable, wenn der EXE-/Projektordner beschreibbar ist.
    candidate = executable_root() / "AssistentBuyer_Data"
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        probe = candidate / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return candidate
    except Exception:
        pass

    local = os.getenv("LOCALAPPDATA")
    if local:
        candidate = Path(local) / "AssistentBuyer"
    else:
        candidate = Path.home() / ".assistentbuyer"
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


RESOURCE_ROOT = resource_root()
STATIC_DIR = RESOURCE_ROOT / "static"
SEED_DB = RESOURCE_ROOT / "data" / "assistentbuyer_seed.db"
DATA_DIR = choose_data_dir()
DB_PATH = DATA_DIR / "assistentbuyer.db"

if not DB_PATH.exists():
    if not SEED_DB.exists():
        raise RuntimeError(f"Seed-Datenbank fehlt: {SEED_DB}")
    shutil.copy2(SEED_DB, DB_PATH)


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=10000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def setting(key: str, default: str = "") -> str:
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def audit(event_type: str, entity_type: str, entity_id: str | None, message: str, payload: Any = None):
    with db() as conn:
        conn.execute(
            """INSERT INTO audit_log(event_type,entity_type,entity_id,message,payload_json,created_at)
               VALUES(?,?,?,?,?,?)""",
            (event_type, entity_type, entity_id, message,
             json.dumps(payload, ensure_ascii=False) if payload is not None else None, now_iso()),
        )


# ---------------------------------------------------------------------
# MP12N: v1.0 bewusst READ ONLY
# ---------------------------------------------------------------------

MP_TIMEOUT = float(os.getenv("MP12N_TIMEOUT", "6"))
MP_CACHE_SECONDS = float(os.getenv("MP12N_CACHE_SECONDS", "5"))
_mp_cache: dict[str, tuple[float, Any]] = {}


def mp_session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.headers.update({
        "User-Agent": f"AssistentBuyer/{APP_VERSION} MP12N-ReadOnly",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    return s


def mp_get(session: requests.Session, path: str, params: dict[str, str] | None = None):
    base = setting("mp12n_base_url", "http://MP12N-IP").rstrip("/")
    url = urljoin(base + "/", path.lstrip("/"))
    try:
        r = session.get(url, params=params, timeout=MP_TIMEOUT, allow_redirects=True)
        r.raise_for_status()
        return r
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"MP12N nicht erreichbar: {exc}") from exc


def norm_text(v: str) -> str:
    return " ".join(v.replace("\xa0", " ").split()).strip()


def parse_recommendation_table(html: str) -> tuple[list[dict[str, str]], bool]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="haeneltable")
    if table is None:
        # Fallback: erste Tabelle mit den erwarteten Überschriften.
        for t in soup.find_all("table"):
            txt = norm_text(t.get_text(" ", strip=True)).lower()
            if "artikelnummer" in txt and "mindestbestand" in txt and "bestellt" in txt:
                table = t
                break
    if table is None:
        start = norm_text(soup.get_text(" ", strip=True))[:220]
        raise HTTPException(status_code=502, detail=f"Keine MP12N-Bestellvorschlagstabelle erkannt: {start!r}")

    items = []
    for row in table.find_all("tr"):
        cells = [norm_text(x.get_text(" ", strip=True)) for x in row.find_all("td")]
        if len(cells) < 5:
            continue
        # MP12N-Layouts enthalten je nach Version eine Auswahlspalte am Anfang.
        vals = cells[-5:]
        items.append({
            "articleNumber": vals[0],
            "description": vals[1],
            "minStock": vals[2],
            "totalStock": vals[3],
            "ordered": vals[4],
        })
    nxt = soup.find("a", href=lambda h: h and "order_recom_searchNext" in h)
    return items, bool(nxt)


def read_recommendations(status_filter: str = "all") -> dict[str, Any]:
    key = "recommendations:" + status_filter
    cached = _mp_cache.get(key)
    if cached and time.time() - cached[0] < MP_CACHE_SECONDS:
        return cached[1]

    s = mp_session()
    try:
        mp_get(s, "/")
    except HTTPException:
        pass
    r = mp_get(s, "/info/article.mp", {
        "orderrecomcombobox": "articlenumber",
        "orderrecomstatuscombobox": status_filter,
        "input": "?",
        "action": "order_recom_search",
    })
    items, has_next = parse_recommendation_table(r.text)
    pages = 1
    seen = {(x["articleNumber"], x["description"]) for x in items}

    while has_next and pages < 20:
        rr = mp_get(s, "/info/article.mp", {"action": "order_recom_searchNext"})
        page, has_next = parse_recommendation_table(rr.text)
        pages += 1
        for x in page:
            k = (x["articleNumber"], x["description"])
            if k not in seen:
                seen.add(k)
                items.append(x)

    result = {
        "source": setting("mp12n_base_url", ""),
        "mode": "READ_ONLY",
        "filter": status_filter,
        "count": len(items),
        "pagesRead": pages,
        "readAt": now_iso(),
        "items": items,
    }
    _mp_cache[key] = (time.time(), result)
    return result


# ---------------------------------------------------------------------
# API models
# ---------------------------------------------------------------------

class OrderItemIn(BaseModel):
    materialId: int
    quantity: float = Field(gt=0)
    unit: str = "Stk"


class OrderCreate(BaseModel):
    supplier: str | None = None
    area: str | None = None
    note: str | None = None
    items: list[OrderItemIn]


class OrderPatch(BaseModel):
    version: int
    status: str | None = None
    note: str | None = None


class ReceiptItem(BaseModel):
    orderItemId: int
    quantity: float = Field(gt=0)
    usageType: str = "eingelagert"
    reference: str | None = None
    note: str | None = None


class ReceiptCreate(BaseModel):
    items: list[ReceiptItem]


class SettingPatch(BaseModel):
    mp12nBaseUrl: str | None = None
    defaultArea: str | None = None


# ---------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------

app = FastAPI(title=APP_NAME, version=APP_VERSION)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    return FileResponse(STATIC_DIR / "sw.js", media_type="application/javascript")


@app.get("/icon.svg")
def icon():
    return FileResponse(STATIC_DIR / "icon.svg", media_type="image/svg+xml")


@app.get("/api/app-info")
def app_info():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "dataDir": str(DATA_DIR),
        "database": str(DB_PATH),
        "mp12nMode": setting("mp12n_mode", "READ_ONLY"),
    }


@app.get("/api/dashboard")
def dashboard(area: str | None = Query(None, pattern="^(H|E)?$")):
    where = ""
    args: list[Any] = []
    if area:
        where = " WHERE area=?"
        args.append(area)
    with db() as conn:
        material_count = conn.execute(f"SELECT COUNT(*) c FROM materials{where}", args).fetchone()["c"]
        if area:
            below = conn.execute(
                """SELECT COUNT(*) c FROM materials
                   WHERE area=? AND total_stock IS NOT NULL AND min_stock IS NOT NULL
                     AND total_stock < min_stock""", (area,)
            ).fetchone()["c"]
            mail_ready = conn.execute(
                "SELECT COUNT(*) c FROM materials WHERE area=? AND mail_ready=1", (area,)
            ).fetchone()["c"]
        else:
            below = conn.execute(
                """SELECT COUNT(*) c FROM materials
                   WHERE total_stock IS NOT NULL AND min_stock IS NOT NULL
                     AND total_stock < min_stock"""
            ).fetchone()["c"]
            mail_ready = conn.execute("SELECT COUNT(*) c FROM materials WHERE mail_ready=1").fetchone()["c"]

        open_orders = conn.execute(
            "SELECT COUNT(*) c FROM purchase_orders WHERE status NOT IN ('Geliefert','Storniert')"
            + (" AND area=?" if area else ""),
            ((area,) if area else ()),
        ).fetchone()["c"]

        open_items = conn.execute(
            """SELECT COUNT(*) c FROM purchase_order_items i
               JOIN purchase_orders o ON o.id=i.order_id
               WHERE i.qty_received < i.qty_ordered"""
            + (" AND o.area=?" if area else ""),
            ((area,) if area else ()),
        ).fetchone()["c"]

    return {
        "area": area,
        "materials": material_count,
        "belowMinFallback": below,
        "mailReady": mail_ready,
        "openOrders": open_orders,
        "openDeliveryItems": open_items,
    }


@app.get("/api/materials")
def materials(
    q: str = "",
    area: str | None = Query(None, pattern="^(H|E)?$"),
    belowMin: bool = False,
    supplier: str | None = None,
    limit: int = Query(100, ge=1, le=600),
    offset: int = Query(0, ge=0),
):
    clauses = []
    args: list[Any] = []
    if area:
        clauses.append("area=?")
        args.append(area)
    if belowMin:
        clauses.append("total_stock IS NOT NULL AND min_stock IS NOT NULL AND total_stock < min_stock")
    if supplier:
        clauses.append("supplier=?")
        args.append(supplier)
    if q.strip():
        like = f"%{q.strip()}%"
        clauses.append("""(
            article_name LIKE ? OR article_number LIKE ? OR manufacturer LIKE ?
            OR manufacturer_name LIKE ? OR manufacturer_article_number LIKE ?
            OR supplier LIKE ? OR mail_name LIKE ?
        )""")
        args.extend([like] * 7)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    with db() as conn:
        total = conn.execute(f"SELECT COUNT(*) c FROM materials{where}", args).fetchone()["c"]
        result = conn.execute(
            f"""SELECT id,article_name,article_number,stock,min_stock,tray,compartment,depth_compartment,
                       package_size,total_stock,manufacturer,manufacturer_name,manufacturer_article_number,
                       model,supplier,mail_name,data_status,manufacturer_source,alternate_supplier,area,
                       mail_ready,version
                FROM materials{where}
                ORDER BY article_name COLLATE NOCASE
                LIMIT ? OFFSET ?""",
            args + [limit, offset],
        ).fetchall()

    items = []
    for r in result:
        d = dict(r)
        d["belowMin"] = (
            d["total_stock"] is not None and d["min_stock"] is not None
            and float(d["total_stock"]) < float(d["min_stock"])
        )
        items.append(d)
    return {"count": total, "items": items}


@app.get("/api/materials/{material_id}")
def material(material_id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Material nicht gefunden")
        return dict(row)


@app.get("/api/suppliers")
def suppliers(area: str | None = Query(None, pattern="^(H|E)?$")):
    with db() as conn:
        rows = conn.execute(
            """SELECT supplier,COUNT(*) c FROM materials
               WHERE supplier IS NOT NULL AND TRIM(supplier)<>''"""
            + (" AND area=?" if area else "")
            + " GROUP BY supplier ORDER BY supplier",
            ((area,) if area else ()),
        ).fetchall()
    return [{"supplier": r["supplier"], "count": r["c"]} for r in rows]


def recalc_order(conn: sqlite3.Connection, order_id: str):
    items = conn.execute(
        "SELECT id,qty_ordered,qty_received FROM purchase_order_items WHERE order_id=?", (order_id,)
    ).fetchall()
    if not items:
        status = "Offen"
    else:
        delivered = sum(1 for i in items if i["qty_received"] >= i["qty_ordered"])
        partial = any(i["qty_received"] > 0 for i in items)
        if delivered == len(items):
            status = "Geliefert"
        elif partial:
            status = "Teilgeliefert"
        else:
            status = "Bestellt"
    conn.execute(
        "UPDATE purchase_orders SET status=?,updated_at=?,version=version+1 WHERE id=?",
        (status, now_iso(), order_id),
    )


@app.post("/api/orders")
def create_order(payload: OrderCreate):
    if not payload.items:
        raise HTTPException(400, "Mindestens eine Bestellposition erforderlich")
    order_id = "AB-" + datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()
    created = now_iso()

    with db() as conn:
        mat_ids = [x.materialId for x in payload.items]
        placeholders = ",".join("?" for _ in mat_ids)
        mats = {
            r["id"]: r for r in conn.execute(
                f"SELECT * FROM materials WHERE id IN ({placeholders})", mat_ids
            ).fetchall()
        }
        missing = [x.materialId for x in payload.items if x.materialId not in mats]
        if missing:
            raise HTTPException(400, f"Unbekannte Material-IDs: {missing}")

        suppliers = {mats[x.materialId]["supplier"] for x in payload.items if mats[x.materialId]["supplier"]}
        supplier = payload.supplier or (next(iter(suppliers)) if len(suppliers) == 1 else None)
        areas = {mats[x.materialId]["area"] for x in payload.items}
        area = payload.area or (next(iter(areas)) if len(areas) == 1 else None)

        conn.execute(
            """INSERT INTO purchase_orders(id,supplier,area,status,note,version,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (order_id, supplier, area, "Bestellt", payload.note, 1, created, created),
        )
        for item in payload.items:
            m = mats[item.materialId]
            conn.execute(
                """INSERT INTO purchase_order_items(
                     order_id,material_id,article_number,description,mail_description,
                     qty_ordered,qty_received,unit,status,note
                   ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    order_id, item.materialId, m["article_number"], m["article_name"], m["mail_name"],
                    item.quantity, 0, item.unit, "Offen", None
                ),
            )

    audit("CREATE", "purchase_order", order_id, "Bestellvorgang angelegt", payload.model_dump())
    return {"id": order_id, "status": "Bestellt"}


@app.get("/api/orders")
def list_orders(
    area: str | None = Query(None, pattern="^(H|E)?$"),
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
):
    clauses = []
    args: list[Any] = []
    if area:
        clauses.append("o.area=?")
        args.append(area)
    if status:
        clauses.append("o.status=?")
        args.append(status)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with db() as conn:
        rows = conn.execute(
            f"""SELECT o.*,
                       COUNT(i.id) AS item_count,
                       COALESCE(SUM(i.qty_ordered),0) AS qty_ordered,
                       COALESCE(SUM(i.qty_received),0) AS qty_received
                FROM purchase_orders o
                LEFT JOIN purchase_order_items i ON i.order_id=o.id
                {where}
                GROUP BY o.id
                ORDER BY o.created_at DESC
                LIMIT ?""",
            args + [limit],
        ).fetchall()
    return [dict(x) for x in rows]


@app.get("/api/orders/{order_id}")
def get_order(order_id: str):
    with db() as conn:
        order = conn.execute("SELECT * FROM purchase_orders WHERE id=?", (order_id,)).fetchone()
        if not order:
            raise HTTPException(404, "Bestellung nicht gefunden")
        items = conn.execute(
            """SELECT i.*,m.tray,m.compartment,m.depth_compartment,m.area,m.supplier
               FROM purchase_order_items i
               LEFT JOIN materials m ON m.id=i.material_id
               WHERE i.order_id=? ORDER BY i.id""",
            (order_id,),
        ).fetchall()
        receipts = conn.execute(
            """SELECT g.* FROM goods_receipts g
               JOIN purchase_order_items i ON i.id=g.order_item_id
               WHERE i.order_id=? ORDER BY g.received_at DESC""", (order_id,)
        ).fetchall()
    return {"order": dict(order), "items": [dict(x) for x in items], "receipts": [dict(x) for x in receipts]}


@app.patch("/api/orders/{order_id}")
def patch_order(order_id: str, payload: OrderPatch):
    with db() as conn:
        current = conn.execute("SELECT * FROM purchase_orders WHERE id=?", (order_id,)).fetchone()
        if not current:
            raise HTTPException(404, "Bestellung nicht gefunden")
        if current["version"] != payload.version:
            raise HTTPException(409, "Der Vorgang wurde zwischenzeitlich geändert. Bitte neu laden.")
        status = payload.status if payload.status is not None else current["status"]
        note = payload.note if payload.note is not None else current["note"]
        conn.execute(
            """UPDATE purchase_orders
               SET status=?,note=?,updated_at=?,version=version+1
               WHERE id=? AND version=?""",
            (status, note, now_iso(), order_id, payload.version),
        )
    audit("UPDATE", "purchase_order", order_id, "Bestellvorgang geändert", payload.model_dump())
    return {"ok": True}


@app.post("/api/orders/{order_id}/receive")
def receive(order_id: str, payload: ReceiptCreate):
    if not payload.items:
        raise HTTPException(400, "Keine Wareneingangspositionen angegeben")
    received_at = now_iso()
    with db() as conn:
        order = conn.execute("SELECT id FROM purchase_orders WHERE id=?", (order_id,)).fetchone()
        if not order:
            raise HTTPException(404, "Bestellung nicht gefunden")

        for rec in payload.items:
            item = conn.execute(
                "SELECT * FROM purchase_order_items WHERE id=? AND order_id=?",
                (rec.orderItemId, order_id),
            ).fetchone()
            if not item:
                raise HTTPException(400, f"Bestellposition {rec.orderItemId} nicht gefunden")
            open_qty = max(0.0, float(item["qty_ordered"]) - float(item["qty_received"]))
            if rec.quantity > open_qty + 1e-9:
                raise HTTPException(
                    400,
                    f"Menge für Position {rec.orderItemId} überschreitet offene Menge {open_qty:g}",
                )

            conn.execute(
                """INSERT INTO goods_receipts(order_item_id,quantity,usage_type,reference,note,received_at)
                   VALUES(?,?,?,?,?,?)""",
                (rec.orderItemId, rec.quantity, rec.usageType, rec.reference, rec.note, received_at),
            )
            new_received = float(item["qty_received"]) + rec.quantity
            new_status = "Geliefert" if new_received >= float(item["qty_ordered"]) else "Teilgeliefert"
            conn.execute(
                """UPDATE purchase_order_items
                   SET qty_received=?,status=?,usage_after_receipt=?
                   WHERE id=?""",
                (new_received, new_status, rec.usageType, rec.orderItemId),
            )

        recalc_order(conn, order_id)

    audit("RECEIPT", "purchase_order", order_id, "Wareneingang gebucht", payload.model_dump())
    return {"ok": True, "receivedAt": received_at}


@app.get("/api/orders/{order_id}/draft")
def order_draft(order_id: str):
    data = get_order(order_id)
    order = data["order"]
    items = data["items"]
    blocked = [x for x in items if not (x.get("mail_description") or "").strip()]
    lines = []
    if blocked:
        return {
            "ready": False,
            "blockedItems": [
                {"articleNumber": x["article_number"], "description": x["description"]} for x in blocked
            ],
            "text": "",
        }
    lines.append(f"Bestellung {order_id}")
    if order.get("supplier"):
        lines.append(f"Lieferant: {order['supplier']}")
    lines.append("")
    for x in items:
        lines.append(f"{x['qty_ordered']:g} {x['unit']}  {x['mail_description']}  [{x['article_number'] or '-'}]")
    return {"ready": True, "blockedItems": [], "text": "\n".join(lines)}


@app.get("/api/history")
def history(limit: int = Query(100, ge=1, le=500)):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(x) for x in rows]


@app.get("/api/haenel/status")
def haenel_status():
    started = time.perf_counter()
    s = mp_session()
    try:
        r = mp_get(s, "/info/article.mp")
        return {
            "bridge": "ok", "mode": "READ_ONLY", "mp12n": "reachable",
            "baseUrl": setting("mp12n_base_url", ""),
            "httpStatus": r.status_code,
            "latencyMs": round((time.perf_counter() - started) * 1000),
        }
    except HTTPException as exc:
        return {
            "bridge": "ok", "mode": "READ_ONLY", "mp12n": "unreachable",
            "baseUrl": setting("mp12n_base_url", ""), "detail": exc.detail,
        }


@app.get("/api/haenel/order-recommendations")
def haenel_recommendations(
    status: str = Query("all", pattern="^(all|notordered)$")
):
    return read_recommendations(status)


@app.get("/api/haenel/order-summary")
def haenel_summary():
    result = read_recommendations("all")
    ordered = sum(1 for x in result["items"] if x["ordered"].strip().lower() == "ja")
    return {
        "total": result["count"],
        "ordered": ordered,
        "notOrdered": result["count"] - ordered,
        "readAt": result["readAt"],
        "source": result["source"],
    }


@app.get("/api/settings")
def get_settings():
    return {
        "mp12nBaseUrl": setting("mp12n_base_url", "http://MP12N-IP"),
        "mp12nMode": setting("mp12n_mode", "READ_ONLY"),
        "defaultArea": setting("default_area", "H"),
    }


@app.patch("/api/settings")
def patch_settings(payload: SettingPatch):
    with db() as conn:
        if payload.mp12nBaseUrl is not None:
            v = payload.mp12nBaseUrl.strip().rstrip("/")
            if not (v.startswith("http://") or v.startswith("https://")):
                raise HTTPException(400, "MP12N-Adresse muss mit http:// oder https:// beginnen")
            conn.execute(
                "INSERT INTO settings(key,value) VALUES('mp12n_base_url',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (v,)
            )
        if payload.defaultArea is not None:
            if payload.defaultArea not in ("H", "E"):
                raise HTTPException(400, "Bereich muss H oder E sein")
            conn.execute(
                "INSERT INTO settings(key,value) VALUES('default_area',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (payload.defaultArea,)
            )
    _mp_cache.clear()
    audit("UPDATE", "settings", None, "Einstellungen geändert", payload.model_dump())
    return {"ok": True}


@app.get("/api/backup")
def backup():
    with db() as conn:
        materials = [dict(r) for r in conn.execute("SELECT * FROM materials ORDER BY id")]
        orders = [dict(r) for r in conn.execute("SELECT * FROM purchase_orders ORDER BY created_at")]
        items = [dict(r) for r in conn.execute("SELECT * FROM purchase_order_items ORDER BY id")]
        receipts = [dict(r) for r in conn.execute("SELECT * FROM goods_receipts ORDER BY id")]
        settings_rows = {r["key"]: r["value"] for r in conn.execute("SELECT * FROM settings")}
    payload = {
        "schema": "assistentbuyer-backup-v1",
        "createdAt": now_iso(),
        "appVersion": APP_VERSION,
        "materials": materials,
        "orders": orders,
        "orderItems": items,
        "goodsReceipts": receipts,
        "settings": settings_rows,
    }
    return JSONResponse(
        payload,
        headers={"Content-Disposition": f'attachment; filename="AssistentBuyer_Backup_{datetime.now():%Y%m%d_%H%M}.json"'},
    )


def run():
    parser = argparse.ArgumentParser(description="AssistentBuyer v1.0")
    parser.add_argument("--lan", action="store_true", help="Im lokalen Netz auf 0.0.0.0 bereitstellen")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    host = args.host or ("0.0.0.0" if args.lan else "127.0.0.1")
    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")).start()

    print(f"{APP_NAME} v{APP_VERSION}")
    print(f"Daten: {DATA_DIR}")
    print(f"MP12N: {setting('mp12n_base_url', '')} [READ ONLY]")
    print(f"Web: http://127.0.0.1:{args.port}")
    if args.lan:
        print("LAN-Modus aktiv. Windows-Firewall/Firmenrichtlinien können eingehende Verbindungen blockieren.")
    uvicorn.run(app, host=host, port=args.port, log_level="warning")


if __name__ == "__main__":
    run()
