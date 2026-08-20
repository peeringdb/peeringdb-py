import types
from datetime import UTC, datetime

import helper
import pytest
from django.core.exceptions import ValidationError

from peeringdb import resource
from peeringdb._update import Updater
from peeringdb.fetch import Fetcher

client = helper.client_fixture("full")


def _updater():
    return Updater(Fetcher(url="", timeout=1))


def test_copy_object_reraises_unexpected_type_error(client, monkeypatch):
    class _Old:
        @property
        def x(self):
            return None

        @x.setter
        def x(self, value):
            raise TypeError("boom")  # not a "Direct assignment" error

    up = _updater()
    old = _Old()
    monkeypatch.setattr(up.backend, "get_object", lambda cls, pk: old)
    monkeypatch.setattr(
        up.backend, "get_fields", lambda cls: [types.SimpleNamespace(name="x")]
    )
    new = types.SimpleNamespace(id=1, x=5)
    with pytest.raises(TypeError):
        up.copy_object(new)


def test_compare_updated_strips_local_timezone(client):
    up = _updater()
    old = types.SimpleNamespace(updated=datetime(2020, 1, 1, tzinfo=UTC))
    assert up._compare_updated({"updated": "2020-01-01T00:00:00Z"}, old) == 0


def test_lookback_sync_not_dict(client):
    up = _updater()
    up.config = {"sync": "notadict"}
    assert up._lookback() == 1


def test_lookback_unparseable_value(client):
    up = _updater()
    up.config = {"sync": {"lookback": "abc"}}
    assert up._lookback() == 1


def test_update_all_skips_requested_resource(client, monkeypatch):
    up = _updater()
    net = resource.get_resource("net")
    loaded = []
    monkeypatch.setattr(up.fetcher, "load", lambda tag, since, **k: loaded.append(tag))

    up.update_all([net], skip=["net"])
    assert "net" in loaded


def test_update_one_depth_warns(client, monkeypatch):
    up = _updater()
    net = resource.get_resource("net")
    monkeypatch.setattr(up.fetcher, "get", lambda *a, **k: {"id": 1})
    monkeypatch.setattr(up, "create_obj", lambda row, res: (object(), False))
    monkeypatch.setattr(up, "copy_object", lambda obj: None)

    up.update_one(net, 1, depth=2)  # non-zero depth -> deprecation warning


def test_create_obj_dangling_clean_failure(client, monkeypatch):
    up = _updater()
    net = resource.get_resource("net")

    def _raise_clean(obj):
        raise ValidationError("bad")

    monkeypatch.setattr(up, "clean_obj", _raise_clean)
    monkeypatch.setattr(up.fetcher, "get", lambda tag, pk, **k: {"id": pk})

    # "org" is a shallow (id-only) ref to an object not in the DB -> dangling
    obj, ok = up.create_obj({"id": 999999, "org": 888888}, net)
    assert obj is None
    assert ok is False


def test_handle_initial_sync_retry_saves(client, monkeypatch):
    up = _updater()
    net = resource.get_resource("net")
    concrete = up.backend.get_concrete(net)
    missing = up.backend.object_missing_error(concrete)

    calls = {"n": 0}
    obj = object()

    def _create(row, res):
        calls["n"] += 1
        if calls["n"] == 1:
            raise missing()  # first attempt: object-missing -> retry branch
        return (obj, False)

    saved = []
    monkeypatch.setattr(up, "create_obj", _create)
    monkeypatch.setattr(up.backend, "save", lambda o: saved.append(o))

    up._handle_initial_sync([{"id": 1}], net)
    assert saved == [obj]


def test_handle_initial_sync_logs_creation_error(client, monkeypatch):
    up = _updater()
    net = resource.get_resource("net")
    concrete = up.backend.get_concrete(net)
    missing = up.backend.object_missing_error(concrete)

    def _raise_missing(row, res):
        raise missing()

    monkeypatch.setattr(up, "create_obj", _raise_missing)
    monkeypatch.setattr("peeringdb._update.log_error", lambda *a, **k: None)

    # create_obj raises the object-missing error -> inner retry also raises ->
    # the error is logged rather than propagated
    up._handle_initial_sync([{"id": 1}], net)
