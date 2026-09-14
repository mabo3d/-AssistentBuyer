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

import sqlite3
from pathlib import Path


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


def check_mp12n_response_validity(response_text: str, endpoint: str = "/info/article.mp") -> dict[str, str | bool]:
    """
    Prüfe MP12N-Response auf Gültigkeit.
    
    Erkennt Login/PIN-Seiten und ungültige Responses.
    
    Args:
        response_text: HTML-Response von MP12N
        endpoint: Der aufgerufene Endpoint (zur Diagnostik)
    
    Returns:
        {"status": "ok"|"login_required"|"invalid", "detail": str}
    """
    text_lower = response_text.lower()
    
    # Erkenne Login/PIN-Seiten
    login_indicators = ["login", "pin", "authentifizierung", "anmelden", "password"]
    if any(indicator in text_lower for indicator in login_indicators):
        return {
            "status": "login_required",
            "detail": "MP12N fordert Authentifizierung an (Login/PIN-Seite erkannt)"
        }
    
    # Erkenne fehlende Daten
    data_indicators = ["haeneltable", "artikelnummer", "bestellvorschlag"]
    if not any(indicator in text_lower for indicator in data_indicators):
        return {
            "status": "invalid",
            "detail": f"MP12N antwortet ohne erwartete Daten (kein {endpoint})"
        }
    
    return {
        "status": "ok",
        "detail": "Response ist gültig"
    }
