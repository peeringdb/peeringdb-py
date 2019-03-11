import logging, re
from functools import reduce

from peeringdb import resource, get_backend

try:
    input = raw_input
except NameError:
    pass


def split_ref(string):
    """ splits a string into (tag, id) """
    re_tag = re.compile('^(?P<tag>[a-zA-Z]+)[\s-]*(?P<pk>\d+)$')
    m = re_tag.search(string)
    if not m:
        raise ValueError("unable to split string '%s'" % (string, ))

    return (m.group('tag').lower(), int(m.group('pk')))


def pretty_speed(value):
    if not value:
        return ''
    try:
        value = int(value)
        if value >= 1000000:
            return "%dT" % (value / 10**6)
        elif value >= 1000:
            return "%dG" % (value / 10**3)
        else:
            return "%dM" % value
    except ValueError:
        return value


def prompt(msg, default=None):
    "Prompt for input"
    if default is not None:
        msg = '{} ({})'.format(msg, repr(default))
    msg = '{}: '.format(msg)
    try:
        s = input(msg)
    except KeyboardInterrupt:
        exit(1)
    except EOFError:
        s = ''
    if not s:
        s = default
    return s


class FieldGroups:
    "Partition a concrete's fields into groups based on type"
    GROUPS = ('scalars', 'one_refs', 'many_refs')

    def __init__(self, concrete):
        backend = get_backend()
        kinds = {kind: {} for kind in FieldGroups.GROUPS}
        fields = backend.get_fields(concrete)
        for field in fields:
            name = field.name
            related, multiple = backend.is_field_related(concrete, name)

            if related:
                if multiple:
                    group = kinds['many_refs']
                else:
                    group = kinds['one_refs']
            else:
                group = kinds['scalars']

            group[name] = field
        self._fields = kinds

        for kind, fs in kinds.items():
            setattr(self, kind, lambda _fs=fs: _fs.items())

    def __getitem__(self, k):
        return self._fields[k]

    def __contains__(self, k):
        return k in self._fields


def limit_mem(limit=(4 * 1024**3)):
    "Set soft memory limit"
    rsrc = resource.RLIMIT_DATA
    soft, hard = resource.getrlimit(rsrc)
    resource.setrlimit(rsrc, (limit, hard))  # 4GB
    softnew, _ = resource.getrlimit(rsrc)
    assert softnew == limit

    _log = logging.getLogger(__name__)
    _log.debug('Set soft memory limit: %s => %s', soft, softnew)
