import pytest
import peeringdb
peeringdb.SUPPORTED_BACKENDS['_mock'] = 'mock.backend'

@pytest.mark.skip
def test_get():
    # get before init
    with pytest.raises(peeringdb.BackendError):
        B = peeringdb.get_backend()

    peeringdb.initialize_backend('_mock')
    B = peeringdb.get_backend()

@pytest.mark.skip('todo - need per-test state')
def test_init():
    # bad name
    with pytest.raises(Exception): # todo
        peeringdb.initialize_backend('_bad')
    # ok
    peeringdb.initialize_backend('_mock')

    # double init
    with pytest.raises(peeringdb.BackendError):
        peeringdb.initialize_backend('_mock')
