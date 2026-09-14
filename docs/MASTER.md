# MASTER.md – Projektspezifikation Phase 0–6 (v1.0 eingefrorener Scope)

## Projektübersicht

**AssistentBuyer v1.0** ist eine Windows-PWA für Werkstatt-Lager- und Bestellverwaltung mit Hänel/MP12N-Integration.

- **Zielversion**: 1.0 (stabil, Release-Ready)
- **Zielplattformen**: Windows (portable EXE), Browser (PWA), iPad/Tablet
- **Scope**: Phase 0–6 eingefrorene Spezifikation
- **Status**: Release-Stabilisierung (keine neuen Features bis v1.0)

---

## Projektziele

### Release 1.0 (jetzt)
✅ Bestandsverwaltung & Lagerkontrolle
✅ Bestellverwaltung (Anfrage → Angebot → Bestellung → WE)
✅ Hänel/MP12N Read-Only Integration
✅ Materialstamm (H/E-getrennt)
✅ Dashboard & Statistiken
✅ Portable Windows-EXE
✅ PWA für Browser/Tablet

### Bewusst NICHT in v1.0
❌ Schreibende MP12N-Integration (Liftbefehle, Bestandsänderungen)
❌ Automatische Hänel-Artikelanlage
❌ Vollautomatische Herstellerrecherche (KI)
❌ Komplexes Rollen-/Rechtesystem
❌ Frei konfigurierbare UI-Widgets
❌ Erweiterte ERP-Funktionalität

---

## Funktionsumfang (Phase 0–6)

### 1. Materialstamm
- ✅ H/E-getrennte Materialsuche
- ✅ Herstellerzuordnung
- ✅ Lieferantenzuordnung
- ✅ Beschaffungsinformationen
- ✅ Verifikationsstatus (raw → normalized → verified)
- ✅ Prüfstatus für bekannte Sonderfälle (194123, 268367, 354978)
- ✅ Materialzähler: 584 Positionen (438 Hydraulik, 146 Elektrik)

### 2. Hänel/MP12N-Integration
- ✅ Live Bestandsabfrage (Read-Only)
- ✅ Lagerorte anzeigen (Tablar, Fach, Tiefe)
- ✅ Mindestbestand anzeigen
- ✅ Bestellbedarf erkennen
- ✅ Bestellvorschläge abrufen
- ✅ Rohdaten-Format standardisiert
- ❌ Keine Schreib-Operationen in v1.0
- ❌ Keine automatische Artikelanlage in v1.0

**Rohdaten von MP12N:**
```
- Artikelnummer
- Hänelbezeichnung
- Bestand
- Mindestbestand
- Tablar
- Fach
- Tiefe
- Verpackungseinheit (Gebinde)
- Gesamtbestand
- Quellseite
- Datensatz-ID
- Fehler-/Rohdatenhinweise
```

### 3. Bestellverwaltung
- ✅ Bestellvorgänge erstellen (AB-YYYYMMDD-XXXXXX)
- ✅ Positionen verwalten (Menge, Einheit, Beschreibung)
- ✅ Anfrage → Angebot → Bestellung → Lieferant
- ✅ Bestellstatus (Bestellt → Teilgeliefert → Geliefert → Storniert)
- ✅ Teil- und Nachlieferungen unterstützen
- ✅ Versionsschutz (Konflikt-Erkennung)
- ✅ E-Mail-Draft-Generierung
- ✅ Ariba-Export (optional)

### 4. Wareneingang
- ✅ WE-Erfassung pro Bestellposition
- ✅ Verwendung vs. Einlagerung getrennt
- ✅ Chargennummern/Referenzen erfassen
- ✅ Mengen-Validierung (nicht über Bestellung)
- ✅ Status-Berechnung (Offen → Teilgeliefert → Geliefert)

### 5. Datenmanagement
- ✅ Zentrale Datenhaltung (SharePoint Lists + Microsoft Graph)
- ✅ Fallback: Excel auf SharePoint
- ✅ Lokal: SQLite (portabel)
- ✅ Datenimport (Excel-Materialstamm)
- ✅ Export/Backup (JSON)
- ✅ Audit-Log (alle Änderungen)
- ✅ Konflikt-/Versionsschutz

