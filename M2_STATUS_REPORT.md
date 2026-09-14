# M2 Release-Gate – Statusbericht & Umsetzungsplan

**Datum:** 2026-09-14  
**Status:** M2.1 Foundation erstellt  
**Nächster Schritt:** Integration in app.py

---

## 📊 M2 – Gesamtstatus (aus initialer Analyse)

| Bereich | Status | Priorität |
|---------|--------|-----------|
| TODO/FIXME-Marker | ✅ Keine gefunden | - |
| SQLite `file is not a database` | 🔴 Release-Blocker | **P0** |
| start_local.bat | ✅ Funktional | P2 |
| start_lan.bat | ✅ Funktional | P2 |
| Seed-DB Integrität | 🟡 Nicht verifiziert | **P1** |
| Seed-DB Schema | 🟡 Nicht verifiziert | **P1** |
| MP12N-Robustheit | 🟡 Unvollständig | **P1** |
| .env / Settings-Konsistenz | 🔴 Problematisch | **P2** |
| Code-Aufräumen | 🟡 Empfohlen | P3 |

---

## 🚀 M2.1 – Kritische Fehlerbehandlung (IN PROGRESS)

### ✅ Abgeschlossene Arbeiten

#### 1. `m2_enhancements.py` erstellt
- **`validate_seed_database()`** – SQLite Integrität & Schema-Prüfung
  - Prüft PRAGMA integrity_check
  - Validiert alle Tabellen vorhanden
  - Validiert alle Spalten pro Tabelle
  - Prüft Foreign Keys
  - Wirft aussagekräftige Fehler bei `sqlite3.DatabaseError`

- **`check_mp12n_response_validity()`** – MP12N Response-Validierung
  - Erkennt Login/PIN-Seiten (Authentifizierung erforderlich)
  - Erkennt fehlende Daten (keine Bestellvorschlagstabelle)
  - Gibt Status + Detail zurück

#### 2. `M2_INTEGRATION_GUIDE.md` erstellt
Schritt-für-Schritt Anleitung zur Integration in `app.py`:
- Imports hinzufügen
- Seed-DB Validierung vor Copy
- MP12N Response-Validierung
- Robuste Status-Prüfung
- Startup-Logging verbessern

---

## 📋 M2.1 – Noch zu tun

### **Schritt 1: app.py anpassen**
1. Import `m2_enhancements` hinzufügen (Zeile 1-26)
2. `validate_seed_database(SEED_DB)` vor Copy aufrufen (Zeile 81-84)
3. `check_mp12n_response_validity()` in `parse_recommendation_table()` (Zeile 153-165)
4. Response-Validierung in `haenel_status()` (Zeile 650-666)
5. Startup-Validierungen in `run()` (Zeile 745-763)

### **Schritt 2: Start-Scripts härten (M2.2 Preview)**
- `start_local.bat` & `start_lan.bat` verbessern
- Python-Check
- Error-Logging
- Datenbankprüfung vor Start
- Port-Konflikt-Handling

---

## 📁 Repository-Struktur (aktuell)

```
/-AssistentBuyer/
├── app.py                      # Hauptanwendung (🔴 Needs M2.1 integration)
├── m2_enhancements.py          # ✅ M2.1 Validierungsfunktionen
├── M2_INTEGRATION_GUIDE.md     # ✅ Integration-Anleitung
├── validate_db.py              # 📋 Veraltet (Hinweis)
├── data/
│   └── assistentbuyer_seed.db  # Seed-Datenbank (zu validieren)
├── start_local.bat             # 🔄 Zu härten
├── start_lan.bat               # 🔄 Zu härten
└── static/
    ├── index.html
    ├── manifest.webmanifest
    └── sw.js
```

---

## 🔧 M2.1 Umsetzungsstrategie

### Kritische Fehlerbehandlung: SQLite

**Problem:** 
- Seed-DB wird blindlings kopiert/geöffnet
- Kein `PRAGMA integrity_check`
- Fehler `file is not a database` wird nicht abgefangen

