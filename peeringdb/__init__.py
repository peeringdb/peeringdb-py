"""
PeeringDB API
"""
import logging, sys
from importlib import import_module
import pkg_resources

__version__ = pkg_resources.require('peeringdb')[0].version
_log_level = logging.INFO


def _config_logs(lvl=None, name=None):
    """
    Set up or change logging configuration.

    _config_logs() => idempotent setup;
    _config_logs(L) => change log level
    """
    # print('_config_log', 'from %s' %name if name else '')
    FORMAT = '%(message)s'
    # maybe better for log files
    # FORMAT='[%(levelname)s]:%(message)s',

    # Reset handlers
    for h in list(logging.root.handlers):
        logging.root.removeHandler(h)

    global _log_level
    if lvl: _log_level = lvl

    logging.basicConfig(level=_log_level, format=FORMAT, stream=sys.stdout)
    _log = logging.getLogger(__name__)
    _log.setLevel(_log_level)

    # external
    for log in ['urllib3', 'asyncio']:
        logging.getLogger(log).setLevel(_log_level)


class BackendError(Exception):
    pass


# Map external module names to adaptor modules
SUPPORTED_BACKENDS = {
    'django_peeringdb': 'django_peeringdb.client_adaptor',
}

__backend = None


def backend_initialized():
    return __backend is not None


def _get():
    global __backend
    if __backend:
        return __backend
    else:
        raise BackendError('Backend not initialized')


def get_backend():
    return _get()[0]


def get_backend_info():
    return _get()[1]


def initialize_backend(name, **kwargs):
    global __backend
    if __backend:
        raise BackendError('Backend already initialized')

    try:
        modname = SUPPORTED_BACKENDS[name]
    except KeyError:
        raise ValueError("Not a supported backend module: '{}'".format(name))
    # Load internal module associated with the ORM module
    supportmod = import_module(modname)
    # Backend is any object returned from load_backend
    B = supportmod.load_backend(**kwargs)

    B.Backend.setup()
    __backend = (B.Backend(), (name, B.__version__))


# TODO
# def is_valid_backend(backend): ...

# namespace imports
from peeringdb.client import Client as PeeringDB
from peeringdb.config import load_config
from peeringdb.resource import get_resource
