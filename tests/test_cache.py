import copy
import json
import os
import tempfile
from unittest.mock import patch

import pytest
import requests
from helper import CONFIG_CACHING

from peeringdb.client import Client
from peeringdb.fetch import Fetcher
from peeringdb.resource import _NAMES as RESOURCE_NAMES
from peeringdb.resource import all_resources

tags = RESOURCE_NAMES.keys()


@pytest.fixture
def fetcher():
    """
    Pytest fixture to create a Fetcher instance for each test
    """
    return Fetcher(**CONFIG_CACHING["sync"])


@pytest.mark.parametrize(
    "url,cache_url,expected_url,expected_cache_url",
    [
        (
            "https://www.peeringdb.com/api",
            "https://public.peeringdb.com",
            "https://www.peeringdb.com/api",
            "https://public.peeringdb.com",
        ),
        (
            "https://www.peeringdb.com/api/",
            "https://public.peeringdb.com/",
            "https://www.peeringdb.com/api",
            "https://public.peeringdb.com",
        ),
        (
            "https://www.peeringdb.com/api///",
            "https://public.peeringdb.com///",
            "https://www.peeringdb.com/api",
            "https://public.peeringdb.com",
        ),
        ("", "", "", ""),
    ],
)
def test_fetcher_url_normalization(url, cache_url, expected_url, expected_cache_url):
    """
    Trailing slashes on url and cache_url must be stripped so that
    f"{self.url}/{endpoint}" concatenations don't produce `//`.
    """
    fetcher = Fetcher(url=url, timeout=60, cache_url=cache_url)
    assert fetcher.url == expected_url
    assert fetcher.cache_url == expected_cache_url


@pytest.mark.parametrize("tag", tags)
@patch("requests.get")
def test_fetch_cache(mock_get, fetcher, tag):
    """
    Test the _fetch_cache method
    """
    # Load the test data from a file
    with open(f"tests/data/cache/{tag}-0.json") as f:
        test_data = json.load(f)

    # Mock the response from the server
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = json.dumps(test_data).encode()
    mock_get.return_value = mock_response

    with tempfile.TemporaryDirectory() as cache_dir:
        fetcher.cache_dir = cache_dir
        # Call the method and check the result
        result = fetcher.entries(tag)
        assert result == test_data["data"]
        assert fetcher.remote_cache_used

        cache_file = os.path.join(fetcher.cache_dir, f"{tag}-0.json")

        # Check that the cache file was created
        assert os.path.exists(cache_file)

        # Check the content of the cache file
        with open(cache_file) as f:
            data = json.load(f)
        assert data == test_data


@patch("requests.get")
def test_cache_used(mock_get, fetcher):
    """
    Test that cache is downloaded and used. Instead of parametrizing per tag,
    this function now reads the tag from the url its requesting.
    """

    def side_effect(url, *args, **kwargs):
        if "?since" in url:
            mock_response = requests.Response()
            mock_response.status_code = 200
            mock_response._content = json.dumps({"data": []}).encode()
            return mock_response

        # Extract the tag from the url
        file = url.split("/")[-1]

        print("URL", url, file)

        # Load the test data from a file
        with open(f"tests/data/cache/{file}") as f:
            test_data = json.load(f)

        assert len(test_data["data"])

        # Mock the response from the server
        mock_response = requests.Response()
        mock_response.status_code = 200
        mock_response._content = json.dumps(test_data).encode()

        return mock_response

    mock_get.side_effect = side_effect

    with tempfile.TemporaryDirectory() as cache_dir:
        config = copy.deepcopy(CONFIG_CACHING)
        config["sync"]["cache_dir"] = cache_dir
        client = Client(config)

        from django_peeringdb.models.concrete import tag_dict

        model = tag_dict["org"]

        # 0 objects in database
        assert model.objects.all().count() == 0

        # update
        client.updater.update_all(all_resources())

        # objects in database
        assert model.objects.all().count()

        assert not client.fetcher.local_cache_used

        # update
        client = Client(config)
        client.updater.update_all(all_resources())

        assert not client.fetcher.local_cache_used

        client.backend.delete_all()


