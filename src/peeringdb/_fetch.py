"""
RPC / REST client implementation module
"""
import json
import logging
import os
import re
import time

import requests
from twentyc.rpc import RestClient
from twentyc.rpc.client import (
    InvalidRequestException,
    NotFoundException,
    PermissionDeniedException,
)

import peeringdb


class CompatibilityError(Exception):
    pass


class Fetcher(RestClient):
    """
    REST client with some patches
    """

    def __init__(self, **kwargs):
        # self.return_error = True
        self.api_key = kwargs.get("api_key", "")
        self.cache_url = kwargs.get("cache_url")
        self.cache_dir = os.path.expanduser(
            kwargs.get("cache_dir", "~/.cache/peeringdb")
        )
        self._log = logging.getLogger(__name__)

        self.cache_downloaded = None
        self.cache_file_used = None

        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        super().__init__(**kwargs)

    def _req(self, func):
        try:
            return func(), None
        except NotFoundException as e:  # 404
            return {}, e
        except PermissionDeniedException as e:  # 401
            return {}, e
        except InvalidRequestException as e:
            pattern = "client version is incompatible"
            error = e.extra["meta"]["error"]
            if re.search(pattern, error):
                raise CompatibilityError(error)
            raise

    def fetch(self, R, pk, depth):
        return self._req(lambda: self.get(R.tag, pk, depth=depth))

    def fetch_latest(self, R, pk, depth, since=None):
        backend = peeringdb.get_backend()
        if since is None:
            since = backend.last_change(backend.get_concrete(R))
        if since:
            since = since + 1
        return self._req(lambda: self.get(R.tag, pk, since=since, depth=depth))

    def fetch_all(self, R, depth, params={}):
        params = {
            k: ",".join(map(str, v)) if isinstance(v, (list, tuple)) else v
            for k, v in params.items()
        }
        return self._req(lambda: self.all(R.tag, depth=depth, **params))

    def _fetch_cache(self, R):
        """
        Will fetch the latest version of the object from the cache
        This is only done on empty databases (e.g., when all the data needs
        to be fetched)

        It will also use a local file cache that lasts 15 minutes.
        """
        ref_tag = R.tag
        cache_url = self.cache_url

        # check if we have an existing cache file

        cache_file = os.path.join(self.cache_dir, f"{ref_tag}-0.json")
        if os.path.exists(cache_file):
            # get file modification time
            mtime = os.path.getmtime(cache_file)

            # if not older than 15 mins return from file
            if time.time() - mtime < 15 * 60:
                self._log.debug(f"Using cached file {cache_file}")
                with open(cache_file) as f:
                    # this is currently only used for testing purposes (so we can easily
                    # check if the cache file was used)
                    self.cache_file_used = True

                    # return cache file contents
                    return json.load(f)["data"]

        # no file cache, load data from cache url
        url = f"{cache_url}/{ref_tag}-0.json"
        self._log.debug(f"Downloading from cache: {url}")
        response = requests.get(url)

        # this is currently only used for testing purposes (so we can easily
        # check if the cache download was used)
        self.cache_downloaded = True

        if response.status_code == 200:
            # write cache file
            with open(os.path.join(self.cache_dir, f"{ref_tag}-0.json"), "w") as f:
                f.write(response.text)

            # return data
            return response.json()["data"]
        else:
            raise Exception(f"Failed to download JSON file for {ref_tag}")

    def fetch_all_latest(self, R, depth, params={}, since=None):
        backend = peeringdb.get_backend()

        if since is None:
            since = backend.last_change(backend.get_concrete(R))

        if not since and self.cache_url and not params and not depth:
            # empty database, do full data update from cache server

            return self._req(lambda: self._fetch_cache(R))

        if since:
            since = since + 1
        params = {
            k: ",".join(map(str, v)) if isinstance(v, (list, tuple)) else v
            for k, v in params.items()
        }
        return self._req(lambda: self.all(R.tag, since=since, depth=depth, **params))

    def fetch_deleted(self, R, pk, depth):
        def req():
            return self.all(R.tag, id=pk, since=1, depth=depth)

        return self._req(req)

    # fixme:
    # RestClient monkeypatches to add headers to request

    def get(self, typ, id, **kwargs):
        """
        Load type by id
        """
        return self._load(self._request(typ, id=id, params=kwargs))

    def _request(self, typ, id=0, method="GET", params=None, data=None, url=None):
        """
        send the request, return response obj
        """
        backend, backend_version = peeringdb.get_backend_info()
        user_agent = "PeeringDB/{} {}/{}".format(
            peeringdb.__version__, backend, backend_version
        )

        headers = {
            "Accept": "application/json",
            "User-Agent": user_agent,
        }
        auth = None

        if self.user:
            auth = (self.user, self.password)
        if not url:
            if id:
                url = f"{self.url}/{typ}/{id}"
            else:
                url = f"{self.url}/{typ}"

        if auth and self.api_key:
            raise ValueError("Cannot use both API key and basic auth")

        if auth:
            response = requests.request(
                method, url, params=params, data=data, auth=auth, headers=headers
            )

            if response.status_code == 401:
                raise ValueError(
                    "Authentication failed: {}".format(
                        response.json().get("meta", {}).get("error", "")
                    )
                )
            return response

        if self.api_key:
            headers["Authorization"] = f"Api-Key {self.api_key}"
            response = requests.request(
                method, url, params=params, data=data, headers=headers
            )
            if response.status_code == 401:
                raise ValueError(
                    "Authentication failed: {}".format(
                        response.json().get("meta", {}).get("error", "")
                    )
                )
            return response

        if not auth or not self.api_key:
            response = requests.request(
                method, url, params=params, data=data, headers=headers
            )

            return response
