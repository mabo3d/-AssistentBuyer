"""
M2.1 Integration Guide for app.py

Diese Datei zeigt, wo und wie die M2.1-Enhancements in app.py integriert werden.
"""

# ================================================================
# SCHRITT 1: Import hinzufügen (nach Zeile 25 in app.py)
# ================================================================

# Füge nach den anderen imports hinzu:
# from m2_enhancements import validate_seed_database, check_mp12n_response_validity


# ================================================================
# SCHRITT 2: Seed-DB Validierung (vor Zeile 81 in app.py)
# ================================================================

# Ersetze die Lines 81-84 mit:

"""
# M2.1: Validate Seed Database vor dem Copy
if not DB_PATH.exists():
    if not SEED_DB.exists():
        raise RuntimeError(f"Seed-Datenbank fehlt: {SEED_DB}")
    
    # M2.1: Validiere Seed-DB Integrität
    validate_seed_database(SEED_DB)
    shutil.copy2(SEED_DB, DB_PATH)
"""


# ================================================================
# SCHRITT 3: MP12N Response Validierung (vor Zeile 165 in app.py)
# ================================================================

# In der Funktion parse_recommendation_table(), nach dem Fallback-Check:

"""
def parse_recommendation_table(html: str) -> tuple[list[dict[str, str]], bool]:
    soup = BeautifulSoup(html, "html.parser")
    
    # M2.1: Validiere MP12N Response
    validity = check_mp12n_response_validity(html)
    if validity["status"] != "ok":
        raise HTTPException(
            status_code=502,
            detail=f"MP12N nicht verfügbar: {validity['detail']}"
        )
    
    table = soup.find("table", id="haeneltable")
    # ... rest der Funktion
"""


# ================================================================
# SCHRITT 4: Robuste MP12N Status-Prüfung (Zeile 650-666 in app.py)
# ================================================================

# Verbessere die haenel_status() Funktion:

"""
@app.get("/api/haenel/status")
def haenel_status():
    started = time.perf_counter()
    s = mp_session()
    try:
        r = mp_get(s, "/info/article.mp")
        
        # M2.1: Prüfe Response-Gültigkeit
        validity = check_mp12n_response_validity(r.text)
        if validity["status"] != "ok":
            return {
                "bridge": "ok",
                "mode": "READ_ONLY",
                "mp12n": "degraded",
                "baseUrl": setting("mp12n_base_url", ""),
                "httpStatus": r.status_code,
                "issue": validity["detail"],
                "latencyMs": round((time.perf_counter() - started) * 1000),
            }
        
        return {
            "bridge": "ok",
            "mode": "READ_ONLY",
            "mp12n": "reachable",
            "baseUrl": setting("mp12n_base_url", ""),
            "httpStatus": r.status_code,
            "latencyMs": round((time.perf_counter() - started) * 1000),
        }
    except HTTPException as exc:
        return {
            "bridge": "ok",
            "mode": "READ_ONLY",
            "mp12n": "unreachable",
            "baseUrl": setting("mp12n_base_url", ""),
            "detail": exc.detail,
        }
"""


# ================================================================
# SCHRITT 5: Startup-Logging (Zeile 745-763 in app.py)
# ================================================================

# Ergänze die run() Funktion um bessere Fehlerbehandlung:

"""
def run():
    parser = argparse.ArgumentParser(description="AssistentBuyer v1.0")
    parser.add_argument("--lan", action="store_true", help="Im lokalen Netz auf 0.0.0.0 bereitstellen")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    # M2.1: Startup-Validierungen
    print(f"{APP_NAME} v{APP_VERSION} - Starting...")
    print(f"Data directory: {DATA_DIR}")
    print(f"Database: {DB_PATH}")
    
    try:
        # Validiere Seed-DB Integrität
        validate_seed_database(SEED_DB)
        print("✓ Seed database validated")
    except RuntimeError as e:
        print(f"✗ Database validation failed: {e}")
        sys.exit(1)
    
    host = args.host or ("0.0.0.0" if args.lan else "127.0.0.1")
    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")).start()

    print(f"{APP_NAME} v{APP_VERSION}")
    print(f"Daten: {DATA_DIR}")
    print(f"MP12N: {setting('mp12n_base_url', '')} [READ ONLY]")
    print(f"Web: http://127.0.0.1:{args.port}")
    if args.lan:
        print("LAN-Modus aktiv. Windows-Firewall/Firmenrichtlinien können eingehende Verbindungen blockieren.")
    
    uvicorn.run(app, host=host, port=args.port, log_level="warning")
"""


print("""
================================================================
M2.1 Integration Summary
================================================================

1. Import m2_enhancements in app.py Zeile 1-26 hinzufügen
2. validate_seed_database() vor DB-Copy aufrufen (Zeile 81-84)
3. check_mp12n_response_validity() in parse_recommendation_table() (Zeile 153-165)
4. Response-Validierung in haenel_status() (Zeile 650-666)
5. Startup-Validierungen in run() (Zeile 745-763)

Status: Ready for Integration
================================================================
""")
