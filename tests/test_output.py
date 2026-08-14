import helper
import pytest

from peeringdb.output._dict import DictWrap

client = helper.client_fixture("full")


def test_resolve_many_no_all_method_returns_empty():
    # depth > 1 but the value has no .all() -> []
    assert DictWrap._resolve_many("x", object(), depth=2) == []


def test_resolve_many_values_list():
    class _V:
        def values_list(self, *_a, **_k):
            return [1, 2, 3]

    assert DictWrap._resolve_many("x", _V(), depth=1) == [1, 2, 3]


def test_resolve_many_no_values_list_returns_empty():
    # depth == 1 but the value has no .values_list() -> []
    assert DictWrap._resolve_many("x", object(), depth=1) == []


def test_resolve_many_depth_zero_returns_none():
    assert DictWrap._resolve_many("x", object(), depth=0) is None


def test_resolve_unknown_group_raises(client):
    dw = DictWrap(None, 0)
    with pytest.raises(ValueError):
        dw.resolve("bogus", "name", 1)
