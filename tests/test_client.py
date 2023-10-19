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


def test_type_wrap(client):
    assert client.tags.net.get(NET0)
    assert client.tags.net.all()
