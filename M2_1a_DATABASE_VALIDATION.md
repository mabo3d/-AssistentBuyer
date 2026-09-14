# M2.1a – Database Validation

## Architektur: Was wird geprüft?

Die Validierung liegt vollständig in `m2_enhancements.py`:

- `validate_seed_database(path)`:
  - `PRAGMA integrity_check`
  - Tabellenprüfung: `materials`, `purchase_orders`, `purchase_order_items`, `goods_receipts`, `settings`, `audit_log`
  - Spaltenprüfung je Tabelle (Pflichtschema)
  - `PRAGMA foreign_key_check`
- `validate_runtime_database(path)`:
  - Alle Prüfungen wie Seed-Validierung
  - Zusätzlich Datei-Existenz und Leerdatei-Prüfung (`size == 0`)
  - Spezielle Fehlermeldung für SQLite-Fehler wie `file is not a database`

Integration in `app.py`:
- Seed-DB wird **vor** dem Kopieren validiert.
- Runtime-DB wird bei jedem Start validiert.
- Bei Fehlern: klare Meldung + `sys.exit(1)` (kein Weiterstart mit defekter DB).

## Test-Szenarien

1. **Seed fehlt**
   - Erwartung: `Seed-Datenbank fehlt: ...`
2. **Seed ist keine SQLite-Datei**
   - Erwartung: `Seed-Datenbankvalidierung fehlgeschlagen: Datenbankdatei ist beschädigt oder kein SQLite-Format: ...`
3. **Runtime-DB leer (0 Byte)**
   - Erwartung: `Datenbankvalidierung fehlgeschlagen: Datenbankdatei ist leer oder beschädigt: ...`
4. **Tabelle fehlt**
   - Erwartung: `Erforderliche Tabellen fehlen: [...]`
5. **Spalten fehlen**
   - Erwartung: `Erforderliche Spalten fehlen in Tabelle <table>: [...]`
6. **Integrität beschädigt**
   - Erwartung: `Datenbankintegrität beschädigt: <result>`
7. **Foreign-Key-Verletzungen**
   - Erwartung: `Foreign-Key-Fehler (Referenz-Integrität): [...]`

## Lokales Testen

1. App normal starten:
   - `python app.py`
2. Defektfall simulieren (Beispiel Runtime-DB):
   - Backup erstellen: `cp AssistentBuyer_Data/assistentbuyer.db /tmp/assistentbuyer.db.bak`
   - Datei beschädigen oder ersetzen (z. B. Textdatei mit `.db`-Endung)
   - App starten und Fehlermeldung prüfen
3. Nach Test Backup zurückkopieren.

Optional für Seed-Test:
- `data/assistentbuyer_seed.db` temporär sichern und durch ungültige Datei ersetzen.

## Rollback-Plan

1. Nur die M2.1a-Änderungen zurücknehmen (`app.py`, `m2_enhancements.py`, diese Doku-Datei).
2. Funktion prüfen:
   - Seed-DB wird wieder ohne Validierung kopiert
   - Startup läuft wieder mit altem Verhalten
3. Danach Root-Cause analysieren (welche Validierung war zu strikt) und angepasst neu ausrollen.
