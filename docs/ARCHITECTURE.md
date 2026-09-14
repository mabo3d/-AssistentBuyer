# ARCHITECTURE.md – System-Design & Komponenten

## Überblick

AssistentBuyer v1.0 ist eine modulare PWA/Desktop-App für Werkstatt-Lager- und Bestellverwaltung mit Hänel/MP12N-Integration.

```
┌─────────────────────────────────────────────────────────┐
│  Browser / PWA (HTML5/CSS3/Vanilla JS/Service Worker)   │
└─────────────────┬───────────────────────────────────────┘
                  │ HTTP REST API
                  ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI Backend (Python)                               │
│  ├── /api/materials        (Materialstamm)              │
│  ├── /api/orders           (Bestellverwaltung)          │
│  ├── /api/haenel           (MP12N Read-Only)            │
│  ├── /api/settings         (Konfiguration)              │
│  └── /api/history          (Audit-Log)                  │
└─────────────────┬───────────────────────────────────────┘
                  │
        ┌─────────┴──────────┬────────────────────┐
        ▼                    ▼                    ▼
    ┌────────┐          ┌──────────┐         ┌─────────┐
    │ SQLite │          │ MP12N    │         │SharePoint│
    │ lokal  │          │ Hänel    │         │(später)  │
    │        │          │ (Read-O) │         │          │
    └────────┘          └──────────┘         └─────────┘
```

---

## Frontend

### Technologie
- **HTML5** + **CSS3** + **Vanilla JavaScript** (ES Modules)
- **PWA** (Progressive Web App)
- **Service Worker** (offline-first, Cache-Strategie)
- Keine schweren Frameworks (React/Vue) für v1.0 – klare Anforderung

### Dateistruktur
```
static/
├── index.html              # SPA-Einstiegspunkt
├── manifest.webmanifest    # PWA-Manifest (Icons, Theme)
├── sw.js                   # Service Worker (Cache-Strategie)
├── icon.svg                # App-Icon
└── [CSS/JS optional]       # Bei modularer Erweiterung
```

### Service Worker – Caching-Strategie
```
/api/*           → Network-First (immer aktuell)
/static/*        → Cache-First (App-Shell)
/index.html      → Network-First (neue Versionen)
```

### PWA-Features
- ✅ Installierbar (Windows, iPad, Browser)
- ✅ Offline-Navigierbar (App-Shell-Modell)
- ✅ API-Aufrufe gehen über Netzwerk (nicht gecacht)
- ✅ Manifest mit Icons & Theme

---

## Backend – FastAPI

### Startpunkt
```python
# app.py
from fastapi import FastAPI
app = FastAPI(title="AssistentBuyer", version="1.0")
```

### API-Struktur

#### **1. Materials** (`/api/materials`)
```
GET  /api/materials              # Materialstamm mit Filterung
GET  /api/materials/{id}         # Material-Detail
GET  /api/suppliers              # Lieferanten-Liste
```

**Filter-Parameter:**
- `q` – Freitext-Suche
- `area` – Bereich (H/E)
- `belowMin` – Nur Unterbestand
- `supplier` – Nach Lieferant filtern

**Response-Felder:**
```json
{
  "id": 1,
  "article_number": "12345",
  "article_name": "Hydraulik-Ventil",
  "manufacturer": "Viega",
  "supplier": "Haefele",
  "stock": 5,
  "min_stock": 10,
  "total_stock": 5,
  "area": "H",
  "mail_ready": true,
  "data_status": "verified",
  "version": 3
}
```

#### **2. Purchase Orders** (`/api/orders`)
```
GET  /api/orders                 # Bestellungen auflisten
POST /api/orders                 # Neue Bestellung erstellen
GET  /api/orders/{id}            # Bestelldetail
PATCH /api/orders/{id}           # Bestellung aktualisieren
POST /api/orders/{id}/receive    # Wareneingang buchen
GET  /api/orders/{id}/draft      # Bestelltext-Entwurf (für E-Mail)
```

**Bestellungs-Lifecycle:**
```
Bestellt
  ├→ Teilgeliefert (wenn Wareneingang < Bestellung)
  └→ Geliefert (wenn Wareneingang = Bestellung)
```

