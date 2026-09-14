# RELEASE.md – Release-Prozess & Checkliste für v1.0

## Release-Pipeline

```
Code → Git Push → GitHub Actions → Tests → PyInstaller → Artifact → Release
  ↓
main Branch (stable)
  ↓
Tests durchlaufen
  ↓
Python Dependencies OK
  ↓
Frontend/Backend paketiert
  ↓
Windows EXE gebaut
  ↓
Artifact verfügbar
```

---

## Release-Checkliste für v1.0

### Phase 0–6 Validierung

- [ ] **M1 – Release-Basis**
  - [x] Repository erstellt
  - [x] .gitignore, .env.example hinzugefügt
  - [x] Dokumentation (BUILD.md, ARCHITECTURE.md, MASTER.md)
  - [ ] Materialstamm-Seed-Daten importiert

- [ ] **M2 – Projektstruktur**
  - [ ] Optional: backend/, frontend/, data/ Reorganisierung
  - [ ] Code-Qualität geprüft
  - [ ] Kommentare aktualisiert

- [ ] **M3 – FastAPI + SQLite**
  - [ ] Datenbank-Schema verifiziert
  - [ ] Alle CRUD-Operationen getestet
  - [ ] Transaktionen OK (PRAGMA foreign_keys, busy_timeout)
  - [ ] Error-Handling komplett

- [ ] **M4 – Materialstamm-Import**
  - [ ] Excel-Import-Script funktioniert
  - [ ] Rohdaten → Normalized → Verified Ebenen OK
  - [ ] Bekannte Prüffälle (194123, 268367, 354978) markiert
  - [ ] 584 Positionen (438 H, 146 E) importiert

- [ ] **M5 – Simulator + Adapter**
  - [ ] SimulatorInventoryAdapter funktioniert
  - [ ] HaenelMP12NAdapter Read-Only verifiziert
  - [ ] Rohdaten-Format einheitlich
  - [ ] Cache-Strategie OK (MP12N: 5s)

- [ ] **M6 – Frontend-Integration**
  - [ ] Frontend ↔ Backend REST-API funktioniert
  - [ ] PWA-Manifest & Service Worker OK
  - [ ] Offline-Modus funktioniert (App-Shell)
  - [ ] Dashboard, Lager, Bestellen, WE, Verlauf, Einstellungen lauffähig

- [ ] **M7 – Phase-0–6-Gesamttest**
  - [ ] Bestandssuche (H/E-getrennt)
  - [ ] Bestellvorgänge erstellen & verwalten
  - [ ] Wareneingang erfassen
  - [ ] Hänel-Integration (Read-Only)
  - [ ] Backup/Export
  - [ ] Audit-Log
  - [ ] Alle Sonderfälle getestet

- [ ] **M8 – GitHub Actions + Build**
  - [ ] CI/CD Workflow läuft
  - [ ] Tests durchlaufen
  - [ ] PyInstaller-Build erfolgreich
  - [ ] Windows EXE funktioniert portabel

- [ ] **M9 – Release Candidate 1**
  - [ ] RC1 gebaut & getestet
  - [ ] Keine blockierenden Bugs
  - [ ] Dokumentation aktuell
  - [ ] Release-Notes vorbereitet

- [ ] **M10 – Regressionstest**
  - [ ] Alle Phase-0–6-Features nochmal durchlaufen
  - [ ] Edge Cases getestet
  - [ ] Performance OK
  - [ ] Keine Regressions

### Vor Release 1.0

**Code-Qualität:**
- [ ] Keine Secrets in Git
- [ ] `.env.example` aktuell
- [ ] `.gitignore` komplett
- [ ] Keine TODO/FIXME-Kommentare für Blockers
- [ ] Code-Review durchgeführt

**Funktionalität:**
- [ ] Alle Phase-0–6-Features funktionieren
- [ ] MP12N Read-Only verifiziert
- [ ] SQLite stabil (kein DatabaseError)
- [ ] PWA auf Windows/iPad lauffähig

**Dokumentation:**
- [ ] README.md aktuell
- [ ] BUILD.md aktuell
- [ ] ARCHITECTURE.md aktuell
- [ ] MASTER.md aktuell
- [ ] Inline-Code-Comments vorhanden

**Build & Deployment:**
- [ ] Windows EXE gebaut & getestet
- [ ] Portable Installation funktioniert
- [ ] GitHub Actions Workflow OK
- [ ] Release-Artifacts verfügbar

---

## Release-Prozess (Schritt für Schritt)

### 1. Vorbereitung

```bash
# Lokale Tests
python -m pytest tests/

# oder manuell
python app.py
# Browser: http://127.0.0.1:8080
```

### 2. Version aktualisieren

In `app.py`:
```python
APP_VERSION = "1.0.0"  # oder "1.0-RC1"
```

