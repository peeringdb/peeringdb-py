"""
PeeringDB resource definitions
"""

from collections import OrderedDict
from typing import Callable

# Generate classes
_NAMES: OrderedDict[str, str] = OrderedDict(
    [
        ("org", "Organization"),
        ("campus", "Campus"),
        ("fac", "Facility"),
        ("net", "Network"),
        ("ix", "InternetExchange"),
        ("carrier", "Carrier"),
        ("carrierfac", "CarrierFacility"),
        ("ixfac", "InternetExchangeFacility"),
        ("ixlan", "InternetExchangeLan"),
        ("ixpfx", "InternetExchangeLanPrefix"),
        ("netfac", "NetworkFacility"),
        ("netixlan", "NetworkIXLan"),
        ("poc", "NetworkContact"),
    ]
)

RESOURCES_BY_TAG: OrderedDict[str, type] = OrderedDict()

for tag, name in _NAMES.items():

    class Meta(type):
        def __repr__(cls, _name: str = name) -> str:
            return _name

    Class = Meta(name, (), {"tag": tag})

    RESOURCES_BY_TAG[tag] = Class
    globals()[name] = Class

is_resource_tag: Callable[[str], bool] = RESOURCES_BY_TAG.__contains__


def get_resource(tag: str) -> type:
    return RESOURCES_BY_TAG[tag]


get: Callable[[str], type] = get_resource


def all_resources() -> list[type]:
    return list(RESOURCES_BY_TAG.values())
