import json
import os
from datetime import datetime
from types import SimpleNamespace

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
    backend = peeringdb.get_backend()
    with pytest.raises(backend.object_missing_error()):
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


def test_auto_resolve_unique_conflict(client_empty):
    # first load all entries
    client = get_client()
    rs = all_resources()
    client.updater.update_all(rs)

    # then manually change name of network with id 3
    net = client.get(Network, 3)

    net_3_remote_name = net.name

    net.name = "placeholder"
    client.updater.backend.save(net)

    # then manually change name of network with id 1
    # to the same name as network with id 3 creating
    # a conflict

    net = client.get(Network, 1)
    net.name = net_3_remote_name
    client.updater.backend.save(net)

    class DummyUniqueException:
        error_dict = {"name": "already exists"}

    row = client.fetcher._get("net", id=3)[0]
    client.updater.update_collision(Network, row, DummyUniqueException())

    # check if the conflict was resolved
    net = client.get(Network, 1)
    assert net.name != net_3_remote_name


def test_handle_initial_sync_success(client_empty):
    """
    Test successful initial sync using _handle_initial_sync.
    """
    client = get_client()
    rs = all_resources()

    # Sync only the first resource (Organization)
    client.updater._handle_initial_sync(client.fetcher.entries(rs[0].tag), rs[0])

    # Check if the first organization exists
    assert client.get(Organization, 1)


def test_handle_initial_sync_error(client_empty, monkeypatch):
    """
    Test error handling in _handle_initial_sync.
    """

    # Delete the file if exists
    if os.path.exists("failed_entries.json"):
        os.remove("failed_entries.json")

    client = get_client()
    rs = all_resources()

    # Mock create_obj to simulate an error for a specific object ID
    original_create_obj = client.updater.create_obj

    def mock_create_obj(row: dict, res):
        if row["id"] == 2:  # Simulate an error for object with ID 2
            raise ValueError("Simulating an error during object creation")
        return original_create_obj(row, res)

    monkeypatch.setattr(client.updater, "create_obj", mock_create_obj)

    client.updater._handle_initial_sync(client.fetcher.entries(rs[0].tag), rs[0])

    with pytest.raises(client.backend.object_missing_error()):
        client.get(Organization, 2)  # Object with ID 2 should be missing
    with open("failed_entries.json") as f:
        failed_objects = json.load(f)
        assert len(failed_objects) == 1
        assert failed_objects[0]["pk"] == 2

    # Delete the file after the test
    if os.path.exists("failed_entries.json"):
        os.remove("failed_entries.json")


def test_handle_incremental_sync_success(client_empty):
    """
    Test successful incremental sync using _handle_incremental_sync.
    """

    client = get_client()
    rs = all_resources()
    client.updater.update_all(rs)  # Do a full sync first
    client.updater._handle_incremental_sync(
        client.fetcher.entries(rs[0].tag), rs[0]
    )  # Incremental sync for Organizations
    assert client.get(Organization, 1)  # Check if the first organization still exists


def test_handle_incremental_sync_error(client_empty, monkeypatch):
    """
    Test error handling in _handle_incremental_sync.
    """
    # Delete the file if exists
    if os.path.exists("failed_entries.json"):
        os.remove("failed_entries.json")

    client = get_client()
    rs = all_resources()

    # Perform a full sync first
    client.updater.update_all(rs)

    # Mock copy_object to simulate an error for a specific object ID
    original_copy_object = client.updater.copy_object

    def mock_copy_object(new_obj):
        if new_obj.id == 1:  # Simulate an error for object with ID 1
            raise ValueError("Simulating an error during object update")
        return original_copy_object(new_obj)

    monkeypatch.setattr(client.updater, "copy_object", mock_copy_object)

    # Change detection (#135) skips rows whose `updated` matches the local
    # copy, so bump id 1's timestamp to force a genuine update through
    # copy_object (where the simulated error is raised).
    entries = client.fetcher.entries(rs[0].tag)
    for row in entries:
        if row["id"] == 1:
            row["updated"] = "2099-01-01T00:00:00"

    client.updater._handle_incremental_sync(
        entries, rs[0]
    )  # Incremental sync for Organizations

    # Assertions
    assert client.get(Organization, 1)  # Object with ID 1 should still exist
    with open("failed_entries.json") as f:
        failed_objects = json.load(f)
        assert len(failed_objects) >= 1
        assert any(
            entry["pk"] == 1 for entry in failed_objects
        )  # Check if object ID 1 is present

    # Delete the file if exists
    if os.path.exists("failed_entries.json"):
        os.remove("failed_entries.json")