### 6. Benutzeroberfläche
- ✅ Dashboard (Überblick, KPIs)
- ✅ Lager-Modul (Bestand, Suche, Lagerorte)
- ✅ Bestellen-Modul (Vorgänge erstellen/verwalten)
- ✅ Wareneingang-Modul (WE-Erfassung)
- ✅ Verlauf-Modul (Journal, Audit-Log)
- ✅ Einstellungen-Modul (MP12N-URL, Bereiche, etc.)
- ✅ MP12N-Modul (Read-Only Status & Vorschläge)
- ✅ PWA (offline-fähig, auf iPad/Windows installierbar)

---

## Datenquellen & Integrationen

### Bestandsinformationen
**Primärquelle: Hänel/MP12N**
- Live-Abfrage über Read-Only-Adapter
- Rohdaten standardisiert
- Keine konkurrierenden Bestände

### Materialstamm
**Quelldateien:**
- `Haenel_Gesamte_Materialliste.xlsx` (Hänel-Referenz)
- `Haenel_Materialstamm_Bestellung_Herstelleranalyse_v11_Bereiche.xlsx` (angereichert)

**Datenebenen:**
```
Rohwert (von Hänel)
  ↓
Normalisiert (Format/Fehler bereinigt)
  ↓
Verifiziert (manuell bestätigt oder auto-validiert)
  ↓
Endstand (für Bestellvorgänge)
```

**Unsichere Zuordnungen** werden nicht automatisch bestätigt.

### Zentrale Daten (v1.0 vorbereitet, aber noch nicht aktiv)
- **Zielzustand**: SharePoint Lists + Microsoft Graph
- **Fallback**: Excel auf SharePoint
- **Inhalte**: Vorgänge, Positionen, Kontakte, Status, Wareneingänge, Historie, Preise, Einstellungen

### Beschaffung
- ✅ E-Mail-Export (Bestelltext)
- ✅ Ariba-Integration (optional)
- ❌ Weitere ERP-Systeme (später)

---

## Technologie-Stack

| Ebene | Technologie |
|-------|-------------|
| **Frontend** | HTML5, CSS3, Vanilla JavaScript (ES Modules) |
| **PWA** | Service Worker, Offline-Support, installierbar |
| **Backend** | Python 3.9+, FastAPI |
| **Datenbank (lokal)** | SQLite (portabel) |
| **Datenbank (zentral)** | SharePoint Lists + Microsoft Graph (vorbereitet) |
| **Lagerintegration** | Hänel MP12N (HTTP, Read-Only) |
| **Build** | PyInstaller (Windows EXE) |
| **CI/CD** | GitHub Actions |
| **VCS** | Git / GitHub |

---

## Architektur-Prinzipien

### 1. Adapter-Pattern (Erweiterbarkeit)

**InventoryAdapter** für Bestandsquellen:
```
InventoryAdapter (Interface)
├── SimulatorInventoryAdapter (Test)
└── HaenelMP12NAdapter (Live, v1.0: Read-Only)
```

Beide liefern identisches Rohdaten-Format.

**CentralDataAdapter** für zentrale Daten:
```
CentralDataAdapter (Interface)
├── SharePointGraphAdapter (Ziel)
├── ExcelSharePointAdapter (Fallback)
└── SimulatorCentralAdapter (Test)
```

### 2. Datenhoheit

- **Hänel**: Liefert aktuellen Istbestand
- **AssistentBuyer**: Liest Hänel, führt keinen konkurrierenden Lager-Istbestand
- **SharePoint/Excel**: Zentrale Business-Daten
- **SQLite**: Lokale App-Daten & Cache

### 3. Saubere Separation

```
UI (Frontend/PWA)
  ↓ REST API
Fachlogik (FastAPI)
  ↓
Adapter-Schicht (InventoryAdapter, CentralDataAdapter)
  ↓
Externe Systeme (MP12N, SharePoint, Excel)
```

Fachlogik hängt nicht direkt von Hänel/SharePoint/Excel ab.

---

## Datensicherheit

