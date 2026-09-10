# AssistentBuyer v1.0 – GitHub Build

Diese Build-Version enthält keine Firmen-Stammdaten.

Enthalten:
- FastAPI-Backend
- WebApp/PWA
- leere SQLite-Seed-Datenbank
- MP12N-Read-only-Connector
- GitHub-Actions-Workflow für die Windows-EXE

Nicht enthalten:
- Materialstamm
- Bestellungen / Wareneingänge
- Snapshots / HAR-Dateien
- interne Dokumentation
- interne IP-Adressen

Die MP12N-Adresse wird erst lokal nach dem Build konfiguriert.

## Windows-EXE bauen
GitHub → Actions → `Build Windows EXE` → `Run workflow`.

Danach steht unter **Artifacts** die Datei `AssistentBuyer-Windows`
mit der erzeugten `AssistentBuyer.exe` bereit.
