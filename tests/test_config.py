
import os
from peeringdb import config
import pytest


test_dir = os.path.relpath(os.path.dirname(__file__))
default_config = config.default_config()


def test_default_config():
    cfg = config.get_config(None)
    assert default_config == cfg
    assert '__config_dir__' not in cfg


def test_config_dir():
    with pytest.raises(IOError):
        config.get_config('nonexistant')


def test_config0():
    cfg_dir = os.path.join(test_dir, 'data', 'config0')
    cfg = config.get_config(cfg_dir)

    assert cfg_dir == cfg['__config_dir__']

    assert default_config['database'] == cfg['database']
    assert default_config['peeringdb'] != cfg['peeringdb']
    assert 60 == cfg['peeringdb']['timeout']


def test_write_conf():
    pass