### Keine produktiven Secrets im Repository
- ❌ MP12N Session-Cookies
- ❌ MP12N Login-Daten
- ❌ SharePoint Client-Secrets
- ❌ Hänel-IP hartcodiert
- ✅ `.env` ist lokal, nicht im Git
- ✅ `.env.example` zeigt die Struktur

### Audit-Log
- ✅ Alle Änderungen werden geloggt
- ✅ Wer, Was, Wann, Warum
- ✅ Nachverfolgbar für QS/Audit

---

## Bekannte Prüffälle & Sonderfälle

**Referenzbestand enthält 7 mehrfach vorkommende Artikelnummern.**

**Bekannte Prüffälle** (nicht automatisch „repariert"):
- 194123
- 268367
- 354978

Diese erfordern manuelle Verifizierung und werden mit Status `PRÜFEN` markiert.

---

## Release-Prozess

### Stabilisierungs-Phase (jetzt)
1. M1 ✅ – Repository + Dokumentation
2. M2 – Projektstruktur bereinigen
3. M3 – FastAPI + SQLite stabilisieren
4. M4 – Materialstamm-Import validieren
5. M5 – Simulator + Adapter vereinheitlichen
6. M6 – Phase-0–6-Gesamttest
7. M7 – Fehlerbehebung
8. M8 – GitHub Actions + PyInstaller-Build
9. M9 – Release Candidate 1
10. M10 – Regressionstest → **Release 1.0**

### Vor Release 1.0
- ✅ Phase 0–6 Gesamttest durchlaufen
- ✅ Keine blockierenden Bugs
- ✅ MP12N Read-Only verifiziert
- ✅ Windows-EXE funktioniert portabel
- ✅ PWA auf iPad/Chrome lauffähig
- ✅ Dokumentation aktuell

### Nach Release 1.0
- ➡️ v1.1: Fehlerbehebungen
- ➡️ v2.0: Schreibende MP12N-Integration, SharePoint-Anbindung, KI-Features

---

## Wichtige Links & Referenzen

- **GitHub Repo**: https://github.com/mabo3d/AssistentBuyer
- **Dokumentation**: `/docs/`
  - `BUILD.md` – Lokales Setup
  - `ARCHITECTURE.md` – System-Design
  - `RELEASE.md` – Release-Prozess

- **Externe Systeme**:
  - Hänel MP12N (HTTP Read-Only)
  - SharePoint Lists (später)
  - Excel Fallback (später)

---

## Versionshistorie

| Version | Datum | Status | Hinweise |
|---------|-------|--------|----------|
| 0.1 | 2026-08 | Konzept | Projektentwurf |
| 0.5 | 2026-09 | Phase 0–6 | Spezifikation eingefrorenen |
| 1.0-RC1 | 2026-09-14 | Release Candidate | M1: Repository + Dokumentation |
| 1.0 | TBD | Release | Nach Phase-0–6-Test |

---

## FAQ

**F: Warum keine schreibende MP12N-Integration in v1.0?**
A: Technisches Risiko minimieren. Read-Only ist sicher. Schreiben nur nach intensiver Verifizierung.

**F: Warum Vanilla JS statt React/Vue?**
A: Keine unnötige Framework-Komplexität in Release-Phase. Interface ist klar abgegrenzt. Später zu React+TS wechselbar.

**F: Warum SQLite lokal + SharePoint zentral?**
A: SQLite ermöglicht Portabilität & Offline. SharePoint zentralisiert Business-Daten und Kollaboration.

**F: Was mit den bekannten Prüffällen (194123, etc.)?**
A: Werden mit Status `PRÜFEN` gekennzeichnet. Manuelle Verifizierung erforderlich. Nicht automatisch „korrigiert".

**F: Kann ich die App auf Tablet/iPad nutzen?**
A: Ja – als PWA installierbar. Voller Funktionsumfang, funktioniert auch offline (App-Shell).

---

## Kontakt & Support

- **Projekt-Owner**: mabo3d
- **GitHub Issues**: Für Bug-Reports & Feature-Requests (nach v1.0)
- **Dokumentation**: `/docs/` im Repo

---

**Stand: 2026-09-14**
**Status: Release-Basis hergestellt (M1 ✅)**
**Nächster Schritt: M2 – Projektstruktur bereinigen**
