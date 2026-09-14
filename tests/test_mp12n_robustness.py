import os

import requests

os.environ.setdefault("ASSISTENTBUYER_DATA_DIR", "/tmp/assistentbuyer-tests")

import app as app_module


class DummyResponse:
    def __init__(self, text: str, status_code: int = 200, url: str = "http://HOST/info/article.mp"):
        self.text = text
        self.status_code = status_code
        self.url = url

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


class DummyCookie:
    def __init__(self, name: str):
        self.name = name


class DummySession:
    def __init__(self, responses=None, error: Exception | None = None, cookies=None):
        self.responses = list(responses or [])
        self.error = error
        self.calls = []
        self.cookies = list(cookies or [])

    def get(self, url, params=None, timeout=None, allow_redirects=None):
        self.calls.append({
            "url": url,
            "params": params,
            "timeout": timeout,
            "allow_redirects": allow_redirects,
        })
        if self.error is not None:
            raise self.error
        if not self.responses:
            raise AssertionError("No dummy response configured")
        return self.responses.pop(0)


def mp12n_setting(url: str):
    return lambda key, default="": url if key == "mp12n_base_url" else default


def valid_table_html(extra_text: str = "") -> str:
    return f"""
    <html>
      <head><title>MP12N Artikel</title></head>
      <body>
        <div>{extra_text}</div>
        <table id="haeneltable">
          <tr>
            <th>Artikelnummer</th>
            <th>Beschreibung</th>
            <th>Mindestbestand</th>
            <th>Gesamtbestand</th>
            <th>Bestellt</th>
          </tr>
          <tr>
            <td>4711</td>
            <td>Testartikel</td>
            <td>2</td>
            <td>5</td>
            <td>Nein</td>
          </tr>
        </table>
      </body>
    </html>
    """


def test_status_returns_unreachable_on_network_error(monkeypatch):
    session = DummySession(error=requests.ConnectTimeout("timeout"))
    monkeypatch.setattr(app_module, "mp_session", lambda: session)
    monkeypatch.setattr(app_module, "setting", mp12n_setting("http://HOST"))

    response = app_module.haenel_status()

    assert response["status"] == "unreachable"


def test_status_detects_login_form_as_auth_required(monkeypatch):
    html = """
    <html>
      <head><title>Login</title></head>
      <body>
        <form id="loginForm" action="/login">
          <label for="pin">PIN</label>
          <input id="pin" name="pin" type="password" />
        </form>
      </body>
    </html>
    """
    session = DummySession([DummyResponse(html, url="http://HOST/login")])
    monkeypatch.setattr(app_module, "mp_session", lambda: session)
    monkeypatch.setattr(app_module, "setting", mp12n_setting("http://HOST"))

    response = app_module.haenel_status()

    assert response["status"] == "auth_required"


def test_status_prefers_valid_table_over_pin_text(monkeypatch):
    session = DummySession([DummyResponse(valid_table_html("PIN-Hinweis"))])
    monkeypatch.setattr(app_module, "mp_session", lambda: session)
    monkeypatch.setattr(app_module, "setting", mp12n_setting("http://HOST"))

    response = app_module.haenel_status()

    assert response["status"] == "ok"


def test_status_returns_degraded_without_auth_or_expected_table(monkeypatch):
    html = "<html><head><title>MP12N</title></head><body><p>Systemmeldung ohne Artikeldaten</p></body></html>"
    session = DummySession([DummyResponse(html)])
    monkeypatch.setattr(app_module, "mp_session", lambda: session)
    monkeypatch.setattr(app_module, "setting", mp12n_setting("http://HOST"))

    response = app_module.haenel_status()

    assert response["status"] == "degraded"


def test_mp_get_uses_origin_for_data_path_when_bootstrap_url_is_configured(monkeypatch):
    session = DummySession([DummyResponse("<html></html>")])
    monkeypatch.setattr(app_module, "setting", mp12n_setting("http://HOST/info/home.pc"))

    app_module.mp_get(session, "/info/article.mp")

    assert session.calls[0]["url"] == "http://HOST/info/article.mp"


def test_read_recommendations_bootstraps_home_page_when_only_origin_is_configured(monkeypatch):
    session = DummySession([
        DummyResponse("<html><body>Bootstrap</body></html>", url="http://HOST/info/home.pc"),
        DummyResponse(valid_table_html(), url="http://HOST/info/article.mp"),
    ], cookies=[DummyCookie("SESSIONID")])
    monkeypatch.setattr(app_module, "mp_session", lambda: session)
    monkeypatch.setattr(app_module, "setting", mp12n_setting("http://HOST"))
    app_module._mp_cache.clear()

    result = app_module.read_recommendations("all")

    assert session.calls[0]["url"] == "http://HOST/info/home.pc"
    assert session.calls[1]["url"] == "http://HOST/info/article.mp"
    assert result["count"] == 1
