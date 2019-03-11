import munge.util
from peeringdb import config
from twentyc.rpc import RestClient

import peeringdb
from peeringdb import get_backend, resource
from peeringdb.resource import get_resource, Network
from peeringdb.sync import Updater, Fetcher


class _Query():
    "Wrapper to access a specific resource"

    def __init__(self, client, res):
        self.client = client
        self.res = res

    def get(self, pk):
        return self.client.get(self.res, pk)

    def all(self, **kwargs):
        return self.client.all(self.res, **kwargs)


class Client:
    "Main PeeringDB client."

    def __init__(self, cfg=None, **kwargs):
        """
        Arguments:
            - cfg <dict>: dict of complete config options (see config.ClientSchema),
                by default loads from DEFAULT_CONFIG_DIR
            - url<str>: URL to connect to
            - user<str>: username to connect to api with
            - password<str>: password
            - timeout<float>: timeout to fail after
        """
        if cfg is None:
            cfg = config.load_config()
        self.config = cfg
        orm_config = cfg['orm']
        orm_name = orm_config['backend']
        if not peeringdb.backend_initialized():
            peeringdb.initialize_backend(orm_name, **orm_config)

        sync_config = cfg['sync']
        # override config with kwargs
        munge.util.recursive_update(sync_config, kwargs)

        self._fetcher = Fetcher(**sync_config)
        self._updater = Updater(self._fetcher, **sync_config)

        self.update_all = self._updater.update_all
        self.update = self._updater.update
        self.update_where = self._updater.update_where

        tag_attrs = {
            res.tag: _Query(self, res)
            for res in resource.all_resources()
        }
        self._Tags = type('_Tags', (), tag_attrs)
        self.tags = self._Tags()

    def fetch(self, R, pk, depth=1):
        "Request object from API"
        d, e = self._fetcher.fetch(R, pk, depth)
        if e: raise e
        return d

    def fetch_all(self, R, depth=1, **kwargs):
        "Request multiple objects from API"
        d, e = self._fetcher.fetch_all(R, depth, kwargs)
        if e: raise e
        return d

    def get(self, res, pk):
        "Get a resource instance by primary key (id)"
        B = get_backend()
        return B.get_object(B.get_concrete(res), pk)

    def all(self, res):
        "Get resources using a filter condition"
        B = get_backend()
        return B.get_objects(B.get_concrete(res))
