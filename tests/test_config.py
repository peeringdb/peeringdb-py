
import datetime
import pytest

from peeringdb import config

def test_default_config():
    cfg = config.get_config()
    assert config.default_config == cfg

def test_write_conf():
    pass
