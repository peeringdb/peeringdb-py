import os.path as _path
import pytest

import peeringdb

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
def set_data_path(fpath, *parts):
    # path = Path(fpath).absolute().parent / Path(*parts)
    path = _path.join(_path.dirname(_path.abspath(fpath)), *parts)
    # assert path.exists(), path
    assert _path.exists(path), path

    global _DATA_PATH
    # _DATA_PATH = path.absolute()
    _DATA_PATH = _path.abspath(path)

def data_path():
    if _DATA_PATH is None:
        raise RuntimeError('data path not set')
    return _DATA_PATH

def reset_data(filename=None):
    client = peeringdb.client.Client(CONFIG)
    # Make sure db is empty
    B = peeringdb.get_backend()
    B.delete_all()

    if filename is None:
        print("Resetting database to empty")
        return

    print("Resetting database from", filename)
    # Insert our stuff
    # FIXME django-specific
    from django.db import connection
    path = _path.join(data_path(), filename)
    sql = open(path).read()
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
