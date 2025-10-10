from collections import OrderedDict
from typing import TYPE_CHECKING, Optional, Union

import munge.util

from peeringdb import (
    _config_logs,
    backend_initialized,
    config,
    get_backend,
    initialize_backend,
    resource,
)
from peeringdb._update import Updater
from peeringdb.fetch import Fetcher

if TYPE_CHECKING:
    from peeringdb.backend import Interface


class _Query:
    """Wrapper to access a specific resource"""

    def __init__(self, client: "Client", res: type) -> None:
        self.client = client
        self.res = res

    def get(self, pk: Union[int, str]) -> object:
        return self.client.get(self.res, pk)

    def all(self, **kwargs: object) -> object:
        return self.client.all(self.res, **kwargs)


class Client:
    """Main PeeringDB client."""

    def __init__(
        self, cfg: Optional[dict[str, object]] = None, **kwargs: object
    ) -> None:
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
        self.config: dict[str, object] = cfg
        log_config = cfg.get("log", {}) if isinstance(cfg, dict) else {}
        if isinstance(log_config, dict):
            _config_logs(**log_config)
        orm_config = cfg.get("orm", {}) if isinstance(cfg, dict) else {}
        orm_name = orm_config.get("backend", "") if isinstance(orm_config, dict) else ""
        if not backend_initialized():
            if isinstance(orm_config, dict):
                initialize_backend(orm_name, **orm_config)

        sync_config = cfg.get("sync", {}) if isinstance(cfg, dict) else {}
        # override config with kwargs
        if isinstance(kwargs, dict) and isinstance(sync_config, dict):
            munge.util.recursive_update(sync_config, kwargs)

        if isinstance(sync_config, dict):
            self.fetcher = Fetcher(**sync_config)
        else:
            self.fetcher = Fetcher(url="", timeout=60)
        self.updater: Updater = Updater(self.fetcher)

        tag_res = OrderedDict(
            [
                (getattr(res, "tag", ""), _Query(self, res))
                for res in resource.all_resources()
            ]
        )
        tag_attrs = {
            **tag_res,
            **{
                "keys": lambda self: list(tag_res.keys()),
                "all": lambda self: list(tag_res.values()),
            },
        }
        self._Tags: type = type("_Tags", (), tag_attrs)
        self.tags: object = self._Tags()

    def get(self, res: type, pk: Union[int, str]) -> object:
        """Get a resource instance by primary key (id)"""
        backend = get_backend()
        return backend.get_object(backend.get_concrete(res), pk)

    def all(self, res: type) -> object:
        """Get resources using a filter condition"""
        backend = get_backend()
        return backend.get_objects(backend.get_concrete(res))

    def update_all(self) -> None:
        """Update all resources from the API."""
        return self.updater.update_all(resource.all_resources())

    @property
    def backend(self) -> "Interface":
        return get_backend()
