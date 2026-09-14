# BUILD.md – Lokales Setup & Entwicklung

## Schnellstart

### Voraussetzungen
- **Python 3.9+** (Windows, macOS, Linux)
- **pip** (Python Package Manager)
- **Git**

### 1. Repository klonen
```bash
git clone https://github.com/mabo3d/AssistentBuyer.git
cd AssistentBuyer
```

### 2. Virtuelle Umgebung erstellen (optional, aber empfohlen)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Dependencies installieren
```bash
pip install -r requirements.txt
```

### 4. Lokale Konfiguration
```bash
# Kopiere .env.example zu .env
cp .env.example .env

# Bearbeite .env und setze mindestens:
# - MP12N_BASE_URL=http://[Hänel-IP]
# - DEFAULT_AREA=H oder E
```

### 5. App starten

**Lokal (nur auf diesem Rechner):**
```bash
python app.py
```
Browser öffnet automatisch: `http://127.0.0.1:8080`

**Im Netzwerk (LAN):**
```bash
python app.py --lan
```
Verfügbar unter: `http://[deine-IP]:8080`

**Mit Port-Option:**
```bash
python app.py --port 9000 --lan
```

---

## Entwicklung

### Struktur
```
AssistentBuyer/
├── app.py                      # FastAPI-Hauptdatei
├── static/
│   ├── index.html              # WebApp/PWA
│   ├── manifest.webmanifest    # PWA-Manifest
│   ├── sw.js                   # Service Worker
│   └── icon.svg                # App-Icon
├── data/
│   └── assistentbuyer_seed.db  # Seed-Datenbank (SQLite)
├── docs/                       # Dokumentation
├── requirements.txt            # Python-Dependencies
├── requirements-build.txt      # Build-Dependencies (PyInstaller)
└── .env.example                # Konfigurations-Template
```

### Datenbank

Die Seed-Datenbank wird beim ersten Start nach `AssistentBuyer_Data/` kopiert:

**Windows (portabel):**
- `AssistentBuyer_Data/assistentbuyer.db` (neben app.py oder EXE)
- oder: `%LOCALAPPDATA%/AssistentBuyer/assistentbuyer.db`

**Linux/macOS:**
- `~/.assistentbuyer/assistentbuyer.db`

**Umgebungsvariable überschreiben:**
```bash
set ASSISTENTBUYER_DATA_DIR=C:\mein\pfad  # Windows
export ASSISTENTBUYER_DATA_DIR=/pfad      # Linux/macOS
python app.py
```

### API-Endpoints (Entwicklung)

| Methode | Endpoint | Beschreibung |
|---------|----------|-------------|
| GET | `/api/app-info` | App-Version & Pfade |
| GET | `/api/dashboard` | Dashboard-Statistiken |
| GET | `/api/materials` | Materialstamm (mit Filter) |
| GET | `/api/materials/{id}` | Detail eines Materials |
| GET | `/api/suppliers` | Lieferanten-Liste |
| GET | `/api/orders` | Bestellungen (mit Filter) |
| POST | `/api/orders` | Neue Bestellung erstellen |
| GET | `/api/orders/{id}` | Bestelldetail |
| PATCH | `/api/orders/{id}` | Bestellung aktualisieren |
| POST | `/api/orders/{id}/receive` | Wareneingang buchen |
| GET | `/api/haenel/status` | MP12N-Verbindungsstatus |
| GET | `/api/haenel/order-recommendations` | Bestellvorschläge von MP12N |
| GET | `/api/settings` | Einstellungen auslesen |
| PATCH | `/api/settings` | Einstellungen speichern |
| GET | `/api/backup` | JSON-Backup der Daten |
| GET | `/api/history` | Audit-Log |

### Hänel/MP12N Read-Only

Die App liest **nur** von MP12N – schreibt **nicht**:
- ✅ Bestandsinformationen auslesen
- ✅ Bestellvorschläge abrufen
- ❌ Keine Liftbefehle
- ❌ Keine Bestandsänderungen

Wird über `/api/haenel/` bereitgestellt.

---

## Testing

### Simulator-Modus (ohne MP12N)

Wenn MP12N nicht erreichbar ist:
1. Setze in `.env`: `MP12N_BASE_URL=http://simulator`
2. App wird mit Demo-Daten laufen

### Manuelles Testen

```bash
# Dashboard
curl http://127.0.0.1:8080/api/dashboard

# Materialien
curl http://127.0.0.1:8080/api/materials?limit=10

# MP12N-Status
curl http://127.0.0.1:8080/api/haenel/status
```

---

## Windows-EXE bauen

Lokal mit PyInstaller:
```bash
pip install -r requirements-build.txt
python build_windows_exe.bat
```

Oder via GitHub Actions:
1. Push zu `main` Branch
2. GitHub → Actions → `Build Windows EXE` → `Run workflow`
3. Artifact `AssistentBuyer-Windows` herunterladen

---

## Troubleshooting

### Port 8080 bereits in Benutzung
```bash
python app.py --port 9000
```

### MP12N nicht erreichbar
1. Prüfe `.env`: Ist `MP12N_BASE_URL` korrekt?
2. Teste manuell: `curl http://[Hänel-IP]/info/article.mp`
3. Falls Firewall: Hänel-Port (meist 80 oder 443) freigeben

### Datenbank-Fehler
```
sqlite3.DatabaseError: file is not a database
```
Lösung:
1. `AssistentBuyer_Data/assistentbuyer.db` löschen
2. App neu starten → wird aus Seed neu erstellt

### Service Worker / PWA funktioniert nicht
1. Browser-Cache löschen
2. DevTools → Application → Storage → Clear site data
3. Seite neu laden (F5)

---

## Entwickler-Tipps

### Requirements aktualisieren
```bash
pip freeze > requirements.txt
```

### Nur Abhängigkeiten (ohne dev-Tools)
```bash
pip install -r requirements.txt
```

### Mit PyInstaller-Tools
```bash
pip install -r requirements-build.txt
```

### Logs prüfen (falls Backend läuft)
```bash
python app.py 2>&1 | tee app.log
```

---

## Next Steps

- **M2**: Projektstruktur bereinigen (optional)
- **M3**: FastAPI + SQLite stabilisieren
- **M4**: Materialstamm-Import validieren
- **M5**: Simulator + HaenelLiveAdapter
- **M6**: Frontend anbinden
- **M7**: Phase-0–6-Tests
