import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from peeringdb import util
from peeringdb._debug import try_or_debug


def test_split_ref():
    assert ("net", 20) == util.split_ref("net20")
    assert ("net", 20) == util.split_ref("NET20")
    assert ("net", 20) == util.split_ref("net 20")
    assert ("net", 20) == util.split_ref("net-20")


def test_split_ref_exc():
    with pytest.raises(ValueError):
        util.split_ref("asdf123a")
    with pytest.raises(ValueError):
        util.split_ref("123asdf")


def test_load_failed_entries_invalid_json():
    """Test that load_failed_entries handles invalid JSON gracefully."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"invalid": json,}')
        f.flush()

        config = {"sync": {"failed_entries": f.name}}

        with patch("peeringdb.util.logging.warning") as mock_warning:
            result = util.load_failed_entries(config)

            assert result == []
            mock_warning.assert_called_once()
            assert "contains invalid JSON" in str(mock_warning.call_args)
    Path(f.name).unlink()


def test_load_failed_entries_valid_json():
    """Test that load_failed_entries works correctly with valid JSON."""
    test_data = [{"resource_tag": "net", "pk": 123, "error": "test error"}]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_data, f)
        f.flush()

        config = {"sync": {"failed_entries": f.name}}

        result = util.load_failed_entries(config)
        assert result == test_data

    Path(f.name).unlink()


def test_load_failed_entries_empty_file():
    """Test that load_failed_entries handles empty files."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("")
        f.flush()

        config = {"sync": {"failed_entries": f.name}}

        result = util.load_failed_entries(config)
        assert result == []

    Path(f.name).unlink()


def test_load_failed_entries_file_not_found():
    """Test that load_failed_entries handles missing files."""
    config = {"sync": {"failed_entries": "/nonexistent/file.json"}}

    result = util.load_failed_entries(config)
    assert result == []


def test_save_and_load_failed_entries_roundtrip(tmp_path):
    """save_failed_entries followed by load_failed_entries round-trips."""
    entries = [{"resource_tag": "net", "pk": 1, "error": "x"}]
    config = {"sync": {"failed_entries": str(tmp_path / "failed.json")}}

    util.save_failed_entries(config, entries)
    assert util.load_failed_entries(config) == entries


def test_save_failed_entries_no_target_is_noop():
    """No failed_entries key -> save is a silent no-op (no exception)."""
    util.save_failed_entries({"sync": {}}, [{"resource_tag": "net", "pk": 1}])


def test_log_error_appends_and_dedupes(tmp_path):
    """log_error records a failed entry and does not duplicate an identical one."""
    config = {"sync": {"failed_entries": str(tmp_path / "failed.json")}}

    util.log_error(config, "net", 5, "boom")
    assert util.load_failed_entries(config) == [
        {"resource_tag": "net", "pk": 5, "error": "boom"}
    ]

    # identical entry is not appended again
    util.log_error(config, "net", 5, "boom")
    assert len(util.load_failed_entries(config)) == 1


def test_pretty_speed():
    assert util.pretty_speed(None) == ""
    assert util.pretty_speed(0) == ""
    assert util.pretty_speed("") == ""
    assert util.pretty_speed(800) == "800M"
    assert util.pretty_speed(1000) == "1G"
    assert util.pretty_speed(5000) == "5G"
    assert util.pretty_speed(1000000) == "1T"
    assert util.pretty_speed(3000000) == "3T"
    # numeric strings are coerced
    assert util.pretty_speed("1000") == "1G"
    # non-numeric strings are returned as-is
    assert util.pretty_speed("fast") == "fast"


def test_str_to_bool():
    for truthy in ["y", "yes", "t", "true", "on", "1"]:
        assert util.str_to_bool(truthy) is True
    for falsy in ["n", "no", "f", "false", "off", "0"]:
        assert util.str_to_bool(falsy) is False
    with pytest.raises(ValueError):
        util.str_to_bool("maybe")


def test_get_log_level():
    assert util.get_log_level("info") == logging.INFO
    assert util.get_log_level("DEBUG") == logging.DEBUG
    assert util.get_log_level(" warning ") == logging.WARNING
    assert util.get_log_level("critical") == logging.CRITICAL
    assert util.get_log_level("error") == logging.ERROR
    assert util.get_log_level("notset") == logging.NOTSET
    assert util.get_log_level("bogus") is None


def test_prompt_uses_default_on_empty(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    assert util.prompt("name", "fallback") == "fallback"


def test_prompt_returns_entered_value(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "typed")
    assert util.prompt("name", "fallback") == "typed"
    assert util.prompt("name") == "typed"


def test_prompt_handles_eof(monkeypatch):
    def _raise_eof(_prompt):
        raise EOFError

    monkeypatch.setattr("builtins.input", _raise_eof)
    assert util.prompt("name", "fallback") == "fallback"


def test_prompt_keyboard_interrupt_exits(monkeypatch):
    def _interrupt(_prompt):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", _interrupt)
    with pytest.raises(SystemExit):
        util.prompt("name")


def test_load_failed_entries_sync_not_dict():
    """A non-dict sync section yields no failed-entries file (returns [])."""
    assert util.load_failed_entries({"sync": "notadict"}) == []


class _MockField:
    def __init__(self, name):
        self.name = name


class _MockFieldBackend:
    def __init__(self, fields, relations):
        self._fields = fields
        self._relations = relations

    def get_fields(self, concrete):
        return self._fields

    def is_field_related(self, concrete, name):
        return self._relations.get(name)


def test_group_fields_none_concrete():
    assert util.group_fields(object(), None) == {
        "scalars": {},
        "single_refs": {},
        "many_refs": {},
    }


def test_group_fields_skips_nameless_and_non_tuple_relation():
    fields = [_MockField(None), _MockField("a"), _MockField("b"), _MockField("c")]
    relations = {"a": None, "b": (True, False), "c": (True, True)}
    backend = _MockFieldBackend(fields, relations)

    groups = util.group_fields(backend, object)

    # non-tuple relation info -> treated as a scalar
    assert "a" in groups["scalars"]
    assert "b" in groups["single_refs"]
    assert "c" in groups["many_refs"]
    # the nameless field is skipped entirely
    assert sum(len(v) for v in groups.values()) == 3


def test_limit_mem(monkeypatch):
    state = {"soft": 1000, "hard": 9999}
    monkeypatch.setattr(
        "peeringdb.util.sys_resource.getrlimit",
        lambda _rsrc: (state["soft"], state["hard"]),
    )

    def _setrlimit(_rsrc, vals):
        state["soft"], state["hard"] = vals

    monkeypatch.setattr("peeringdb.util.sys_resource.setrlimit", _setrlimit)

    util.limit_mem(5000)
    assert state["soft"] == 5000


def test_try_or_debug_returns_value():
    assert try_or_debug(lambda: 42) == 42


def test_try_or_debug_reraises():
    def _boom():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        try_or_debug(_boom)
