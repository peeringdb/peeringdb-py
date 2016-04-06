
import re


def split_ref(string):
    """ splits a string into (tag, id) """
    re_tag = re.compile('^(?P<tag>[a-zA-Z]+)[\s-]*(?P<pk>\d+)$')
    m = re_tag.search(string)
    if not m:
        raise ValueError("unable to split string '%s'" % (string,))

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
