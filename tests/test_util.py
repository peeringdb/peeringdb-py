
import pytest
from peeringdb import util


def test_split_ref():
    assert ('net', 20) == util.split_ref('net20')
    assert ('net', 20) == util.split_ref('NET20')
    assert ('net', 20) == util.split_ref('net 20')
    assert ('net', 20) == util.split_ref('net-20')

def test_split_ref_exc():
    with pytest.raises(ValueError):
        util.split_ref('asdf123a')
    with pytest.raises(ValueError):
        util.split_ref('123asdf')

