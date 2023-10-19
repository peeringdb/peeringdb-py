import copy
import json
import os
import tempfile
from unittest.mock import patch

import pytest
import requests
from helper import CONFIG_CACHING

import peeringdb.resource as resource
from peeringdb._fetch import Fetcher
from peeringdb.client import Client
from peeringdb.resource import _NAMES as objs
from peeringdb.resource import RESOURCES_BY_TAG

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
        result = fetcher._fetch_cache(RESOURCES_BY_TAG[tag])
        assert result == test_data["data"]

        cache_file = os.path.join(fetcher.cache_dir, f"{tag}-0.json")

        # Check that the cache file was created
        assert os.path.exists(cache_file)

        # Check the content of the cache file
        with open(cache_file) as f:
            data = json.load(f)
        assert data == test_data


@pytest.mark.parametrize("tag", tags)
@patch("requests.get")
def test_fetch_cache_error(mock_get, fetcher, tag):
    """
    Test the _fetch_cache method when the server returns an error
    """
    # Mock the response from the server
    mock_response = requests.Response()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    # Call the method and check the exception

    with tempfile.TemporaryDirectory() as cache_dir:
        fetcher.cache_dir = cache_dir
        with pytest.raises(Exception) as e:
            fetcher._fetch_cache(RESOURCES_BY_TAG[tag])
        assert str(e.value) == f"Failed to download JSON file for {tag}"


@patch("requests.get")
def test_cache_used(mock_get, fetcher):
    """
    Test that cache is downloaded and used. Instead of parametrizing per tag,
    this function now reads the tag from the url its requesting.
    """

    def side_effect(url, *args, **kwargs):
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
        client.update_all()

        # objects in database
        assert model.objects.all().count()

        # cache downloaded and used
        # cache file NOT used
        assert client._fetcher.cache_downloaded
        assert not client._fetcher.cache_file_used

        # update
        client = Client(config)
        client.update_all()

        # cache not downloaded
        # cache file not used
        assert not client._fetcher.cache_downloaded
        assert not client._fetcher.cache_file_used

        client.backend.delete_all()


@patch("requests.get")
def test_cache_file_used(mock_get, fetcher):
    """
    Test that cache is downloaded and used. Instead of parametrizing per tag,
    this function now reads the tag from the url its requesting.
    """

    def side_effect(url, *args, **kwargs):
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

        client.update_all()

        # cache downloaded
        # cache file NOT used

        assert client._fetcher.cache_downloaded
        assert not client._fetcher.cache_file_used

        # wipe database (cache files still exist)

        client.backend.delete_all()

        # update

        client = Client(config)
        client.update_all()

        # cache NOT downloaded
        # cache file used

        assert not client._fetcher.cache_downloaded
        assert client._fetcher.cache_file_used

        assert model.objects.all().count()

        client.backend.delete_all()
