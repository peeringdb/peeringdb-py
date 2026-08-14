import types

import helper
import pytest

import peeringdb
from peeringdb.backend import EmptyContext, Field, Interface, reftag_to_cls

peeringdb.SUPPORTED_BACKENDS["_mock"] = "mock.backend"

# Interface methods that concrete backends must override; the base raises.
_STUB_CALLS = [
    lambda b: b.create_object(int),
    lambda b: b.delete_all(),
    lambda b: b.detect_missing_relations(object(), Exception()),
    lambda b: b.detect_uniqueness_error(Exception()),
    lambda b: b.get_field_names(int),
    lambda b: b.get_field_concrete(int, "x"),
    lambda b: b.get_object(int, 1),
    lambda b: b.get_object_by(int, "x", 1),
    lambda b: b.get_objects(int),
    lambda b: b.get_objects_by(int, "x", 1),
    lambda b: b.is_field_related(int, "x"),
    lambda b: b.last_change(int),
    lambda b: b.save(object()),
    lambda b: b.set_relation_many_to_many(object(), "x", []),
]


def test_reftag_to_cls_maps_string_args():
    class _B(Interface):
        REFTAG_CONCRETE = {"net": int}
        REFTAG_RESOURCE = {"net": str}

        @reftag_to_cls
        def by_concrete(self, concrete):
            return concrete

        @reftag_to_cls
        def by_resource(self, resource):
            return resource

    b = _B()
    assert b.by_concrete("net") is int
    assert b.by_resource("net") is str
    # non-string args pass through untouched
    assert b.by_concrete(float) is float


def test_interface_optional_defaults():
    iface = Interface()
    assert issubclass(iface.validation_error(), Exception)
    assert issubclass(iface.object_missing_error(), Exception)
    assert isinstance(iface.atomic_transaction(), EmptyContext)
    iface.setup()

    obj = types.SimpleNamespace()
    iface.update(obj, "asn", 5)
    assert obj.asn == 5

    assert isinstance(iface.get_field(int, "asn"), Field)
    assert iface.convert_field(int, "asn", 3) == 3
    iface.clean(obj)
    iface.migrate_database()
    assert iface.is_database_migrated() is True


def test_get_fields_default_impl():
    class _B(Interface):
        def get_field_names(self, concrete):
            return ["a", "b"]

    assert [f.name for f in _B().get_fields(int)] == ["a", "b"]


def test_base_resource_concrete_maps():
    class _B(Interface):
        RESOURCE_MAP = {str: int}

    b = _B()
    assert b.get_concrete(str) is int
    assert b.is_concrete(int) is True
    assert b.is_concrete(float) is False
    assert b.get_resource(int) is str


def test_config_logs_bad_allow_other_loggers():
    # an unparseable allow_other_loggers value falls back to False (no raise)
    peeringdb._config_logs("INFO", allow_other_loggers="not-a-bool")


def test_get_backend_info(client):
    name, _version = peeringdb.get_backend_info()
    assert name == "django_peeringdb"


def test_initialize_backend_already_initialized(client):
    with pytest.raises(peeringdb.BackendError):
        peeringdb.initialize_backend("django_peeringdb")


def test_get_backend_uninitialized(monkeypatch):
    monkeypatch.setattr(peeringdb, "__backend", None)
    with pytest.raises(peeringdb.BackendError):
        peeringdb.get_backend()


def test_initialize_backend_bad_name(monkeypatch):
    monkeypatch.setattr(peeringdb, "__backend", None)
    with pytest.raises(ValueError):
        peeringdb.initialize_backend("_nonexistent_backend")


def test_field():
    f = Field("asn")
    assert f.name == "asn"
    assert f.column is None


def test_empty_context():
    with EmptyContext():
        pass


def test_concrete_map_alias():
    # CONCRETE_MAP is a backwards-compat alias of concrete_map
    b = Interface()
    assert b.CONCRETE_MAP == b.concrete_map == {}


@pytest.mark.parametrize("call", _STUB_CALLS)
def test_interface_stub_raises_not_implemented(call):
    with pytest.raises(NotImplementedError):
        call(Interface())


@pytest.mark.skip
def test_get():
    # get before init
    with pytest.raises(peeringdb.BackendError):
        peeringdb.get_backend()

    peeringdb.initialize_backend("_mock")
    peeringdb.get_backend()


@pytest.mark.skip("todo - need per-test state")
def test_init():
    # bad name
    with pytest.raises(Exception):  # todo
        peeringdb.initialize_backend("_bad")
    # ok
    peeringdb.initialize_backend("_mock")

    # double init
    with pytest.raises(peeringdb.BackendError):
        peeringdb.initialize_backend("_mock")


client = helper.client_fixture("full")


def test_delete_all(client):
    from django.db import connection

    def _count():  # returns (int,)
        with connection.cursor() as c:
            return c.execute(helper.SQL_COUNT_ROWS).fetchone()

    ct = _count()
    assert ct[0] > 0, ct

    peeringdb.client.Client(helper.CONFIG)
    backend = peeringdb.get_backend()
    backend.delete_all()

    ct = _count()
    assert ct[0] == 0, ct
