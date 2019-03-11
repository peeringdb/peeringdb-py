"""
Sync implementation module
"""
import logging
import datetime
from collections import defaultdict
from peeringdb.resource import get_resource
from peeringdb import get_backend
from peeringdb.util import FieldGroups


def _field_resource(B, concrete, field):
    return B.get_resource(B.get_field_concrete(concrete, field))


def clean_helper(B, obj, clean_func):
    """
    Clean object, intercepting and collecting any missing-relation or
    unique-constraint errors and returning the relevant resource ids/fields.

    Returns:
        - tuple: (<dict of non-unique fields>, <dict of missing refs>)
    """
    try:
        clean_func(obj)
    except B.validation_error() as e:
        # _debug.log_validation_errors(B, e, obj, k)

        # Check if it's a uniqueness or missing relation error
        fields = B.detect_uniqueness_error(e)
        missing = B.detect_missing_relations(obj, e)
        return fields, missing
    return (None, None)


def initialize_object(B, res, row):
    """
    Do a shallow initialization of an object

    Arguments:
        - row<dict>: dict of data like depth=1, i.e. many_refs are only ids
    """
    B = get_backend()
    field_groups = FieldGroups(B.get_concrete(res))

    try:
        obj = B.get_object(B.get_concrete(res), row['id'])
    except B.object_missing_error(B.get_concrete(res)):
        tbl = B.get_concrete(res)
        obj = tbl()

    # Set attributes, refs
    for fname, field in field_groups['scalars'].items():
        value = row.get(fname, getattr(obj, fname, None))
        value = B.convert_field(obj.__class__, fname, value)
        setattr(obj, fname, value)
    # _debug('res, row: %s, %s', res, row)

    # Already-fetched, and id-only refs
    fetched, dangling = defaultdict(dict), defaultdict(set)

    # To handle subrows that might be shallow (id) or deep (dict)
    def _handle_subrow(R, subrow):
        if isinstance(subrow, dict):
            pk = subrow['id']
            fetched[R][pk] = subrow
        else:
            pk = subrow
            dangling[R].add(pk)
        return pk

    for fname, field in field_groups['one_refs'].items():
        fieldres = _field_resource(B, B.get_concrete(res), fname)
        key = field.column
        subrow = row.get(key)
        if subrow is None:  # e.g. use "org" if "org_id" is missing
            key = fname
            subrow = row[key]
        pk = _handle_subrow(fieldres, subrow)
        setattr(obj, key, pk)

    for fname, field in field_groups['many_refs'].items():
        fieldres = _field_resource(B, B.get_concrete(res), fname)
        pks = [
            _handle_subrow(fieldres, subrow) for subrow in row.get(fname, [])
        ]

    return obj, fetched, dangling


def set_object_relations(B, res, obj, row):
    field_groups = FieldGroups(B.get_concrete(res))

    for fname, field in field_groups['many_refs'].items():
        fieldres = _field_resource(B, B.get_concrete(res), fname)
        pks = row.get(fname, [])
        objs = [B.get_object(B.get_concrete(fieldres), pk) for pk in pks]
        B.set_relation_many_to_many(obj, fname, objs)


def patch_object(B, res, obj, strip_tz):
    field_groups = FieldGroups(B.get_concrete(res))

    for fname in field_groups['scalars']:
        value = getattr(obj, fname)
        if strip_tz and isinstance(value, datetime.datetime):
            value = value.replace(tzinfo=None)
        B.update(obj, fname, value)

