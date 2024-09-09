from pathlib import Path

import pytest

import peeringdb
from peeringdb.util import client_load

SQL_COUNT_ROWS = "select count(*) from peeringdb_facility"

CONFIG = {
    "orm": {
        "backend": "django_peeringdb",
        "database": {
            "engine": "sqlite3",
            "host": "",
            "name": ":memory:",
            "password": "",
            "port": 0,
            "user": "",
        },
        "secret_key": "",
        "migrate": True,
    },
    "sync": {
        "url": "https://test.peeringdb.com/api",
        "user": "",
        "password": "",
        "only": [],
        "strip_tz": 1,
        "timeout": 0,
        # we dont want to use caching during normal tests
        # caching will be tested specifically, so keep blank
        "cache_url": "",
    },
    "log": {"allow_other_loggers": 0, "level": "INFO"},
}

CONFIG_CACHING = {
    "orm": {
        "backend": "django_peeringdb",
        "database": {
            "engine": "sqlite3",
            "host": "",
            "name": ":memory:",
            "password": "",
            "port": 0,
            "user": "",
        },
        "secret_key": "",
        "migrate": True,
    },
    "sync": {
        "url": "https://test.peeringdb.com/api",
        "user": "",
        "password": "",
        "only": [],
        "strip_tz": 1,
        "timeout": 0,
        # we dont want to use caching during normal tests
        # caching will be tested specifically, so keep blank
        "cache_url": "cache://localhost",
    },
    "log": {"allow_other_loggers": 0, "level": "INFO"},
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


set_data_path(__file__, "../data")


def data_path():
    if _DATA_PATH is None:
        raise RuntimeError("data path not set")
    return _DATA_PATH


def reset_data(dumppath=None):

    # Make sure db is empty
    client = peeringdb.client.Client(CONFIG)
    client.backend.delete_all()

    if dumppath is None:
        print("Resetting database to empty")
        return

    path = data_path() / dumppath
    assert path.is_dir(), path
    print("Resetting database from", path)

    client_load(client, path)


# Fixture factory
def client_fixture(filename, scope="function"):
    def func():
        reset_data(filename)
        return peeringdb.client.Client(CONFIG)

    return pytest.fixture(scope=scope)(func)