@patch("requests.get")
def test_proxy_passed_to_api_get(mock_get):
    """Proxy setting is forwarded to requests.get for API calls."""
    proxy_url = "http://proxy.example.com:3128"
    fetcher = Fetcher(
        url="https://test.peeringdb.com/api",
        timeout=0,
        proxy=proxy_url,
    )

    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = json.dumps({"data": []}).encode()
    mock_get.return_value = mock_response

    fetcher._get("net")

    _, kwargs = mock_get.call_args
    assert kwargs.get("proxies") == {"http": proxy_url, "https": proxy_url}


@patch("requests.get")
def test_proxy_passed_to_cache_fetch(mock_get):
    """Proxy setting is forwarded to requests.get for remote cache fetches."""
    proxy_url = "http://proxy.example.com:3128"
    fetcher = Fetcher(
        url="https://test.peeringdb.com/api",
        timeout=0,
        cache_url="cache://localhost",
        proxy=proxy_url,
    )

    with open("tests/data/cache/net-0.json") as f:
        test_data = json.load(f)

    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = json.dumps(test_data).encode()
    mock_get.return_value = mock_response

    with tempfile.TemporaryDirectory() as cache_dir:
        fetcher.cache_dir = cache_dir
        fetcher.entries("net")

    _, kwargs = mock_get.call_args
    assert kwargs.get("proxies") == {"http": proxy_url, "https": proxy_url}


@patch("requests.get")
def test_cache_file_used(mock_get, fetcher):
    """
    Test that cache is downloaded and used. Instead of parametrizing per tag,
    this function now reads the tag from the url its requesting.
    """

    def side_effect(url, *args, **kwargs):
        if "?since" in url:
            mock_response = requests.Response()
            mock_response.status_code = 200
            mock_response._content = json.dumps({"data": []}).encode()
            return mock_response

        # Extract the tag from the url
        file = url.split("/")[-1]
        print("URL", url, file)

        # Load the test data from a file
        with open(f"tests/data/cache/{file}") as f:
            test_data = json.load(f)

        assert len(test_data["data"])

        # Mock the response from the server
        mock_response = requests.Response()
        mock_response.status_code = 200
        mock_response._content = json.dumps(test_data).encode()

        return mock_response

    mock_get.side_effect = side_effect

    with tempfile.TemporaryDirectory() as cache_dir:
        config = copy.deepcopy(CONFIG_CACHING)
        config["sync"]["cache_dir"] = cache_dir
        client = Client(config)

        from django_peeringdb.models.concrete import tag_dict

        model = tag_dict["org"]

        # 0 objects in database
        assert model.objects.all().count() == 0

        # update

        client.updater.update_all(all_resources())

        # wipe database (cache files still exist)

        client.backend.delete_all()

        # update

        client = Client(config)
        client.updater.update_all(all_resources())

        assert model.objects.all().count()

        client.backend.delete_all()


def _api_response(payload):
    resp = requests.Response()
    resp.status_code = 200
    resp._content = json.dumps(payload).encode()
    return resp


@patch("requests.get")
def test_private_object_bypasses_remote_cache_and_hits_api(mock_get):
    """A private object with fetch_private=True must skip the remote cache
    (which has no private fields) and fetch from the API instead (#92)."""
    mock_get.side_effect = lambda url, *a, **k: _api_response({"data": [{"id": 1}]})

    with tempfile.TemporaryDirectory() as cache_dir:
        fetcher = Fetcher(
            url="https://test.peeringdb.com/api",
            timeout=0,
            api_key="testkey",
            cache_url="https://public.peeringdb.com",
            cache_dir=cache_dir,
        )
        fetcher.load("ixlan", since=None, fetch_private=True)

    urls = [call.args[0] for call in mock_get.call_args_list]
    assert urls, "expected at least one request"
    # remote cache was never contacted...
    assert all("public.peeringdb.com" not in u for u in urls)
    assert fetcher.remote_cache_used is False
    # ...the API was
    assert any("test.peeringdb.com/api/ixlan" in u for u in urls)


