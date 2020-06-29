from pathlib import Path
import pytest

import peeringdb

SQL_COUNT_ROWS="select count(*) from peeringdb_facility"

CONFIG = {
    'orm': {
        'backend': 'django_peeringdb',
        'database': {
            'engine': 'sqlite3',
            'host': '',
            'name': ':memory:',
            'password': '',
            'port': 0,
            'user': '',
        },
        'secret_key': '',
        'migrate': True,
    },
    'sync': {
        'url': 'https://test.peeringdb.com/api',
        'user': '',
        'password': '',
        'only': [],
        'strip_tz': 1,
        'timeout': 0,
    }
}

_DATA_PATH = None
def set_data_path(path, *parts):
    if not isinstance(path, Path):
        path = Path(path)
    assert path.exists(), path

    path = path.resolve()
    if not path.is_dir():
        path = path.parent
    path = path.resolve() / Path(*parts)
    global _DATA_PATH
    _DATA_PATH = path.absolute()

set_data_path(__file__, '../data')

def data_path():
    if _DATA_PATH is None:
        raise RuntimeError('data path not set')
    return _DATA_PATH

def reset_data(filename=None):
    from django.db import connection # FIXME django-specific
    # Make sure db is empty
    client = peeringdb.client.Client(CONFIG)
    client.backend.delete_all()

    if filename is None:
        print("Resetting database to empty")
        return

    print("Resetting database from", filename)
    path = data_path() / filename
    sql = path.open().read()

    with connection.cursor() as c:
        c.executescript(sql)

def client_for_data(filename):
    reset_data(filename)
    return peeringdb.client.Client(CONFIG)

# Fixture factory
def client_fixture(filename, scope='function'):
    def func():
        return client_for_data(filename)
    return pytest.fixture(scope=scope)(func)
