import pytest

from peeringdb.client import PeeringDB


def test_nonexistant_config():
    with pytest.raises(IOError):
        PeeringDB(conf_dir="nonexistant")


def test_get():
    pdb = PeeringDB()
    net1 = pdb.get("net", 1)
    assert net1


def test_type_wrap():
    pdb = PeeringDB()
    net = pdb.type_wrap("net")
    net1 = net.get(1)
    assert net1