#### **3. Hänel/MP12N** (`/api/haenel`)
```
GET /api/haenel/status           # Verbindungsstatus
GET /api/haenel/order-recommendations  # Bestellvorschläge
GET /api/haenel/order-summary    # Zusammenfassung
```

**v1.0: READ-ONLY**
- ✅ Bestandsabfragen
- ✅ Bestellvorschläge
- ❌ Keine Schreib-Operationen (→ v2.0)

#### **4. Settings** (`/api/settings`)
```
GET  /api/settings               # Einstellungen auslesen
PATCH /api/settings              # Einstellungen speichern
```

**Speicher-Orte:**
- SQLite `settings` Tabelle
- Umgebungsvariablen (`.env`)
- Defaults (in `app.py`)

#### **5. Audit & History** (`/api/history`)
```
GET /api/history                 # Audit-Log (letzte N Einträge)
```

**Logged:**
- Material-Änderungen
- Bestellungs-Aktionen
- Wareneingänge
- Settings-Updates

---

## Datenbank – SQLite

### Schema (Seed-DB: `data/assistentbuyer_seed.db`)

```sql
-- Materialstamm
CREATE TABLE materials (
  id INTEGER PRIMARY KEY,
  article_number TEXT,
  article_name TEXT,
  manufacturer TEXT,
  manufacturer_name TEXT,
  supplier TEXT,
  stock INTEGER,
  min_stock INTEGER,
  total_stock INTEGER,
  area TEXT CHECK(area IN ('H','E')),
  mail_ready BOOLEAN,
  data_status TEXT,
  version INTEGER,
  ...
)

-- Bestellvorgänge
CREATE TABLE purchase_orders (
  id TEXT PRIMARY KEY,         -- AB-20260914-ABC123
  supplier TEXT,
  area TEXT,
  status TEXT,                 -- Bestellt, Teilgeliefert, Geliefert, Storniert
  note TEXT,
  version INTEGER,
  created_at TEXT,
  updated_at TEXT
)

-- Bestellpositionen
CREATE TABLE purchase_order_items (
  id INTEGER PRIMARY KEY,
  order_id TEXT,
  material_id INTEGER,
  article_number TEXT,
  description TEXT,
  qty_ordered REAL,
  qty_received REAL,
  unit TEXT,
  status TEXT,                 -- Offen, Teilgeliefert, Geliefert
  ...
)

-- Wareneingänge
CREATE TABLE goods_receipts (
  id INTEGER PRIMARY KEY,
  order_item_id INTEGER,
  quantity REAL,
  usage_type TEXT,             -- eingelagert, verwendet, ...
  reference TEXT,              -- z.B. Chargennummer
  note TEXT,
  received_at TEXT
)

-- Einstellungen
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value TEXT
)

-- Audit-Log
CREATE TABLE audit_log (
  id INTEGER PRIMARY KEY,
  event_type TEXT,             -- CREATE, UPDATE, DELETE, RECEIPT
  entity_type TEXT,            -- purchase_order, material, settings
  entity_id TEXT,
  message TEXT,
  payload_json TEXT,
  created_at TEXT
)
```

### Transaktionen & Integrität
```python
# Context Manager für DB
@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")    # FK-Constraints
    conn.execute("PRAGMA busy_timeout=10000") # Konflikt-Handling
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
```

---

## Adapter-Pattern (Erweiterbarkeit)

### 1. InventoryAdapter – Bestandsquellen

**Interface:**
```python
class InventoryAdapter:
    def get_inventory(self) -> dict
    def get_article(self, article_number: str) -> dict
    def health_check(self) -> bool
```

**Implementierungen:**
- `SimulatorInventoryAdapter` – Demo-Daten (Test/Entwicklung)
- `HaenelMP12NAdapter` – Live-Hänel-Integration (v1.0: Read-Only)

**Rohdaten-Format (einheitlich):**
```json
{
  "article_number": "12345",
  "description": "Ventil XL",
  "stock": 5,
  "minimum_stock": 10,
  "tray": "A",
  "compartment": 3,
  "depth": "normal",
  "package_unit": 1,
  "total_stock": 5,
  "source": "MP12N",
  "source_record_id": "abc123",
  "warnings": []
}
```

