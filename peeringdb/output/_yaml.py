import yaml
from peeringdb import get_backend
from peeringdb.util import FieldGroups

# from peeringdb.debug import try_or_debug


# Wrap orm object into node for graph traversal
class YamlWrap(FieldGroups):
    def __init__(self, o, depth):
        self.tag = 'tag:yaml.org,2002:map'
        self.object = o
        self.depth = depth
        self.fields = FieldGroups(o.__class__)

    @staticmethod
    def _resolve_one(name, value, depth):
        if depth > 0:
            return YamlWrap(value, depth - 1)
        else:
            return value.id

    @staticmethod
    def _resolve_many(name, value, depth):
        if depth > 1:
            return [YamlWrap(o, depth - 1) for o in value.all()]
        elif depth == 1:
            return list(value.values_list('id', flat=True))

    def resolve(self, group, name, value):
        if group == 'scalars':
            return value
        elif group == 'one_refs':
            return YamlWrap._resolve_one(name, value, self.depth)
        elif group == 'many_refs':
            return YamlWrap._resolve_many(name, value, self.depth)
        else:
            raise ValueError(group)

    def field_values(self):
        for group in self.fields.GROUPS:
            if self.depth == 0 and group == 'many_refs':
                continue
            for name in self.fields[group]:
                value = self.resolve(group, name, getattr(self.object, name))
                yield name, value


def represent_wrapped(dumper, wrap):
    _dict = {}
    for name, value in wrap.field_values():
        _dict[name] = value
    alist = [(k, _dict[k]) for k in sorted(_dict)]
    return dumper.represent_mapping(wrap.tag, alist)


def default_representer(dumper, data):
    # Py2 workaround
    rep_func = getattr(dumper, 'represent_unicode', None)
    if rep_func is None:
        rep_func = dumper.represent_str
    return rep_func(str(data))


def _init():
    dumper = yaml.SafeDumper
    for cls in get_backend().CUSTOM_FIELDS:
        dumper.add_representer(cls, default_representer)
    dumper.add_representer(YamlWrap, represent_wrapped)


def dump(obj, depth, file):
    _init()
    if get_backend().is_concrete(type(obj)):
        obj = YamlWrap(obj, depth)
    yaml.safe_dump(obj, stream=file, default_flow_style=False)
