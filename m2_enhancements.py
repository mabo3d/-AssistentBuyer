"""
M2.1 Release-Gate Enhancements.

SQLite-Schema (Pflichtspalten):
    materials: id, article_name, article_number, stock, min_stock, tray, compartment,
               depth_compartment, package_size, total_stock, manufacturer, manufacturer_name,
               manufacturer_article_number, model, supplier, mail_name, data_status,
               manufacturer_source, alternate_supplier, area, mail_ready, version
    purchase_orders: id, supplier, area, status, note, version, created_at, updated_at
    purchase_order_items: id, order_id, material_id, article_number, description,
                          mail_description, qty_ordered, qty_received, unit, status,
                          note, usage_after_receipt
    goods_receipts: id, order_item_id, quantity, usage_type, reference, note, received_at
    settings: key, value
    audit_log: id, event_type, entity_type, entity_id, message, payload_json, created_at
"""

import re
import sqlite3
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


REQUIRED_SCHEMA: dict[str, set[str]] = {
    "materials": {
        "id", "article_name", "article_number", "stock", "min_stock",
        "tray", "compartment", "depth_compartment", "package_size",
        "total_stock", "manufacturer", "manufacturer_name",
        "manufacturer_article_number", "model", "supplier",
        "mail_name", "data_status", "manufacturer_source",
        "alternate_supplier", "area", "mail_ready", "version",
    },
    "purchase_orders": {
        "id", "supplier", "area", "status", "note",
        "version", "created_at", "updated_at",
    },
    "purchase_order_items": {
        "id", "order_id", "material_id", "article_number", "description",
        "mail_description", "qty_ordered", "qty_received", "unit", "status",
        "note", "usage_after_receipt",
    },
    "goods_receipts": {
        "id", "order_item_id", "quantity", "usage_type",
        "reference", "note", "received_at",
    },
    "settings": {"key", "value"},
    "audit_log": {
        "id", "event_type", "entity_type", "entity_id",
        "message", "payload_json", "created_at",
    },
}


def _validate_database(path: Path, *, check_non_empty: bool) -> None:
    if not path.exists():
        raise RuntimeError(f"Datenbankdatei fehlt: {path}")
    if check_non_empty and path.stat().st_size == 0:
        raise RuntimeError(f"Datenbankdatei ist leer oder beschädigt: {path}")

    try:
        with sqlite3.connect(path) as conn:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            integrity_check_result = integrity[0] if integrity else "unbekannt"
            if integrity_check_result != "ok":
                raise RuntimeError(f"Datenbankintegrität beschädigt: {integrity_check_result}")

            existing_tables = {
                row[0]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            }
            missing_tables = sorted(set(REQUIRED_SCHEMA) - existing_tables)
            if missing_tables:
                raise RuntimeError(f"Erforderliche Tabellen fehlen: {missing_tables}")

            for table, required_columns in REQUIRED_SCHEMA.items():
                existing_columns = {
                    row[1]
                    for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()
                }
                missing_columns = sorted(required_columns - existing_columns)
                if missing_columns:
                    raise RuntimeError(
                        f"Erforderliche Spalten fehlen in Tabelle {table}: {missing_columns}"
                    )

            fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
            if fk_errors:
                raise RuntimeError(f"Foreign-Key-Fehler (Referenz-Integrität): {fk_errors}")
    except sqlite3.DatabaseError as exc:
        if "file is not a database" in str(exc).lower():
            raise RuntimeError(
                f"Datenbankdatei ist beschädigt oder kein SQLite-Format: {path}"
            ) from exc
        raise RuntimeError(f"Datenbankdatei ist beschädigt oder kein SQLite-Format: {path}") from exc


def validate_seed_database(path: Path) -> None:
    _validate_database(path, check_non_empty=False)


def validate_runtime_database(path: Path) -> None:
    _validate_database(path, check_non_empty=True)


def _norm_html_text(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split()).strip()


def _table_matches_expected_headers(table) -> bool:
    header_cells = []
    for row in table.find_all("tr", limit=2):
        header_cells.extend(row.find_all(["th", "td"]))
    headers = {_norm_html_text(cell.get_text(" ", strip=True)).lower() for cell in header_cells}
    return {
        "artikelnummer",
        "mindestbestand",
        "bestellt",
    }.issubset(headers)


def _find_expected_mp12n_table(soup: BeautifulSoup):
    table = soup.find("table", id="haeneltable")
    if table is not None:
        return table

    for candidate in soup.find_all("table"):
        if _table_matches_expected_headers(candidate):
            return candidate
    return None


def _detect_auth_markers(soup: BeautifulSoup, visible_text: str, final_url: str | None) -> list[str]:
    markers: list[str] = []

    if soup.select('input[type="password"]'):
        markers.append("password_input")

    for form in soup.find_all("form"):
        attrs = " ".join(
            " ".join(value) if isinstance(value, list) else str(value or "")
            for value in (form.get("id"), form.get("name"), form.get("action"), form.get("class"))
        ).lower()
        if re.search(r"(^|[^a-z0-9])(login|password|passwd|pin|kennwort|auth)([^a-z0-9]|$)", attrs):
            markers.append("auth_form")
            break

    strong_terms = {
        match.group(0)
        for match in re.finditer(
            r"\b(login|anmelden|authentifizierung|authentifizieren|passwort|kennwort|password|passwd)\b",
            visible_text,
        )
    }
    if strong_terms:
        markers.append("auth_text")

    pin_in_text = bool(re.search(r"\bpin\b", visible_text))
    if pin_in_text and ("password_input" in markers or "auth_form" in markers or strong_terms):
        markers.append("pin_text")

    parsed_final_url = (final_url or "").lower()
    if re.search(r"(^|[/?=&_-])(login|signin|auth|password|kennwort|passwd)([/?=&_.-]|$)", parsed_final_url):
        markers.append("login_redirect")

    return markers


def check_mp12n_response_validity(
    response_text: str,
    endpoint: str = "/info/article.mp",
    final_url: str | None = None,
) -> dict[str, Any]:
    """
    Prüfe MP12N-Response auf Gültigkeit.
    
    Erkennt Login/PIN-Seiten und ungültige Responses.
    
    Args:
        response_text: HTML-Response von MP12N
        endpoint: Der aufgerufene Endpoint (zur Diagnostik)
    
    Returns:
        {"status": "ok"|"auth_required"|"degraded", "reason": str}
    """
    soup = BeautifulSoup(response_text, "html.parser")
    title = _norm_html_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    visible_text = _norm_html_text(soup.get_text(" ", strip=True)).lower()
    tables = soup.find_all("table")
    expected_table = _find_expected_mp12n_table(soup)
    auth_markers = _detect_auth_markers(soup, visible_text, final_url)

    if expected_table is not None:
        reason = "MP12N-Artikeldatenstruktur erkannt"
        status = "ok"
    elif auth_markers:
        reason = "MP12N fordert Authentifizierung oder PIN an"
        status = "auth_required"
    else:
        reason = f"MP12N antwortet ohne erkennbare Artikeldatenstruktur für {endpoint}"
        status = "degraded"

    return {
        "status": status,
        "reason": reason,
        "title": title,
        "tableCount": len(tables),
        "hasExpectedTable": expected_table is not None,
        "authMarkers": auth_markers,
    }