### 2. CentralDataAdapter – Zentrale Datenspeicherung (später)

**Interface:**
```python
class CentralDataAdapter:
    def get_materials(self) -> list
    def save_order(self, order: dict) -> bool
    def sync_central(self) -> dict
```

**Implementierungen:**
- `SharePointGraphAdapter` – Microsoft Graph (Ziel)
- `ExcelSharePointAdapter` – Excel-Fallback
- `SimulatorCentralAdapter` – Test

---

## Konfiguration

### Quellen (Priorität)
1. **Umgebungsvariablen** (`.env`)
2. **SQLite `settings` Tabelle**
3. **Defaults** (in `app.py`)

### Wichtige Settings
```python
mp12n_base_url       # HTTP-Adresse Hänel
mp12n_mode          # READ_ONLY (v1.0)
mp12n_timeout       # Sekunden
mp12n_cache_seconds # Cache-Dauer
default_area        # H oder E
```

### Sensitive Daten
- ❌ Nicht in Code
- ❌ Nicht in Git
- ✅ Nur in `.env` (lokal, gitignore)
- ✅ Oder Umgebungsvariablen

---

## Build & Deployment

### Lokal (Entwicklung)
```bash
python app.py
```
→ `http://127.0.0.1:8080`

### Windows EXE (Portable)
```bash
pip install -r requirements-build.txt
python build_windows_exe.bat
```
→ `dist/AssistentBuyer.exe`

### GitHub Actions (CI/CD)
```yaml
# .github/workflows/build-windows.yml
Jobs:
  - Install Dependencies
  - Run Tests
  - PyInstaller Build
  - Upload Artifact
```

---

## Fehlerbehandlung

### HTTP-Status-Codes
- `200` – OK
- `400` – Bad Request (Input-Fehler)
- `404` – Not Found
- `409` – Conflict (Versions-Konflikt)
- `502` – MP12N nicht erreichbar

### Datenbank-Fehler
```python
try:
    with db() as conn:
        conn.execute(...)
except sqlite3.IntegrityError:
    raise HTTPException(400, "Datensatz bereits vorhanden")
except sqlite3.OperationalError:
    raise HTTPException(500, "Datenbankfehler")
```

---

## Sicherheit (v1.0)

### Was schützen wir
- ✅ Lokale SQLite-Datei (Benutzer-Verzeichnis)
- ✅ Hänel-IP nicht hardcodieren
- ✅ Session-Cookies nicht speichern
- ✅ Audit-Log aller Änderungen

### Was wir nicht schützen (v1.0)
- ❌ Keine User-Authentication (Desktop/LAN-App)
- ❌ Keine Verschlüsselung (optional später)
- ❌ Keine Role-Based Access Control (later)

---

## Performance

### Caching (MP12N)
```python
MP_CACHE_SECONDS = 5  # Bestellvorschläge 5s cachen
```

### Datenbank
```python
conn.execute("PRAGMA busy_timeout=10000")  # 10s Warten bei Locks
```

### Frontend (Service Worker)
- App-Shell gecacht (index.html, CSS, Assets)
- API-Aufrufe immer fresh (Network-First)

---

## Next Steps – Roadmap

| Milestone | Fokus | Features |
|-----------|-------|----------|
| M1 ✅ | Release-Basis | Repo + Docs + .gitignore |
| M2 | Struktur | Optional: backend/, frontend/, data/ |
| M3 | Stabilisierung | FastAPI + SQLite Tests |
| M4 | Import | Materialstamm-Excel-Import |
| M5 | Adapter | Simulator + HaenelLiveAdapter |
| M6 | Integration | Frontend ↔ Backend testen |
| M7 | Phase-0–6-Tests | Alle Features validieren |
| M8 | CI/CD | GitHub Actions + PyInstaller |
| M9 | Release Candidate | v1.0-RC1 |
| M10 | QA | Regressionstest |

---

## Phase 0–6 (v1.0 Scope)

✅ Phase 0–6 ist eingefrorene Spezifikation.

Keine neuen Features bis Release 1.0!

Nur Release-blockierende Fehler beheben.
