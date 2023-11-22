import helper
import pytest

import peeringdb
from peeringdb.client import Client
from peeringdb.resource import Network, Organization, all_resources

# first net id
FIRST_NET = 1


def get_client():
    return Client(helper.CONFIG)


# test single-object, aka. partial sync (disabled in release)
def get_pclient():
    c = Client(helper.CONFIG)
    return c


client_dup = helper.client_fixture("full_nonunique")


def test_full(client_empty):
    client = get_client()
    rs = all_resources()
    client.updater.update_all(rs)
    assert client.get(Network, FIRST_NET)


# Ensure fetching is not order-dependent
def test_reversed(client_empty):
    client = client_empty
    # sanity check for empty client
    B = peeringdb.get_backend()
    with pytest.raises(B.object_missing_error()):
        client.get(Network, FIRST_NET)

    rs = all_resources()
    rs = reversed(rs)
    client.updater.update_all(rs)


def test_single_disabled(client_empty):
    client = client_empty
    with pytest.raises(Exception):
        client.update(Network, FIRST_NET)


def test_single(client_empty):
    client = get_pclient()
    client.updater.update_one(Network, FIRST_NET)
    assert client.get(Network, FIRST_NET)
    # and no invalid references
    assert client.get(Organization, FIRST_NET)


def test_single_deep(client_empty):
    client = get_pclient()
    client.updater.update_one(Network, FIRST_NET, depth=2)
    assert client.get(Network, FIRST_NET)
    assert client.get(Organization, FIRST_NET)


# Test sync where update would result in a duplicate field
# Test data should include: swapped case; deleted case
def test_nonunique(client_dup):
    client = client_dup
    # sanity check - do we actually have a duplicate
    swapdup = client.get(Network, 2)
    d = client.fetcher._get("net", id=FIRST_NET)[0]

    swapdup.name = d["name"]
    swapdup.save()
    assert d["name"] == swapdup.name

    # obj that doesn't exist remotely
    assert client.get(Network, 4)

    client.updater.update_one(Network, FIRST_NET)

    assert client.get(Network, FIRST_NET)

    # remotely deleted dup should be gone
    # FIXME: this needs adjustment of data on test.peeringdb.com in the form
    # of a deleted network.
    # B = peeringdb.get_backend()
    # with pytest.raises(B.object_missing_error()):
    #    client.get(Network, 4)


def test_nonunique_single(client_dup):
    client = get_pclient()
    client.updater.update_one(Network, FIRST_NET)
    assert client.get(Network, FIRST_NET)


@pytest.mark.sync
def test_auth(client_empty):
    with pytest.raises(ValueError):
        config = helper.CONFIG
        config["sync"]["user"] = "test"
        config["sync"]["password"] = "test"
        config["sync"]["api_key"] = "test"
        client = Client(config, dry_run=True)
        rs = all_resources()
        client.updater.update_all(rs, 0)
        client.get(Network, FIRST_NET)


# TODO:

# data integrity (needs mocking?)

# test for ignoring objects created after sync begins
