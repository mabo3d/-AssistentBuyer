import os
import tempfile
import unittest
from unittest.mock import patch

import requests

os.environ.setdefault("ASSISTENTBUYER_DATA_DIR", tempfile.mkdtemp(prefix="assistentbuyer-tests-"))

import app as app_module
from m2_enhancements import check_mp12n_response_validity


class DummyResponse:
    def __init__(self, text: str, status_code: int = 200, url: str = "http://HOST/info/article.mp"):
        self.text = text
        self.status_code = status_code
        self.url = url

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


class DummyCookie:
    def __init__(self, name: str, value: str = "secret"):
        self.name = name
        self.value = value


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


def valid_header_table_html() -> str:
    return """
    <html>
      <head><title>MP12N Alternativlayout</title></head>
      <body>
        <table>
          <tr>
            <th>Artikelnummer</th>
            <th>Beschreibung</th>
            <th>Mindestbestand</th>
            <th>Bestellt</th>
          </tr>
          <tr>
            <td>0815</td>
            <td>Alternativ</td>
            <td>4</td>
            <td>Nein</td>
          </tr>
        </table>
      </body>
    </html>
    """


class MP12NRobustnessTests(unittest.TestCase):
    def tearDown(self):
        app_module._mp_cache.clear()

    def test_status_returns_unreachable_on_network_error(self):
        session = DummySession(error=requests.ConnectTimeout("timeout"))
        with patch.object(app_module, "mp_session", return_value=session), patch.object(
            app_module,
            "setting",
            side_effect=mp12n_setting("http://HOST"),
        ):
            response = app_module.haenel_status()

        self.assertEqual(response["status"], "unreachable")
        self.assertEqual(response["mp12n"], "unreachable")

    def test_status_detects_login_form_as_auth_required(self):
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
        with patch.object(app_module, "mp_session", return_value=session), patch.object(
            app_module,
            "setting",
            side_effect=mp12n_setting("http://HOST"),
        ):
            response = app_module.haenel_status()

        self.assertEqual(response["status"], "auth_required")

    def test_status_prefers_valid_table_over_pin_text(self):
        session = DummySession([DummyResponse(valid_table_html("PIN-Hinweis"))])
        with patch.object(app_module, "mp_session", return_value=session), patch.object(
            app_module,
            "setting",
            side_effect=mp12n_setting("http://HOST"),
        ):
            response = app_module.haenel_status()

        self.assertEqual(response["status"], "ok")

    def test_status_returns_degraded_without_auth_or_expected_table(self):
        html = "<html><head><title>MP12N</title></head><body><p>Systemmeldung ohne Artikeldaten</p></body></html>"
        session = DummySession([DummyResponse(html)])
        with patch.object(app_module, "mp_session", return_value=session), patch.object(
            app_module,
            "setting",
            side_effect=mp12n_setting("http://HOST"),
        ):
            response = app_module.haenel_status()

        self.assertEqual(response["status"], "degraded")

    def test_status_detects_login_redirect_with_http_200(self):
        session = DummySession([DummyResponse("<html><body>Weiterleitung</body></html>", url="http://HOST/login")])
        with patch.object(app_module, "mp_session", return_value=session), patch.object(
            app_module,
            "setting",
            side_effect=mp12n_setting("http://HOST"),
        ):
            response = app_module.haenel_status()

        self.assertEqual(response["status"], "auth_required")

    def test_mp_get_uses_origin_for_data_path_when_bootstrap_url_is_configured(self):
        session = DummySession([DummyResponse("<html></html>")])
        with patch.object(app_module, "setting", side_effect=mp12n_setting("http://HOST/info/home.pc")):
            app_module.mp_get(session, "/info/article.mp")

        self.assertEqual(session.calls[0]["url"], "http://HOST/info/article.mp")

    def test_mp_get_uses_https_origin_for_data_path_when_bootstrap_url_is_configured(self):
        session = DummySession([DummyResponse("<html></html>")])
        with patch.object(app_module, "setting", side_effect=mp12n_setting("https://HOST/info/home.pc")):
            app_module.mp_get(session, "/info/article.mp")

        self.assertEqual(session.calls[0]["url"], "https://HOST/info/article.mp")

    def test_read_recommendations_bootstraps_home_page_when_only_origin_is_configured(self):
        session = DummySession([
            DummyResponse("<html><body>Bootstrap</body></html>", url="http://HOST/info/home.pc"),
            DummyResponse(valid_table_html(), url="http://HOST/info/article.mp"),
        ], cookies=[DummyCookie("SESSIONID", "very-secret-cookie")])
        with patch.object(app_module, "mp_session", return_value=session), patch.object(
            app_module,
            "setting",
            side_effect=mp12n_setting("http://HOST"),
        ):
            result = app_module.read_recommendations("all")

        self.assertEqual(session.calls[0]["url"], "http://HOST/info/home.pc")
        self.assertEqual(session.calls[1]["url"], "http://HOST/info/article.mp")
        self.assertEqual(result["count"], 1)

    def test_response_validity_accepts_expected_mp12n_table_without_id(self):
        validity = check_mp12n_response_validity(valid_header_table_html())

        self.assertEqual(validity["status"], "ok")
        self.assertTrue(validity["hasExpectedTable"])

    def test_response_validity_marks_unexpected_html_as_degraded(self):
        validity = check_mp12n_response_validity("<html><body><p>Unbekannte Systemseite</p></body></html>")

        self.assertEqual(validity["status"], "degraded")
        self.assertFalse(validity["hasExpectedTable"])


if __name__ == "__main__":
    unittest.main()
