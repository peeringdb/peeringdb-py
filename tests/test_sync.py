import json
import os

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
    if os.path.exists("failed_entries_file.json"):
        os.remove("failed_entries_file.json")

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
    with open("failed_entries_file.json") as f:
        failed_objects = json.load(f)
        assert len(failed_objects) == 1
        assert failed_objects[0]["pk"] == 2

    # Delete the file after the test
    if os.path.exists("failed_entries_file.json"):
        os.remove("failed_entries_file.json")


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
    if os.path.exists("failed_entries_file.json"):
        os.remove("failed_entries_file.json")

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

    client.updater._handle_incremental_sync(
        client.fetcher.entries(rs[0].tag), rs[0]
    )  # Incremental sync for Organizations

    # Assertions
    assert client.get(Organization, 1)  # Object with ID 1 should still exist
    with open("failed_entries_file.json") as f:
        failed_objects = json.load(f)
        assert len(failed_objects) >= 1
        assert any(
            entry["pk"] == 1 for entry in failed_objects
        )  # Check if object ID 1 is present

    # Delete the file if exists
    if os.path.exists("failed_entries_file.json"):
        os.remove("failed_entries_file.json")


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
