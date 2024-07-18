import contextlib
import tempfile

import pytest
from confu.exceptions import ValidationError

try:
    from tempfile import TemporaryDirectory
except ImportError:
    import shutil

    @contextlib.contextmanager
    def TemporaryDirectory():
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path)


import helper

import peeringdb
from peeringdb import config


# Check round-tripping of config
def test_default_config():
    DEFAULT = config.default_config()
    with TemporaryDirectory() as path:
        cfg = config.load_config(path)
    assert DEFAULT == cfg


def test_load_config(config0_dir):
    with pytest.raises(IOError):
        config.load_config("nonexistent")

    c = config.load_config(config0_dir)
    DEFAULT = config.default_config()
    assert c["sync"] != DEFAULT["sync"]
    assert c["sync"]["timeout"] == 60
    assert c["sync"]["strip_tz"] == DEFAULT["sync"]["strip_tz"]
    assert c["sync"]["url"] != DEFAULT["sync"]["url"]


def test_write():
    with TemporaryDirectory() as td:
        DEFAULT = config.default_config()
        config.write_config(DEFAULT, td)


def test_schema_migration():
    "Test that old config files are successfully detected and converted to new schema"

    old_data = {
        "peeringdb": {
            "url": "https://test.peeringdb.com/api",
            "user": "dude",
            "password": "12345",
            "timeout": 5,
        },
        "database": {
            "engine": "sqlite3",
            "name": "peeringdb.sqlite3",
            "host": "",
            "port": 9000,
            "user": "guy",
            "password": "abc",
        },
    }
    new_data = {
        "sync": {
            "api_key": "",
            "url": "https://test.peeringdb.com/api",
            "cache_url": "https://public.peeringdb.com",
            "cache_dir": "~/.cache/peeringdb",
            "user": "dude",
            "password": "12345",
            "timeout": 5,
            "only": [],
            "strip_tz": 1,
        },
        "orm": {
            "backend": "django_peeringdb",
            "secret_key": "",
            "migrate": True,
            "database": {
                "engine": "sqlite3",
                "name": "peeringdb.sqlite3",
                "host": "",
                "port": 9000,
                "user": "guy",
                "password": "abc",
            },
        },
        "log": {"allow_other_loggers": 0, "level": "INFO"},
    }

    # Test detection
    assert config.detect_old(old_data)
    assert not config.detect_old(new_data)
    # Try partial data
    old_part = {
        "peeringdb": {
            "url": "https://test.peeringdb.com/api",
            "timeout": 10,
        }
    }
    assert config.detect_old(old_part)
    # empty case
    assert not config.detect_old({})

    # Test conversion
    conv_data = config.convert_old(old_data)
    assert config.CLIENT_SCHEMA.validate(conv_data)
    assert not config.detect_old(conv_data)
    assert conv_data == new_data

    conv_part = config.convert_old(old_part)
    assert config.CLIENT_SCHEMA.validate(conv_part)


@contextlib.contextmanager
def _patch_input(mp, inputs):
    def _input(_):
        return inputs.pop()

    with mp.context() as m:
        m.setattr("builtins.input", _input)
        yield


# TODO test_prompt_config
