import helper
import pytest

import peeringdb
from peeringdb import resource

client = helper.client_fixture("full")
NET0 = 1


def test_nonexistent_config():
    with pytest.raises(Exception):
        peeringdb.client.Client({})


def test_get(client):
    assert client.get(resource.Network, NET0)
    with pytest.raises(Exception):
        client.get(resource.Network, 9999)


def test_update_all(client):
    client.update_all()
    assert client.get(resource.Network, NET0)


def test_type_wrap(client):
    assert client.tags.net.get(NET0)
    assert client.tags.net.all()


def test_client_cfg_none_loads_default(client, monkeypatch):
    monkeypatch.setattr("peeringdb.client.config.load_config", lambda: helper.CONFIG)
    c = peeringdb.client.Client(cfg=None)
    assert c.config is helper.CONFIG


def test_client_non_dict_sync_falls_back(client):
    c = peeringdb.client.Client(
        {"orm": {"backend": "django_peeringdb"}, "sync": "notadict"}
    )
    assert c.fetcher.url == ""
