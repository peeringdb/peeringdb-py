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
from peeringdb.resource import _NAMES as objs
from peeringdb.resource import all_resources

tags = objs.keys()


@pytest.fixture
def fetcher():
    """
    Pytest fixture to create a Fetcher instance for each test
    """
    return Fetcher(**CONFIG_CACHING["sync"])


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
