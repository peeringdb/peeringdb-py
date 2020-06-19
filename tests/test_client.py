import pytest, os

import helper
import peeringdb
from peeringdb import resource

client = helper.client_fixture('insert_full.sql')
NET0 = 7

def test_nonexistent_config():
    with pytest.raises(Exception):
        peeringdb.client.Client({})

def test_get(client):
    assert client.get(resource.Network, NET0)
    with pytest.raises(Exception):
        client.get(resource.Network, 12)

def test_type_wrap(client):
    assert client.tags.net.get(NET0)
    assert client.tags.net.all()

def test_version_check(client_empty, patch_version, patch_backend_version):
    with patch_version:
        with pytest.raises(peeringdb.sync.CompatibilityError):
            client_empty.fetch(resource.Network, NET0)

    with patch_backend_version:
        with pytest.raises(peeringdb.sync.CompatibilityError):
            client_empty.fetch(resource.Network, NET0)
