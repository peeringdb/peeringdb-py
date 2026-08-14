from unittest.mock import MagicMock

import pytest
import requests

from peeringdb.fetch import CompatibilityError, Fetcher


def _resp(status_code=200, json_data=None):
    """Build a fake requests.Response."""
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data if json_data is not None else {}
    if status_code >= 400:
        r.raise_for_status.side_effect = requests.exceptions.HTTPError()
    else:
        r.raise_for_status.return_value = None
    return r


def _fetcher():
    return Fetcher(url="https://example.com/api", timeout=1)


def test_get_success(monkeypatch):
    monkeypatch.setattr(
        "peeringdb.fetch.requests.get",
        lambda *a, **k: _resp(200, {"data": [{"id": 1}]}),
    )
    assert _fetcher()._get("net") == [{"id": 1}]


def test_get_bad_request(monkeypatch):
    monkeypatch.setattr(
        "peeringdb.fetch.requests.get",
        lambda *a, **k: _resp(400, {"meta": {"error": "nope"}}),
    )
    with pytest.raises(ValueError, match="Bad request error"):
        _fetcher()._get("net")


def test_get_incompatible_client_raises_compatibility_error(monkeypatch):
    monkeypatch.setattr(
        "peeringdb.fetch.requests.get",
        lambda *a, **k: _resp(
            400, {"meta": {"error": "client version is incompatible"}}
        ),
    )
    with pytest.raises(CompatibilityError):
        _fetcher()._get("net")


def test_get_server_error(monkeypatch):
    monkeypatch.setattr("peeringdb.fetch.requests.get", lambda *a, **k: _resp(500))
    with pytest.raises(ValueError, match="Error fetching"):
        _fetcher()._get("net")


def test_get_request_exception(monkeypatch):
    def _boom(*_a, **_k):
        raise requests.exceptions.ConnectionError("down")

    monkeypatch.setattr("peeringdb.fetch.requests.get", _boom)
    with pytest.raises(ValueError, match="Request error"):
        _fetcher()._get("net")


def test_get_rate_limited_then_succeeds(monkeypatch):
    responses = [_resp(429), _resp(200, {"data": ["ok"]})]
    monkeypatch.setattr(
        "peeringdb.fetch.requests.get", lambda *a, **k: responses.pop(0)
    )
    monkeypatch.setattr("peeringdb.fetch.time.sleep", lambda _s: None)

    fetcher = _fetcher()
    assert fetcher._get("net") == ["ok"]
    assert fetcher.attempt == 1


def test_get_sends_api_key_header(monkeypatch):
    captured = {}

    def _get(url, **kwargs):
        captured["headers"] = kwargs.get("headers")
        return _resp(200, {"data": []})

    monkeypatch.setattr("peeringdb.fetch.requests.get", _get)
    Fetcher(url="https://example.com/api", timeout=1, api_key="secret")._get("net")
    assert captured["headers"]["Authorization"] == "Api-Key secret"


def test_get_sends_basic_auth_header(monkeypatch):
    captured = {}

    def _get(url, **kwargs):
        captured["headers"] = kwargs.get("headers")
        return _resp(200, {"data": []})

    monkeypatch.setattr("peeringdb.fetch.requests.get", _get)
    Fetcher(url="https://example.com/api", timeout=1, user="u", password="p")._get(
        "net"
    )
    assert captured["headers"]["Authorization"].startswith("Basic ")


def test_load_returns_early_when_already_loaded(monkeypatch):
    def _boom(*_a, **_k):
        raise AssertionError("should not hit the network")

    monkeypatch.setattr("peeringdb.fetch.requests.get", _boom)
    fetcher = _fetcher()
    fetcher.resources["net"] = [{"id": 1}]
    fetcher.load("net")  # early-returns without fetching
    assert fetcher.resources["net"] == [{"id": 1}]


def test_load_remote_cache_error(monkeypatch):
    monkeypatch.setattr("peeringdb.fetch.requests.get", lambda *a, **k: _resp(404))
    fetcher = Fetcher(
        url="https://example.com/api", timeout=1, cache_url="https://cache.example.com"
    )
    with pytest.raises(ValueError, match="from remote cache"):
        fetcher.load("net", since=0)


def test_get_found_in_cache():
    fetcher = _fetcher()
    fetcher.resources["net"] = [{"id": 5, "name": "x"}]
    assert fetcher.get("net", 5) == {"id": 5, "name": "x"}


def test_get_force_fetch_returns_first(monkeypatch):
    monkeypatch.setattr(
        "peeringdb.fetch.requests.get",
        lambda *a, **k: _resp(200, {"data": [{"id": 7}]}),
    )
    assert _fetcher().get("net", 7, force_fetch=True) == {"id": 7}


def test_get_falls_back_to_api(monkeypatch):
    monkeypatch.setattr(
        "peeringdb.fetch.requests.get",
        lambda *a, **k: _resp(200, {"data": [{"id": 8}]}),
    )
    fetcher = _fetcher()
    fetcher.resources["net"] = [{"id": 1}]  # 8 not cached -> second _get finds it
    assert fetcher.get("net", 8) == {"id": 8}


def test_get_not_found_raises(monkeypatch):
    monkeypatch.setattr(
        "peeringdb.fetch.requests.get", lambda *a, **k: _resp(200, {"data": []})
    )
    fetcher = _fetcher()
    fetcher.resources["net"] = [{"id": 1}]
    with pytest.raises(ValueError, match="not found"):
        fetcher.get("net", 99)
