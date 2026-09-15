import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import requests

os.environ.setdefault("ASSISTENTBUYER_DATA_DIR", tempfile.mkdtemp(prefix="assistentbuyer-tests-"))

import app as app_module


VALID_MP12N_HTML = """
<html>
  <head><title>MP12N Artikel</title></head>
  <body>
    <table id="haeneltable">
      <tr>
        <th>Artikelnummer</th>
        <th>Beschreibung</th>
        <th>Mindestbestand</th>
        <th>Gesamtbestand</th>
        <th>Bestellt</th>
      </tr>
    </table>
  </body>
</html>
"""


def set_mp12n_base_url(value: str) -> None:
    with app_module.db() as conn:
        conn.execute(
            "INSERT INTO settings(key,value) VALUES('mp12n_base_url',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (value,),
        )
    app_module._mp_cache.clear()


class HaenelDiagnosticsTests(unittest.TestCase):
    def test_probe_sanitizes_configured_origin_and_final_urls(self):
        set_mp12n_base_url("https://alice@example.com/mp12n/bootstrap?debug=1#frag")

        with patch.object(
            app_module,
            "mp_get",
            return_value=SimpleNamespace(
                text=VALID_MP12N_HTML,
                status_code=200,
                url="https://bob@example.com/info/article.mp?debug=1#step",
            ),
        ):
            payload = app_module.haenel_probe()

        self.assertEqual(payload["configuredUrl"], "https://example.com/mp12n/bootstrap")
        self.assertEqual(payload["origin"], "https://example.com")
        self.assertEqual(payload["finalUrl"], "https://example.com/info/article.mp")
        self.assertNotIn("alice@", str(payload))
        self.assertNotIn("bob@", str(payload))
        self.assertNotIn("debug=1", str(payload))
        self.assertNotIn("#step", str(payload))

    def test_status_sanitizes_urls_from_config_and_response(self):
        set_mp12n_base_url("https://alice@example.com/mp12n/bootstrap?debug=1#frag")

        with patch.object(
            app_module,
            "mp_get",
            return_value=SimpleNamespace(
                text=VALID_MP12N_HTML,
                status_code=200,
                url="https://bob@redirect.example.com/info/article.mp?debug=1#step",
            ),
        ):
            payload = app_module.haenel_status()

        self.assertEqual(payload["baseUrl"], "https://example.com/mp12n/bootstrap")
        self.assertEqual(payload["configuredUrl"], "https://example.com/mp12n/bootstrap")
        self.assertEqual(payload["origin"], "https://example.com")
        self.assertEqual(payload["finalUrl"], "https://redirect.example.com/info/article.mp")
        self.assertNotIn("alice@", str(payload))
        self.assertNotIn("bob@", str(payload))
        self.assertNotIn("debug=1", str(payload))
        self.assertNotIn("#step", str(payload))
        self.assertEqual(payload["status"], "ok")

    def test_settings_reject_base_url_without_host(self):
        with self.assertRaises(app_module.HTTPException) as ctx:
            app_module.patch_settings(app_module.SettingPatch(mp12nBaseUrl="http:///missing-host"))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Host", ctx.exception.detail)

    def test_settings_reject_base_url_with_invalid_scheme(self):
        with self.assertRaises(app_module.HTTPException) as ctx:
            app_module.patch_settings(app_module.SettingPatch(mp12nBaseUrl="ftp://example.com/info/home.pc"))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("http:// oder https://", ctx.exception.detail)

    def test_settings_reject_base_url_with_invalid_port(self):
        with self.assertRaises(app_module.HTTPException) as ctx:
            app_module.patch_settings(app_module.SettingPatch(mp12nBaseUrl="https://example.com:abc/info/home.pc"))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("ungültigen Port", ctx.exception.detail)

    def test_mp_get_error_detail_does_not_echo_sensitive_url(self):
        set_mp12n_base_url("https://alice@example.com/mp12n/bootstrap?debug=1#frag")

        with patch.object(
            requests.Session,
            "get",
            side_effect=requests.ConnectionError("https://alice@example.com/info/article.mp?debug=1#frag"),
        ):
            with self.assertRaises(app_module.HTTPException) as ctx:
                app_module.mp_get(app_module.mp_session(), "/info/article.mp")

        detail = ctx.exception.detail
        self.assertIn("ConnectionError", detail)
        self.assertNotIn("alice@", detail)
        self.assertNotIn("debug=1", detail)
        self.assertNotIn("#frag", detail)

    def test_status_reports_invalid_base_url_as_unreachable(self):
        set_mp12n_base_url("http:///missing-host")

        payload = app_module.haenel_status()

        self.assertEqual(payload["status"], "unreachable")
        self.assertEqual(payload["finalUrl"], "")
        self.assertIn("Host", payload["reason"])

    def test_probe_exposes_cookie_names_but_not_values(self):
        set_mp12n_base_url("http://HOST/info/home.pc?token=abc#frag")

        with patch.object(
            app_module,
            "mp_session",
            return_value=SimpleNamespace(cookies=[SimpleNamespace(name="SESSIONID", value="very-secret")]),
        ), patch.object(
            app_module,
            "mp_get",
            return_value=SimpleNamespace(
                text="<html><table id='haeneltable'><tr><th>Artikelnummer</th><th>Beschreibung</th><th>Mindestbestand</th><th>Gesamtbestand</th><th>Bestellt</th></tr></table></html>",
                status_code=200,
                url="http://HOST/info/article.mp?sid=secret",
            ),
        ):
            payload = app_module.haenel_probe()

        self.assertEqual(payload["cookieNames"], ["SESSIONID"])
        self.assertNotIn("very-secret", str(payload))
        self.assertNotIn("token=abc", str(payload))
        self.assertNotIn("sid=secret", str(payload))


if __name__ == "__main__":
    unittest.main()
