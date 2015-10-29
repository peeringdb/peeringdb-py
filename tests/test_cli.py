
import datetime
import pytest

import os
import peeringdb
from peeringdb import cli
import pytest


test_dir = os.path.relpath(os.path.dirname(__file__))

def test_get_deps():
    assert ['django_peeringdb'] == cli.get_deps('sqlite3')