### 3. CHANGELOG & Release-Notes

Erstelle `docs/CHANGELOG.md`:
```markdown
## [1.0.0] – 2026-09-XX

### Added
- Materialstamm-Verwaltung (H/E-getrennt)
- Bestellverwaltung (Anfrage → Bestellung → WE)
- Hänel/MP12N Read-Only Integration
- PWA für Browser/Tablet
- Portable Windows-EXE
- Dashboard & Statistiken
- Audit-Log
- Backup/Export

### Fixed
- sqlite3.DatabaseError Fehler behoben
- MP12N Session-Handling verbessert

### Known Issues
- [Optional]: Bekannte limitierungen für v1.1

### Security
- Keine Secrets im Repository
- Credentials nur über .env
```

### 4. Commit & Tag

```bash
git add -A
git commit -m "Release v1.0.0 – Phase 0–6 abgeschlossen"
git tag -a v1.0.0 -m "AssistentBuyer v1.0.0 – Production Release"
git push origin main
git push origin v1.0.0
```

### 5. GitHub Actions – Windows-Build

1. GitHub → Actions → `Build Windows EXE`
2. `Run workflow` auf `main` Branch
3. Warten auf Completion
4. Artifact `AssistentBuyer-Windows` herunterladen

### 6. Artifact prüfen

```bash
# Artifact extrahieren
unzip AssistentBuyer-Windows.zip

# EXE testen
AssistentBuyer.exe
# → sollte App im Browser öffnen
```

### 7. GitHub Release erstellen

1. GitHub → Releases → `Create a new release`
2. Tag: `v1.0.0`
3. Title: `AssistentBuyer v1.0.0 – Release`
4. Description: Release-Notes (aus CHANGELOG)
5. Attach Artifact: `AssistentBuyer.exe`
6. `Publish release`

### 8. Kommunikation

- Projekt-Stakeholder informieren
- Release-Notes teilen
- Download-Link bereitstellen

---

## Versionierung

### Semantic Versioning (semver)

```
MAJOR.MINOR.PATCH
  1  .  0  .  0
```

- **MAJOR** (1.0 → 2.0): Breaking Changes
- **MINOR** (1.0 → 1.1): Neue Features, Bugfixes
- **PATCH** (1.0.0 → 1.0.1): Nur Bugfixes

### v1.0 Roadmap

| Version | Status | Fokus |
|---------|--------|-------|
| v1.0.0 | Release | Phase 0–6 komplett |
| v1.0.1 | Bugfix | Kleine Fehler (if needed) |
| v1.1.0 | Feature | SharePoint-Integration, erweiterte MP12N |
| v2.0.0 | Major | Schreibende MP12N, KI-Features |

---

## Post-Release

### Monitoring
- [ ] Benutzer-Feedback sammeln
- [ ] Fehler-Reports analysieren
- [ ] Performance-Metriken prüfen

### Patches (v1.0.1, v1.0.2, ...)
- Nur kritische Bugfixes
- Kein Scope-Creep
- Schnelle Release-Zyklen

### Nächste Major (v1.1, v2.0)
- Nach v1.0 stabilisiert
- New Scope eingefrorenes
- Same Release-Prozess

---

## Troubleshooting Release

### PyInstaller Fehler

```bash
# Clean rebuild
rm -rf dist/ build/ *.egg-info
pip install -r requirements-build.txt --force-reinstall
pyinstaller --onefile --windowed app.py
```

### GitHub Actions Fehler

Prüfe `.github/workflows/build-windows.yml`:
- Python Version OK?
- Dependencies korrekt?
- Build-Flags stimmen?

### Windows EXE läuft nicht

```bash
# Konsolen-Ausgabe sehen
AssistentBuyer.exe 2>&1
# oder: starte im Terminal, nicht per Doppelklick
```

---

## Release-Dokumente

Folgende Dateien sollten vor Release aktuell sein:

- ✅ `README.md` – Projekt-Übersicht
- ✅ `docs/MASTER.md` – Spezifikation
- ✅ `docs/BUILD.md` – Setup
- ✅ `docs/ARCHITECTURE.md` – Design
- ✅ `docs/CHANGELOG.md` – Release-Notes
- ✅ `docs/RELEASE.md` – Dieser Prozess

---

## Sign-off

Vor Release-Freigabe müssen folgende Punkte sign-off sein:

```
Release v1.0.0 Sign-Off

Code Quality:      ☐ OK
Functionality:     ☐ OK
Documentation:     ☐ OK
Build & Deploy:    ☐ OK
Phase-0–6-Test:    ☐ OK

Approved by: ________________
Date:        ________________
```

---

**Stand: 2026-09-14**
**Status: Release-Prozess definiert (M1 ✅)**
**Nächste Phase: M2 – Struktur bereinigen**
