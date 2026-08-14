import importlib

from peeringdb import _types


def test_value_alias_is_defined():
    # Reload so the alias definition executes *under* coverage regardless of
    # import ordering during collection. pytest-cov can otherwise miss a module
    # that was imported before instrumentation started (a non-deterministic
    # artifact, not a real gap).
    importlib.reload(_types)
    assert _types.Value == (str | int | bool | list | dict)
