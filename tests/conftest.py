import pytest
import logging
import sys, os, tempfile
import os.path as _path
import sqlite3
from contextlib import contextmanager

sys.path.append(_path.join(_path.dirname(__file__)))

import helper
import peeringdb

from peeringdb.client import Client

peeringdb._config_logs(logging.DEBUG)


@pytest.fixture
def config0_dir():
    return str(helper.data_path() / "config0")


client_empty = helper.client_fixture(None)


@pytest.fixture
def patch_version(monkeypatch):
    @contextmanager
    def func():
        with monkeypatch.context() as mc:
            mc.setattr("peeringdb.__version__", "0.1.0")
            yield

    return func()


@pytest.fixture
def patch_backend_version(monkeypatch):
    @contextmanager
    def func():
        with monkeypatch.context() as mc:
            b, (bn, bv) = peeringdb.__backend
            mc.setattr("peeringdb.__backend", (b, (bn, "0.1.0")))
            yield

    return func()
