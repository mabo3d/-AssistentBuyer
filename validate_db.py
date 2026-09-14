def validate_seed_database():
    """Vor Start: Seed-DB auf Integrität und erwartetes Schema prüfen."""
    if not SEED_DB.exists():
        raise RuntimeError(f"Seed-Datenbank fehlt: {SEED_DB}")

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
        with sqlite3.connect(SEED_DB) as conn:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise RuntimeError(
                    f"Seed-DB beschädigt: {integrity}"
                )

            existing_tables = {
                row[0]
                for row in conn.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type='table'
                    """
                ).fetchall()
            }

            missing_tables = set(required_schema) - existing_tables
            if missing_tables:
                raise RuntimeError(
                    "Tabellen fehlen in Seed-DB: "
                    + ", ".join(sorted(missing_tables))
                )

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

            fk_errors = conn.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

            if fk_errors:
                raise RuntimeError(
                    f"Foreign-Key-Fehler in Seed-DB: {fk_errors[:10]}"
                )

    except sqlite3.DatabaseError as exc:
        raise RuntimeError(
            f"Seed-Datei ist keine gültige SQLite-Datenbank: {SEED_DB}"
        ) from exc
