"""
M2.1 Release-Gate Enhancements
- SQLite Database Validation
- MP12N Robustness Check
"""

import sqlite3
from pathlib import Path


def validate_seed_database(seed_db_path: Path) -> None:
    """
    Vor Start: Seed-DB auf Integrität und erwartetes Schema prüfen.
    
    Raises:
        RuntimeError: Wenn DB fehlt, beschädigt ist oder Schema nicht vollständig
    """
    if not seed_db_path.exists():
        raise RuntimeError(f"Seed-Datenbank fehlt: {seed_db_path}")

    required_schema = {
        "materials": {
            "id", "article_name", "article_number", "stock", "min_stock",
            "tray", "compartment", "depth_compartment", "package_size",
            "total_stock", "manufacturer", "manufacturer_name",
            "manufacturer_article_number", "model", "supplier",
            "mail_name", "data_status", "manufacturer_source",
            "alternate_supplier", "area", "mail_ready", "version"
        },
        "purchase_orders": {
            "id", "supplier", "area", "status", "note",
            "version", "created_at", "updated_at"
        },
        "purchase_order_items": {
            "id", "order_id", "material_id", "article_number",
            "description", "mail_description", "qty_ordered",
            "qty_received", "unit", "status", "note",
            "usage_after_receipt"
        },
        "goods_receipts": {
            "id", "order_item_id", "quantity", "usage_type",
            "reference", "note", "received_at"
        },
        "settings": {
            "key", "value"
        },
        "audit_log": {
            "id", "event_type", "entity_type", "entity_id",
            "message", "payload_json", "created_at"
        },
    }

    try:
        with sqlite3.connect(seed_db_path) as conn:
            # Prüfe Integrität
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise RuntimeError(
                    f"Seed-DB beschädigt (Integrität): {integrity}"
                )

            # Prüfe Tabellen
            existing_tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }

            missing_tables = set(required_schema) - existing_tables
            if missing_tables:
                raise RuntimeError(
                    "Tabellen fehlen in Seed-DB: "
                    + ", ".join(sorted(missing_tables))
                )

            # Prüfe Spalten pro Tabelle
            for table, required_columns in required_schema.items():
                existing_columns = {
                    row[1]
                    for row in conn.execute(
                        f'PRAGMA table_info("{table}")'
                    ).fetchall()
                }

                missing_columns = required_columns - existing_columns
                if missing_columns:
                    raise RuntimeError(
                        f"Spalten fehlen in {table}: "
                        + ", ".join(sorted(missing_columns))
                    )

            # Prüfe Foreign Keys
            fk_errors = conn.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

            if fk_errors:
                raise RuntimeError(
                    f"Foreign-Key-Fehler in Seed-DB: {fk_errors[:10]}"
                )

    except sqlite3.DatabaseError as exc:
        raise RuntimeError(
            f"Seed-Datei ist keine gültige SQLite-Datenbank: {seed_db_path}"
        ) from exc


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
