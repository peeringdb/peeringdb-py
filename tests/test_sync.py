import pytest

import helper
import peeringdb
from peeringdb.resource import all_resources, Network, Organization

# first net id
FIRST_NET = 7

# allows incomplete (or partial) syncs
class _PartialEnabledContext(peeringdb.sync.UpdateContext):
    def __init__(self, *args):
        super().__init__(*args)
        self.disable_partial = False


def get_client():
    return peeringdb.PeeringDB(helper.CONFIG)


# test single-object, aka. partial sync (disabled in release)
def get_pclient():
    c = peeringdb.PeeringDB(helper.CONFIG)
    c._updater._ContextClass = _PartialEnabledContext
    return c


client_dup = helper.client_fixture("full_nonunique")


def test_full(client_empty):
    client = get_client()
    rs = all_resources()
    client.update_all(rs)
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
    client.update_all(rs)


def test_single_disabled(client_empty):
    client = client_empty
    with pytest.raises(Exception):
        client.update(Network, FIRST_NET)


def test_single(client_empty):
    client = get_pclient()
    client.update(Network, FIRST_NET)
    assert client.get(Network, FIRST_NET)
    # and no invalid references
    assert client.get(Organization, FIRST_NET)


def test_single_deep(client_empty):
    client = get_pclient()
    client.update(Network, FIRST_NET, depth=2)
    assert client.get(Network, FIRST_NET)
    assert client.get(Organization, FIRST_NET)


def test_selection(client_empty):
    client = get_pclient()
    client.update_where(Network, name="net 7205f40e", since=0)
    assert client.get(Network, FIRST_NET)

    client.update_where(Network, id__in=[8, 9], since=0)
    assert client.get(Network, 8)
    assert client.get(Network, 9)


# Test sync where update would result in a duplicate field
# Test data should include: swapped case; deleted case
def test_nonunique(client_dup):
    client = client_dup
    # sanity check - do we actually have a duplicate
    swapdup = client.get(Network, 9)
    d = client._fetcher.fetch_latest(Network, FIRST_NET, 0, since=0)
    assert d[0][0]["name"] == swapdup.name

    # obj that doesn't exist remotely
    assert client.get(Network, 12)

    rs = all_resources()
    client.update_all(rs, since=0)

    assert client.get(Network, FIRST_NET)

    # remotely deleted dup should be gone
    B = peeringdb.get_backend()
    with pytest.raises(B.object_missing_error()):
        client.get(Network, 12)


def test_nonunique_single(client_dup):
    client = get_pclient()
    client.update(Network, FIRST_NET)
    assert client.get(Network, FIRST_NET)


# FIXME: when not placed last, breaks other tests:
# dry_run=True attribute gets set on ALL clients. wtf?
@pytest.mark.sync
def test_dry_run(client_empty):
    client = peeringdb.PeeringDB(helper.CONFIG, dry_run=True)
    rs = all_resources()
    client.update_all(rs)
    # still empty?
    with pytest.raises(peeringdb.get_backend().object_missing_error()):
        client.get(Network, FIRST_NET)


# TODO:

# data integrity (needs mocking?)

# test for ignoring objects created after sync begins
