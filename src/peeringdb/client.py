from collections import OrderedDict

import munge.util

from peeringdb import (
    backend_initialized,
    config,
    get_backend,
    initialize_backend,
    resource,
)
from peeringdb._update import Updater
from peeringdb.fetch import Fetcher


class _Query:
    """Wrapper to access a specific resource"""

    def __init__(self, client, res):
        self.client = client
        self.res = res

    def get(self, pk):
        return self.client.get(self.res, pk)

    def all(self, **kwargs):
        return self.client.all(self.res, **kwargs)


class Client:
    """Main PeeringDB client."""

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
        orm_config = cfg["orm"]
        orm_name = orm_config["backend"]
        if not backend_initialized():
            initialize_backend(orm_name, **orm_config)

        sync_config = cfg["sync"]
        # override config with kwargs
        munge.util.recursive_update(sync_config, kwargs)

        self.fetcher = Fetcher(**sync_config)
        self.updater = Updater(self.fetcher)

        tag_res = OrderedDict(
            [(res.tag, _Query(self, res)) for res in resource.all_resources()]
        )
        tag_attrs = {
            **tag_res,
            **{
                "keys": lambda self: list(tag_res.keys()),
                "all": lambda self: list(tag_res.values()),
            },
        }
        self._Tags = type("_Tags", (), tag_attrs)
        self.tags = self._Tags()

    def get(self, res, pk):
        """Get a resource instance by primary key (id)"""
        backend = get_backend()
        return backend.get_object(backend.get_concrete(res), pk)

    def all(self, res):
        """Get resources using a filter condition"""
        backend = get_backend()
        return backend.get_objects(backend.get_concrete(res))

    @property
    def backend(self):
        return get_backend()
