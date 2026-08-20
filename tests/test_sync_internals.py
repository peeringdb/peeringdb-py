import types

import pytest

from peeringdb import _sync


class _DummyRes:
    pass


class _SyncBackend:
    """Minimal backend exercising the _sync helpers without Django."""

    def __init__(self):
        self.m2m = []

    def get_concrete(self, res):
        return res

    def get_fields(self, concrete):
        return [
            types.SimpleNamespace(name="org", column="org"),
            types.SimpleNamespace(name="netixlan_set", column="netixlan_set"),
        ]

    def is_field_related(self, concrete, name):
        if name == "org":
            return (True, False)
        if name == "netixlan_set":
            return (True, True)
        return (False, False)

    def get_field_concrete(self, concrete, name):
        return int

    def get_resource(self, concrete):
        return concrete

    def get_object(self, concrete, pk):
        return f"obj-{pk}"

    def set_relation_many_to_many(self, obj, field_name, objs):
        self.m2m.append((field_name, objs))


def test_field_resource_field_without_name():
    with pytest.raises(ValueError, match="no name"):
        _sync._field_resource(object(), int, object())


def test_field_resource_non_type_concrete():
    class _B:
        def get_field_concrete(self, concrete, name):
            return "not-a-type"

    field = types.SimpleNamespace(name="org")
    with pytest.raises(ValueError, match="Expected type"):
        _sync._field_resource(_B(), int, field)


def test_get_subrow_by_column():
    field = types.SimpleNamespace(column="org_id")
    key, subrow = _sync._get_subrow({"org_id": 5}, "org", field)
    assert (key, subrow) == ("org_id", 5)


def test_get_subrow_no_column_uses_field_name():
    field = types.SimpleNamespace(column=None)
    key, subrow = _sync._get_subrow({"org": 7}, "org", field)
    assert (key, subrow) == ("org", 7)


def test_get_subrow_missing_key():
    field = types.SimpleNamespace(column=None)
    key, subrow = _sync._get_subrow({}, "org", field)
    assert (key, subrow) == ("org", None)


def test_extract_relations_deep_and_shallow_refs():
    backend = _SyncBackend()
    row = {
        "org": {"id": 3, "name": "o"},  # deep single ref -> fetched
        "netixlan_set": [5, {"id": 6}],  # 5 -> dangling, {id:6} -> fetched
    }
    fetched, dangling = _sync.extract_relations(backend, _DummyRes, row)

    assert 3 in fetched[int]
    assert 6 in fetched[int]
    assert 5 in dangling[int]


def test_extract_relations_missing_single_ref():
    # a single ref absent from the row yields a None subrow (handled, not stored)
    backend = _SyncBackend()
    fetched, dangling = _sync.extract_relations(backend, _DummyRes, {})
    assert dict(fetched) == {}
    assert dict(dangling) == {}


def test_set_single_relations_deep_and_shallow():
    backend = _SyncBackend()

    obj = types.SimpleNamespace()
    _sync.set_single_relations(backend, _DummyRes, obj, {"org": {"id": 9}})
    assert obj.org == 9  # deep ref -> pk from ["id"]

    obj2 = types.SimpleNamespace()
    _sync.set_single_relations(backend, _DummyRes, obj2, {"org": 4})
    assert obj2.org == 4  # shallow ref -> pk is the value


def test_set_many_relations_list_and_non_list():
    backend = _SyncBackend()

    obj = types.SimpleNamespace()
    _sync.set_many_relations(backend, _DummyRes, obj, {"netixlan_set": [1, 2]})
    assert backend.m2m[-1] == ("netixlan_set", ["obj-1", "obj-2"])

    obj2 = types.SimpleNamespace()
    _sync.set_many_relations(backend, _DummyRes, obj2, {"netixlan_set": "notalist"})
    assert backend.m2m[-1] == ("netixlan_set", [])