def test_since_param_drops_plus_one_and_applies_lookback(client_empty):
    """
    #135: the incremental cursor must be `last_change - lookback`, never
    `last_change + 1` (which skipped objects changed in the boundary second).
    """
    client = get_client()
    upd = client.updater

    # full/initial sentinels -> None (full fetch)
    assert upd._since_param(None) is None
    assert upd._since_param(0) is None

    # default lookback is 1 -> cursor rewound by one second (re-includes the
    # boundary second; required for whole-second/mirror upstreams)
    assert upd._since_param(1000) == 999

    # lookback can be widened for replication-lag margin
    upd.config["sync"]["lookback"] = 5
    assert upd._since_param(1000) == 995

    # explicit 0 is honored (e.g. known sub-second upstream): cursor is _since,
    # never _since + 1
    upd.config["sync"]["lookback"] = 0
    assert upd._since_param(1000) == 1000

    # floored at 1 so a huge lookback can't collapse to 0 (== full fetch)
    upd.config["sync"]["lookback"] = 10_000
    assert upd._since_param(1000) == 1


def test_incremental_sync_skips_unchanged(client_empty):
    """
    #135: re-fetched rows that match the local copy must be skipped, not
    re-written (keeps the lookback window cheap and the output honest).
    """
    client = get_client()
    rs = all_resources()
    client.updater.update_all(rs)  # full sync

    # Same entries, nothing changed upstream -> all recognized as unchanged.
    counts = client.updater._handle_incremental_sync(
        client.fetcher.entries(rs[0].tag), rs[0]
    )
    assert counts["created"] == 0
    assert counts["updated"] == 0
    assert counts["unchanged"] > 0


def test_incremental_sync_applies_newer_timestamp(client_empty):
    """
    #135: an object whose `updated` is newer than the local copy is applied
    via the timestamp fast path; the rest stay unchanged.
    """
    client = get_client()
    rs = all_resources()
    client.updater.update_all(rs)

    entries = client.fetcher.entries(rs[0].tag)
    target = entries[0]["id"]
    for row in entries:
        if row["id"] == target:
            row["updated"] = "2099-01-01T00:00:00Z"

    counts = client.updater._handle_incremental_sync(entries, rs[0])
    assert counts["updated"] == 1
    assert counts["unchanged"] == len(entries) - 1


def test_incremental_sync_same_second_content_change(client_empty):
    """
    #135 core regression: the API serves `updated` at whole-second precision,
    so an object re-edited in the same second ties on the timestamp. The content
    comparison must still detect the change.
    """
    client = get_client()
    rs = all_resources()
    client.updater.update_all(rs)

    entries = client.fetcher.entries(Organization.tag)
    target = dict(entries[0])  # copy so we don't mutate the cached entry
    # leave `updated` identical -> ties at second granularity
    target["name"] = str(target.get("name") or "") + " (renamed)"

    counts = client.updater._handle_incremental_sync([target], Organization)
    assert counts["updated"] == 1  # caught via content despite identical `updated`


def test_compare_updated(client_empty):
    """Timestamp comparison: 1 newer / -1 older / 0 equal / None unknown."""
    upd = get_client().updater
    old = SimpleNamespace(updated=datetime(2023, 4, 21, 13, 46, 32))

    assert upd._compare_updated({"updated": "2023-04-21T13:46:33Z"}, old) == 1
    assert upd._compare_updated({"updated": "2023-04-21T13:46:31Z"}, old) == -1
    assert upd._compare_updated({"updated": "2023-04-21T13:46:32Z"}, old) == 0
    # missing / unparseable / missing-local -> None (caller treats as apply)
    assert upd._compare_updated({}, old) is None
    assert upd._compare_updated({"updated": "not-a-date"}, old) is None
    assert (
        upd._compare_updated(
            {"updated": "2023-04-21T13:46:32Z"}, SimpleNamespace(updated=None)
        )
        is None
    )


