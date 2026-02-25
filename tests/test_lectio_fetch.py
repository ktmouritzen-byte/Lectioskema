from __future__ import annotations
# pyright: reportMissingImports=false

from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import gzip

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lectio_sync.lectio_fetch import fetch_html


class _FakeHeaders:
    def __init__(self, *, content_encoding: str | None, charset: str | None = "utf-8") -> None:
        self._content_encoding = content_encoding
        self._charset = charset

    def get(self, name: str, default=None):
        if name.lower() == "content-encoding":
            return self._content_encoding
        return default

    def get_content_charset(self):
        return self._charset


class _FakeResponse:
    def __init__(self, *, body: bytes, headers: _FakeHeaders) -> None:
        self._body = body
        self.headers = headers

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class LectioFetchTests(unittest.TestCase):
    def test_fetch_html_decompresses_gzip(self) -> None:
        html = "<html><body><table id='m_Content_SkemaMedNavigation_skema_skematabel'></table></body></html>"
        gz = gzip.compress(html.encode("utf-8"))

        def _fake_urlopen(req, timeout=30):
            return _FakeResponse(body=gz, headers=_FakeHeaders(content_encoding="gzip"))

        with patch("lectio_sync.lectio_fetch.urlopen", _fake_urlopen):
            out = fetch_html(url="https://example.invalid/", cookie_header="a=b", timeout_seconds=5)

        self.assertIn("<table", out)
        self.assertIn("m_Content_SkemaMedNavigation_skema_skematabel", out)


if __name__ == "__main__":
    unittest.main()
