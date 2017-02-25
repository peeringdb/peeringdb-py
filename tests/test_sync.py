
from peeringdb.localdb import LocalDB
import pytest


@pytest.mark.sync
def test_sync():
    db = LocalDB({})
    db.sync()
