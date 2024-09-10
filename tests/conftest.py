import logging
from contextlib import contextmanager

import helper
import pytest

import peeringdb

peeringdb._config_logs(logging.INFO)


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


# Register custom pytest marks 'sync' and 'output'
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "sync: mark a test as part of the sync tests"
    )
    config.addinivalue_line(
        "markers", "output: mark a test as part of the output tests"
    )
