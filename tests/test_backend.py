import pytest

import peeringdb

peeringdb.SUPPORTED_BACKENDS["_mock"] = "mock.backend"
import helper


@pytest.mark.skip
def test_get():
    # get before init
    with pytest.raises(peeringdb.BackendError):
        B = peeringdb.get_backend()

    peeringdb.initialize_backend("_mock")
    B = peeringdb.get_backend()


@pytest.mark.skip("todo - need per-test state")
def test_init():
    # bad name
    with pytest.raises(Exception):  # todo
        peeringdb.initialize_backend("_bad")
    # ok
    peeringdb.initialize_backend("_mock")

    # double init
    with pytest.raises(peeringdb.BackendError):
        peeringdb.initialize_backend("_mock")


client = helper.client_fixture("full")


def test_delete_all(client):
    from django.db import connection

    def _count():  # returns (int,)
        with connection.cursor() as c:
            return c.execute(helper.SQL_COUNT_ROWS).fetchone()

    ct = _count()
    assert ct[0] > 0, ct

    client = peeringdb.client.Client(helper.CONFIG)
    B = peeringdb.get_backend()
    B.delete_all()

    ct = _count()
    assert ct[0] == 0, ct
