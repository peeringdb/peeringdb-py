"""
Sync implementation module
"""

from collections import defaultdict
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from peeringdb.backend import Interface

from peeringdb.util import group_fields


def _field_resource(backend: "Interface", concrete: type, field: object) -> type:
    field_name = getattr(field, "name", None)
    if field_name is None:
        raise ValueError("Field has no name")
    field_concrete = backend.get_field_concrete(concrete, field_name)
    if not isinstance(field_concrete, type):
        raise ValueError(f"Expected type, got {type(field_concrete)}")
    return backend.get_resource(field_concrete)


def _get_subrow(
    row: dict[str, Union[str, int, bool, list, dict]], fname: str, field: object
) -> tuple[str, Union[str, int, bool, list, dict, None]]:
    key = getattr(field, "column", None)
    if key is not None and isinstance(key, str):
        subrow = row.get(key)
    else:
        key = fname
        subrow = None
    if subrow is None:  # e.g. use "org" if "org_id" is missing
        key = fname
        try:
            subrow = row[key]
        except KeyError:
            subrow = None
    return key, subrow


def extract_relations(
    backend: "Interface", res: type, row: dict[str, Union[str, int, bool, list, dict]]
) -> tuple[
    dict[type, dict[Union[str, int], dict[str, Union[str, int, bool, list, dict]]]],
    dict[type, set[Union[str, int]]],
]:
    field_groups = group_fields(backend, backend.get_concrete(res))
    # Already-fetched, and id-only refs
    fetched: dict = defaultdict(dict)
    dangling = defaultdict(set)

    # Handle subrows that might be shallow (id) or deep (dict)
    def _handle_subrow(resource, subrow):
        if isinstance(subrow, dict):
            pk = subrow["id"]
            fetched[resource][pk] = subrow
        elif subrow is None:
            return
        else:
            pk = subrow
            dangling[resource].add(pk)
        return pk

    for fname, field in field_groups["single_refs"].items():
        fieldres = _field_resource(backend, backend.get_concrete(res), field)
        _, subrow = _get_subrow(row, fname, field)
        _handle_subrow(fieldres, subrow)

    for fname, field in field_groups["many_refs"].items():
        fieldres = _field_resource(backend, backend.get_concrete(res), field)
        many_data = row.get(fname, [])
        if isinstance(many_data, list):
            for subrow in many_data:
                _handle_subrow(fieldres, subrow)

    return fetched, dangling


def set_single_relations(
    backend: "Interface",
    res: type,
    obj: object,
    row: dict[str, Union[str, int, bool, list, dict]],
) -> None:
    field_groups = group_fields(backend, backend.get_concrete(res))
    for fname, field in field_groups["single_refs"].items():
        key, subrow = _get_subrow(row, fname, field)
        if isinstance(subrow, dict):
            pk = subrow["id"]
        else:
            pk = subrow
        setattr(obj, key, pk)


def set_many_relations(
    backend: "Interface",
    res: type,
    obj: object,
    row: dict[str, Union[str, int, bool, list, dict]],
) -> None:
    field_groups = group_fields(backend, backend.get_concrete(res))
    for fname, field in field_groups["many_refs"].items():
        fieldres = _field_resource(backend, backend.get_concrete(res), field)
        pks_data = row.get(fname, [])
        if isinstance(pks_data, list):
            pks = pks_data
        else:
            pks = []
        objs = [backend.get_object(backend.get_concrete(fieldres), pk) for pk in pks]
        backend.set_relation_many_to_many(obj, fname, objs)
