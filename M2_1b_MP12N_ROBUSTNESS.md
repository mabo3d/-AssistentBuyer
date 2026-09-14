# M2.1b – MP12N Robustness / Login-PIN Detection

## Ziel

Die MP12N-Anbindung in AssistentBuyer wird robuster, ohne Schreibzugriffe auf den MP12N einzuführen. Der Scope bleibt strikt bei Lesezugriffen und bei der Erkennung von Verfügbarkeit, Login-Anforderungen und unklaren Antworten.

## Statusmodell

`/api/haenel/status` und `/api/haenel/probe` verwenden vier Zustände:

- `ok` – MP12N erreichbar und erwartete Artikeldatenstruktur erkannt
- `auth_required` – MP12N erreichbar, aber Login/PIN/Auth wird angefordert
- `degraded` – MP12N antwortet, aber die erwartete Artikeldatenstruktur ist nicht sicher erkennbar
- `unreachable` – Netzwerk-, Timeout- oder HTTP-Fehler

Erlaubte Diagnosedaten sind nur technische Statusinformationen wie `status`, `httpStatus`, `finalUrl` und `reason`.

## URL-Normalisierung

Die Konfiguration `mp12n_base_url` wird in zwei Teile getrennt:

- `origin` – nur Schema und Host
- `bootstrapPath` – optionaler konfigurierter Einstiegspfad

Beispiele:

- `http://HOST/info/home.pc` → `origin=http://HOST`, `bootstrapPath=/info/home.pc`
- `http://HOST` → `origin=http://HOST`, `bootstrapPath=/info/home.pc`

Alle Datenabfragen wie `/info/article.mp` werden immer relativ zum `origin` aufgebaut. Dadurch wird aus `http://HOST/info/home.pc` nicht mehr fälschlich `http://HOST/info/home.pc/info/article.mp`.

## Login-Erkennung

Die HTML-Prüfung nutzt mehrere Indikatoren statt einfachem Substring-Matching:

- `input[type="password"]`
- Formulare mit Auth-Begriffen in `id`, `name`, `action` oder `class`
- deutliche Auth-Texte wie `Login`, `Anmelden`, `Authentifizierung`, `Passwort`, `Kennwort`
- Redirects auf typische Login-Ziele

Ein einzelnes Vorkommen von `PIN` reicht nicht aus. Wenn gleichzeitig die erwartete MP12N-Artikeltabelle erkannt wird, gewinnt immer `ok`.

## Datenstruktur-Erkennung

Eine MP12N-Antwort gilt als valide, wenn mindestens eine der folgenden Bedingungen erfüllt ist:

- `table#haeneltable` vorhanden
- eine Tabelle mit den Headern `Artikelnummer`, `Mindestbestand` und `Bestellt` erkannt

Antworten ohne Auth-Marker und ohne diese Struktur werden als `degraded` behandelt.

## READ-ONLY-Garantie

M2.1b führt keine Schreibzugriffe auf den MP12N ein.

- nur `GET`-Requests
- Redirects erlaubt
- keine POST-, Änderungs- oder Steuerbefehle

Die bestehende Recommendation-Logik inklusive Pagination bleibt erhalten.

## Sicherheitsregeln

- keine produktiven Hosts oder IPs hardcodieren
- keine PINs, Credentials, Token oder Cookie-Werte speichern oder committen
- im Diagnose-Endpoint nur Cookie-Namen, niemals Cookie-Werte ausgeben
- Netzwerkfehler und Inhaltsprüfung getrennt behandeln

## Testfälle

Abgedeckte Regressionen:

- Netzwerk nicht erreichbar → `unreachable`
- Login-Formular mit HTTP 200 → `auth_required`
- `PIN`-Text plus valide `haeneltable` → `ok`
- HTTP 200 ohne Login-Marker und ohne erwartete Tabelle → `degraded`
- konfigurierte URL `http://HOST/info/home.pc` ruft `/info/article.mp` korrekt über `http://HOST/info/article.mp` auf
- konfigurierte URL `http://HOST` nutzt Bootstrap `/info/home.pc` und Datenpfad `/info/article.mp`

## Bekannte Grenzen

- Die Erkennung basiert auf HTML-Heuristiken und kann ungewöhnliche, stark angepasste MP12N-Layouts nur eingeschränkt klassifizieren.
- Ohne erwartete Tabelle und ohne klare Auth-Hinweise wird absichtlich `degraded` statt `ok` gemeldet.