@patch("requests.get")
def test_private_incremental_passes_since_to_api(mock_get):
    """The since_private watermark the caller passes must reach the API query."""
    mock_get.side_effect = lambda url, *a, **k: _api_response({"data": []})

    with tempfile.TemporaryDirectory() as cache_dir:
        fetcher = Fetcher(
            url="https://test.peeringdb.com/api",
            timeout=0,
            api_key="testkey",
            cache_url="https://public.peeringdb.com",
            cache_dir=cache_dir,
        )
        fetcher.load("ixlan", since=201, fetch_private=True)

    urls = [call.args[0] for call in mock_get.call_args_list]
    assert any("ixlan?since=201" in u for u in urls)


@patch("requests.get")
def test_private_sync_writes_and_reuses_since_private_watermark(mock_get, tmp_path):
    """End-to-end through the real backend: a --fetch-private sync seeds the
    since_private watermark for each private resource, and the next sync fetches
    them incrementally from the watermark (windowed by the #135 lookback)."""

    def side_effect(url, *args, **kwargs):
        resp = requests.Response()
        resp.status_code = 200
        # incremental API queries return nothing new
        if "?since=" in url:
            resp._content = json.dumps({"data": []}).encode()
            return resp
        # serve any resource from the shared fixtures, whether requested as an
        # API path (".../ixlan") or a cache file (".../ixlan-0.json")
        tag = url.rstrip("/").split("/")[-1].replace("-0.json", "")
        try:
            with open(f"tests/data/cache/{tag}-0.json") as f:
                resp._content = f.read().encode()
        except FileNotFoundError:
            resp._content = json.dumps({"data": []}).encode()
        return resp

    mock_get.side_effect = side_effect

    config = copy.deepcopy(CONFIG_CACHING)
    config["sync"]["cache_dir"] = str(tmp_path)
    api_url = config["sync"]["url"].rstrip("/")

    client = Client(config)
    rs = all_resources()

    # first --fetch-private sync: full fetch, then seed the watermark
    client.updater.update_all(rs, fetch_private=True)

    state_file = tmp_path / ".since-private.json"
    assert state_file.exists()
    state = json.loads(state_file.read_text())
    assert isinstance(state[api_url]["ixlan"], int)
    assert isinstance(state[api_url]["poc"], int)
    ixlan_ts = state[api_url]["ixlan"]

    # second sync: ixlan is fetched incrementally from the watermark, not in
    # full. Use a fresh Client so the fetcher's in-memory resource cache is
    # empty (each real CLI run is a new process); same DB + cache dir persist.
    mock_get.reset_mock()
    client = Client(config)
    client.updater.update_all(rs, fetch_private=True)
    urls = [call.args[0] for call in mock_get.call_args_list]
    expected_since = client.updater._since_param(ixlan_ts)
    assert any(f"ixlan?since={expected_since}" in u for u in urls)

    client.backend.delete_all()


@patch("requests.get")
def test_private_fetch_ignores_fresh_public_local_cache(mock_get, tmp_path):
    """A --fetch-private run must NOT read a fresh public local cache file.

    The first private fetch passes since=None (watermark unset), which reaches
    the local-cache branch. The local cache file only ever holds the public
    payload (no private fields), so without the not-fetch-private guard it would
    load public data and silently skip private data — reintroducing #92 on the
    canonical "public sync, then --fetch-private within 15m" first-run flow.
    """
    # a fresh public cache file left by a prior non-private sync (url is null)
    public = {"data": [{"id": 1, "ixf_ixp_member_list_url": None}]}
    (tmp_path / "ixlan-0.json").write_text(json.dumps(public))

    api = {"data": [{"id": 1, "ixf_ixp_member_list_url": "https://example.com/ixf"}]}
    mock_get.side_effect = lambda url, *a, **k: _api_response(api)

    fetcher = Fetcher(
        url="https://test.peeringdb.com/api",
        timeout=0,
        api_key="testkey",
        cache_url="https://public.peeringdb.com",
        cache_dir=str(tmp_path),
    )
    fetcher.load("ixlan", since=None, fetch_private=True)

    # went to the API, not the fresh public local cache
    assert fetcher.local_cache_used is False
    urls = [call.args[0] for call in mock_get.call_args_list]
    assert any("test.peeringdb.com/api/ixlan" in u for u in urls)
    assert fetcher.resources["ixlan"] == api["data"]