def test_content_differs(client_empty):
    """Field-level comparison used to break a same-second `updated` tie."""
    client = get_client()
    rs = all_resources()
    client.updater.update_all(rs)

    concrete = client.updater.backend.get_concrete(Organization)
    row = client.fetcher.entries(Organization.tag)[0]
    old = client.updater.backend.get_object(concrete, row["id"])
    new, _ = client.updater.create_obj(row, Organization)

    # freshly built from the same row -> identical
    assert client.updater._content_differs(new, old) is False
    # mutate a stored field -> differs
    new.name = "a completely different organization name"
    assert client.updater._content_differs(new, old) is True


def test_content_differs_biases_to_apply_on_error(client_empty):
    """An uncomparable field is treated as a difference (never silently skip)."""
    client = get_client()
    rs = all_resources()
    client.updater.update_all(rs)

    row = client.fetcher.entries(Organization.tag)[0]
    new, _ = client.updater.create_obj(row, Organization)

    class Boom:
        def __getattr__(self, name):
            raise RuntimeError("uncomparable")

    assert client.updater._content_differs(new, Boom()) is True


def test_changed_obj_applies_on_unknown_timestamp(client_empty):
    """Missing/unparseable `updated` -> apply (fail-safe, never drop a change)."""
    client = get_client()
    rs = all_resources()
    client.updater.update_all(rs)

    concrete = client.updater.backend.get_concrete(Organization)
    row = dict(client.fetcher.entries(Organization.tag)[0])
    old = client.updater.backend.get_object(concrete, row["id"])
    row.pop("updated", None)  # cmp == None

    assert client.updater._changed_obj(row, Organization, old) is not None


def test_incremental_sync_skips_older_remote(client_empty):
    """A row older than the local copy is skipped without a write (cmp == -1)."""
    client = get_client()
    rs = all_resources()
    client.updater.update_all(rs)

    target = dict(client.fetcher.entries(Organization.tag)[0])
    target["updated"] = "1990-01-01T00:00:00Z"  # older than what we stored
    target["name"] = "should not be written"

    counts = client.updater._handle_incremental_sync([target], Organization)
    assert counts["unchanged"] == 1
    assert counts["updated"] == 0
    # local copy left untouched
    assert client.get(Organization, target["id"]).name != "should not be written"


def test_incremental_sync_creates_new_object(client_empty):
    """#135: a row whose id is not present locally is created (created++)."""
    client = get_client()
    rs = all_resources()
    client.updater.update_all(rs)

    # drop reverse-relation sets; keep scalars + FK refs
    base = {
        k: v
        for k, v in client.fetcher.entries(Organization.tag)[0].items()
        if not isinstance(v, list)
    }
    base["id"] = 999999
    base["name"] = "Incremental Created Org 999999"  # unique name

    counts = client.updater._handle_incremental_sync([base], Organization)
    assert counts["created"] == 1
    assert counts["updated"] == 0
    assert client.get(Organization, 999999)


def test_incremental_sync_create_error(client_empty, monkeypatch):
    """A new-id row whose create fails is logged, not raised."""
    if os.path.exists("failed_entries.json"):
        os.remove("failed_entries.json")

    client = get_client()
    rs = all_resources()
    client.updater.update_all(rs)

    base = {
        k: v
        for k, v in client.fetcher.entries(Organization.tag)[0].items()
        if not isinstance(v, list)
    }
    base["id"] = 888888
    base["name"] = "Create Error Org 888888"

    original_create_obj = client.updater.create_obj

    def boom(row, res):
        if row.get("id") == 888888:
            raise ValueError("Simulating an error during object creation")
        return original_create_obj(row, res)

    monkeypatch.setattr(client.updater, "create_obj", boom)

    counts = client.updater._handle_incremental_sync([base], Organization)
    assert counts["created"] == 0
    with open("failed_entries.json") as f:
        failed = json.load(f)
        assert any(entry["pk"] == 888888 for entry in failed)

    if os.path.exists("failed_entries.json"):
        os.remove("failed_entries.json")


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
