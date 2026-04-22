"""Tests for mobile FastAPI client."""

from __future__ import annotations

import json
from urllib import error

import pytest

from patrimonio.mobile.api_client import ApiClientError, FastFinanceApiClient


class _Response:
    def __init__(self, payload: dict | list):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        del exc_type, exc, tb
        return False


def test_get_summary_success(monkeypatch):
    client = FastFinanceApiClient(base_url="http://example")

    def fake_urlopen(req, timeout):
        del timeout
        assert req.full_url == "http://example/api/resumen"
        return _Response({"patrimonio_neto": "10.00"})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = client.get_summary()
    assert result["patrimonio_neto"] == "10.00"


def test_delete_bank_uses_expected_path(monkeypatch):
    client = FastFinanceApiClient(base_url="http://example")

    def fake_urlopen(req, timeout):
        del timeout
        assert req.full_url == "http://example/api/bancos/33"
        assert req.method == "DELETE"
        return _Response({"message": "ok"})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = client.delete_bank(33)
    assert result["message"] == "ok"


def test_http_error_raises_api_client_error(monkeypatch):
    client = FastFinanceApiClient(base_url="http://example")

    class _ErrPayload:
        def read(self):
            return b'{"detail":"bad request"}'

        def close(self):
            return None

    def fake_urlopen(req, timeout):
        del req, timeout
        raise error.HTTPError(
            url="http://example/api/resumen",
            code=400,
            msg="bad",
            hdrs=None,
            fp=_ErrPayload(),
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(ApiClientError, match="HTTP 400"):
        client.get_summary()
