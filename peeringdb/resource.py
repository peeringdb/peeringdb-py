"""
PeeringDB resource definitions
"""
from collections import OrderedDict

# Generate classes
_NAMES = OrderedDict([
    ('org', 'Organization'),
    ('fac', 'Facility'),
    ('net', 'Network'),
    ('ix', 'InternetExchange'),
    ('ixfac', 'InternetExchangeFacility'),
    ('ixlan', 'InternetExchangeLan'),
    ('ixpfx', 'InternetExchangeLanPrefix'),
    ('netfac', 'NetworkFacility'),
    ('netixlan', 'NetworkIXLan'),
    ('poc', 'NetworkContact'),
])

RESOURCES_BY_TAG = OrderedDict()

for tag, name in _NAMES.items():

    class Meta(type):
        def __repr__(cls, _name=name):
            return _name

    Class = Meta(name, (), {'tag': tag})

    RESOURCES_BY_TAG[tag] = Class
    locals()[name] = Class

is_resource_tag = RESOURCES_BY_TAG.__contains__


def get_resource(tag):
    return RESOURCES_BY_TAG[tag]


get = get_resource


def all_resources():
    return list(RESOURCES_BY_TAG.values())
