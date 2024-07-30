import json
from datetime import datetime
from decimal import Decimal
from ipaddress import IPv4Address, IPv6Address

import django_countries.fields

from peeringdb import get_backend
from peeringdb.util import group_fields


class DictWrap:
    def __init__(self, o, depth):
        self.object = o
        self.depth = depth
        backend = get_backend()
        self.fields = group_fields(backend, o.__class__)

    @staticmethod
    def _resolve_one(name, value, depth):
        if depth > 0:
            return DictWrap(value, depth - 1).to_dict()
        elif value is None:
            return None
        else:
            return value.id

    @staticmethod
    def _resolve_many(name, value, depth):
        if depth > 1:
            return [DictWrap(o, depth - 1).to_dict() for o in value.all()]
        elif depth == 1:
            return list(value.values_list("id", flat=True))

    def resolve(self, group, name, value):
        if group == "scalars":
            if isinstance(value, datetime):
                return value.isoformat()
            elif isinstance(value, django_countries.fields.Country):
                return str(value)
            elif isinstance(value, Decimal):
                return float(value)
            elif isinstance(value, (IPv4Address, IPv6Address)):
                return str(value)
            return value
        elif group == "single_refs":
            return DictWrap._resolve_one(name, value, self.depth)
        elif group == "many_refs":
            return DictWrap._resolve_many(name, value, self.depth)
        else:
            raise ValueError(group)

    def field_values(self):
        for group in self.fields:
            if self.depth == 0 and group == "many_refs":
                continue
            for name in self.fields[group]:
                value = self.resolve(group, name, getattr(self.object, name))
                if value is None:
                    value = "None"
                yield name, value

    def to_dict(self):
        data = {}
        for name, value in self.field_values():
            data[name] = value
        return data


def dump_python_dict(obj, depth):
    if get_backend().is_concrete(type(obj)):
        obj = DictWrap(obj, depth).to_dict()
    return obj
