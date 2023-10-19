import base64
import json
import logging
import os
import re
import time
import urllib

import requests

from peeringdb.private import PRIVATE_OBJECTS


class CompatibilityError(Exception):
    pass


class Fetcher:
    def __init__(
        self, url: str, timeout: int, api_key: str = "", cache_url: str = "", **kwargs
    ):
        """
        Construct a new Fetcher
        :param url: PeeringDB API URL
        :param timeout: HTTP query timeout
        :param api_key: API key
        :param cache_url: PeeringDB cache URL
        :param cache_dir: Local cache directory
        :param kwargs:
        """
        self._log = logging.getLogger(__name__)

        self.resources = {}
        self.url = url
        self.timeout = timeout or 60
        self.api_key = api_key
        self.cache_url = cache_url
        self.cache_dir = os.path.expanduser(
            kwargs.get("cache_dir", "~/.cache/peeringdb")
        )
        self.user = kwargs.get("user", "")
        self.password = kwargs.get("password", "")

        # Used for testing
        self.remote_cache_used = False
        self.local_cache_used = False

    def _get(self, endpoint: str, **params):
        url = f"{self.url}/{endpoint}"
        url_params = urllib.parse.urlencode(params)
        if url_params:
            url = f"{url}?{url_params}"
        headers = {}
        if self.api_key != "":
            headers = {"Authorization": "Api-Key " + self.api_key}
        elif self.user:
            # basic auth
            headers = {
                "Authorization": "Basic "
                + base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
            }

        resp = requests.get(url, timeout=self.timeout, headers=headers)

        if resp.status_code == 429:
            raise ValueError(f"Rate limited: {resp.text}")
        elif resp.status_code == 400:
            error = resp.json()["meta"]["error"]
            if re.search("client version is incompatible", error):
                raise CompatibilityError(error)
            raise
        elif resp.status_code != 200:
            raise ValueError(f"Error fetching {url}: {resp.status_code}")
        return resp.json()["data"]

    def load(
        self,
        resource: str,
        since: int = 0,
        fetch_private: bool = False,
        initial_private: bool = False,
    ):
        """
        Load a resource from mock data.
        :param resource: Resource tag (i.e. "net")
        :param since: Unix timestamp of last update (0 for all)
        :param fetch_private: Fetch private data (poc, ixlan)
        :param initial_private: private data has never been fetched before.
        """
        if resource in self.resources:
            return

        cache_file = os.path.join(self.cache_dir, f"{resource}-0.json")

        fetch_private = fetch_private and resource in PRIVATE_OBJECTS

        # Load from local cache if <15m old
        if (
            not since
            and os.path.exists(cache_file)
            and os.path.getmtime(cache_file) > (time.time() - 15 * 60)
        ):
            self._log.info(f"[{resource}] Fetching from local cache")
            with open(cache_file) as f:
                self.resources[resource] = json.load(f)["data"]
            self.local_cache_used = True

        # Fetch from remote cache if available
        elif not since and self.cache_url and not fetch_private:
            self._log.info(f"[{resource}] Fetching from remote cache")

            resp = requests.get(
                f"{self.cache_url}/{resource}-0.json", timeout=self.timeout
            )

            if resp.status_code == 200:
                # make sure dir exists
                os.makedirs(self.cache_dir, exist_ok=True)

                with open(cache_file, "w") as f:
                    f.write(resp.text)
                self.resources[resource] = resp.json()["data"]
                self.remote_cache_used = True
            else:
                raise ValueError(
                    f"Error fetching {resource} @ {self.cache_url}/{resource}.json from remote cache: {resp.status_code}"
                )

        # Fall back to fetching from API
        else:
            if fetch_private and initial_private:
                # Fetch private data for the first time, so we reset the
                # since parameter to grab all objects.
                since = None

            self._log.info(
                f"[{resource}] Fetching from API {'(private)' if fetch_private else ''}"
            )
            if not since or since == 0:
                self.resources[resource] = self._get(resource)
            else:
                self.resources[resource] = self._get(resource, since=since)

    def entries(self, tag: str):
        """
        Get all entries by tag ro load it if we don't already have the resource
        :param tag: Resource tag (i.e. "net")
        :return:
        """
        if tag not in self.resources:
            self.load(tag)
        return self.resources[tag]

    def get(self, tag: str, pk: int, depth: int = 0):
        """
        Get an individual object or attempt to query
        :param tag: Resource tag (i.e. "net")
        :param pk: Primary key
        :param depth: Depth of related objects to fetch
        """
        if tag not in self.resources:
            objs = self._get(tag, since=1, id=pk, depth=depth)
            if len(objs) > 0:
                return objs[0]
        for row in self.resources[tag]:
            if row["id"] == pk:
                return row
        objs = self._get(tag, since=1, id=pk, depth=depth)
        if len(objs) > 0:
            return objs[0]
        raise ValueError(f"Object {tag} {pk} not found")
