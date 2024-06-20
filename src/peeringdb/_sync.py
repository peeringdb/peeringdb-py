"""
Sync implementation module
"""

from collections import defaultdict

from peeringdb.util import group_fields


def _field_resource(B, concrete, field):
    return B.get_resource(B.get_field_concrete(concrete, field))


def _get_subrow(row, fname, field):
    key = field.column
    subrow = row.get(key)
    if subrow is None:  # e.g. use "org" if "org_id" is missing
        key = fname
        try:
            subrow = row[key]
        except KeyError:
            subrow = None
    return key, subrow


def extract_relations(B, res, row):
    field_groups = group_fields(B, B.get_concrete(res))
    # Already-fetched, and id-only refs
    fetched, dangling = defaultdict(dict), defaultdict(set)

    # Handle subrows that might be shallow (id) or deep (dict)
    def _handle_subrow(R, subrow):
        if isinstance(subrow, dict):
            pk = subrow["id"]
            fetched[R][pk] = subrow
        elif subrow is None:
            return
        else:
            pk = subrow
            dangling[R].add(pk)
        return pk

    for fname, field in field_groups["single_refs"].items():
        fieldres = _field_resource(B, B.get_concrete(res), fname)
        _, subrow = _get_subrow(row, fname, field)
        _handle_subrow(fieldres, subrow)

    for fname, field in field_groups["many_refs"].items():
        fieldres = _field_resource(B, B.get_concrete(res), fname)
        for subrow in row.get(fname, []):
            _handle_subrow(fieldres, subrow)

    return fetched, dangling


def set_single_relations(B, res, obj, row):
    field_groups = group_fields(B, B.get_concrete(res))
    for fname, field in field_groups["single_refs"].items():
        key, subrow = _get_subrow(row, fname, field)
        if isinstance(subrow, dict):
            pk = subrow["id"]
        else:
            pk = subrow
        setattr(obj, key, pk)


def set_many_relations(B, res, obj, row):
    field_groups = group_fields(B, B.get_concrete(res))
    for fname, field in field_groups["many_refs"].items():
        fieldres = _field_resource(B, B.get_concrete(res), fname)
        pks = row.get(fname, [])
        objs = [B.get_object(B.get_concrete(fieldres), pk) for pk in pks]
        B.set_relation_many_to_many(obj, fname, objs)
