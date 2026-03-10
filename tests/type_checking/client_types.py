"""
Type-checking tests for peeringdb.client.Client.

Checked by mypy (via uv tox -e mypy).
Each snippet documents a type contract that must hold.

Issue: https://github.com/peeringdb/peeringdb-py/issues/134
"""

from collections.abc import Mapping

from peeringdb.client import Client

# cfg accepts dict[str, dict[str, object]] (nested dict).
# Before the fix, mypy rejected this because dict is invariant.

nested_cfg: dict[str, dict[str, object]] = {
    "sync": {"api_key": "test-key", "url": "https://test.peeringdb.com/api/"},
    "orm": {"backend": "django_peeringdb"},
}
_client_from_nested_dict: Client = Client(cfg=nested_cfg)

# cfg also accepts a plain Mapping
flat_mapping: Mapping[str, object] = {"sync": {}}
_client_from_mapping: Client = Client(cfg=flat_mapping)

# cfg is optional - None is valid
_client_no_cfg: Client = Client(cfg=None)