**Lösung:**
- ✅ `validate_seed_database()` prüft bei Startup
- ✅ Aussagekräftige Fehlermeldungen
- ✅ Startup verhindert bei DB-Problemen

### Kritische Fehlerbehandlung: MP12N

**Problem:**
- HTTP 200 wird als "erreichbar" interpretiert
- Login/PIN-Seite wird nicht erkannt
- Keine Unterscheidung: "keine Verbindung" vs. "authentifizierung erforderlich"

**Lösung:**
- ✅ `check_mp12n_response_validity()` prüft Response-Inhalt
- ✅ Erkennt Login-Indikatoren
- ✅ Status: "ok" | "login_required" | "invalid"

---

## 🎯 M2 – Priorisierte Abarbeitungsreihenfolge

1. **M2.1a:** Integration der Validierungsfunktionen in `app.py`
2. **M2.1b:** Start-Scripts härten (`start_local.bat`, `start_lan.bat`)
3. **M2.1c:** Konfiguration .env ↔ settings DB vereinheitlichen
4. **M2.2:** Code-Cleanup (optional für v1.0)
5. **M2.3:** Regressionstest
6. **→ v1.0 Build**

---

## 📝 Seed-Database Schemavalidierung

**Geprüfte Tabellen & Spalten:**

### materials (22 Spalten)
id, article_name, article_number, stock, min_stock, tray, compartment, depth_compartment, package_size, total_stock, manufacturer, manufacturer_name, manufacturer_article_number, model, supplier, mail_name, data_status, manufacturer_source, alternate_supplier, area, mail_ready, version

### purchase_orders (8 Spalten)
id, supplier, area, status, note, version, created_at, updated_at

### purchase_order_items (12 Spalten)
id, order_id, material_id, article_number, description, mail_description, qty_ordered, qty_received, unit, status, note, usage_after_receipt

### goods_receipts (7 Spalten)
id, order_item_id, quantity, usage_type, reference, note, received_at

### settings (2 Spalten)
key, value

### audit_log (7 Spalten)
id, event_type, entity_type, entity_id, message, payload_json, created_at

---

## 💾 Repository-Commits (M2.1)

| Commit | Message | Status |
|--------|---------|--------|
| f45ddcc | M2.1: Add validate_seed_database() helper function | ✅ |
| dd537c5 | M2.1: Remove validate_db.py - consolidate in app.py | ✅ |
| 5aa7780 | M2.1: Add m2_enhancements.py with SQLite validation | ✅ |
| 5916046 | M2.1: Integration guide for app.py enhancements | ✅ |
| **PENDING** | M2.1: Integrate validations into app.py | 🔄 |

---

## ⚡ Nächste Aktion

**Verwendeter Ansatz:**
- `m2_enhancements.py` als separate Modul (clean, testbar, wartbar)
- `M2_INTEGRATION_GUIDE.md` als Dokumentation
- Modulare Integration (kein großes Datei-Rewrite)

**Entscheidung erforderlich:**

**Option A:** Großer PR
- Alle M2.1 Punkte auf einmal in `app.py` integrieren
- 1 umfassender PR
- **Schneller an v1.0**

**Option B:** Schrittweise PRs
- M2.1a → M2.1b → M2.1c in separaten PRs
- **Bessere Nachvollziehbarkeit**
- **Mehr Zeit**

**Empfehlung:** **Option A** – Zeit ist knapp für Release, und M2.1 ist zusammenhängend.

---

## 📌 Offene Fragen / Erörterungen

1. ✅ Seed-DB Schema korrekt? → Bestätigt durch deine Analyse
2. ✅ MP12N Login-Erkennung ausreichend? → Basiert auf deinem Paternoster-Feedback
3. ⏳ .env / settings Priority? → Noch zu klären
4. ⏳ Start-Scripts Error-Logging wo? → Logs in Datei oder Console?

---

**Chat-Konsolidierung:** ✅ Abgeschlossen  
**Stand:** M2.1 Foundation ready, wartet auf Integration  
**Zieltermin v1.0:** Nach M2-Completion
