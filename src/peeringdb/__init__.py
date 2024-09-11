"""
PeeringDB API
"""

import logging
import sys
from distutils.util import strtobool
from importlib import import_module
from importlib import metadata as importlib_metadata

from peeringdb.util import get_log_level

__version__ = importlib_metadata.version("peeringdb")
_log_level = logging.INFO


def _config_logs(level=None, name=None, allow_other_loggers=False):
    """
    Set up or change logging configuration.

    _config_logs() => idempotent setup;
    _config_logs(L) => change log level
    """
    # print('_config_log', 'from %s' %name if name else '')
    logging_format = "%(message)s"
    # maybe better for log files
    # FORMAT='[%(levelname)s]:%(message)s',

    if isinstance(level, str):
        level = get_log_level(level)

    global _log_level
    if level:
        _log_level = level

    if not isinstance(allow_other_loggers, bool):
        try:
            allow_other_loggers = strtobool(str(allow_other_loggers))
        except Exception:
            allow_other_loggers = False

    if not allow_other_loggers:
        # Reset handlers
        for h in list(logging.root.handlers):
            logging.root.removeHandler(h)

    logging.basicConfig(level=_log_level, format=logging_format, stream=sys.stdout)
    _log = logging.getLogger(__name__)
    _log.setLevel(_log_level)

    # external
    for log in ["urllib3", "asyncio"]:
        logging.getLogger(log).setLevel(_log_level)


class BackendError(Exception):
    pass


# Map external module names to adaptor modules
SUPPORTED_BACKENDS = {
    "django_peeringdb": "django_peeringdb.client_adaptor",
}

__backend = None


def backend_initialized():
    return __backend is not None


def _get():
    global __backend
    if __backend:
        return __backend
    else:
        raise BackendError("Backend not initialized")


def get_backend():
    return _get()[0]


def get_backend_info():
    return _get()[1]


def initialize_backend(name, **kwargs):
    global __backend
    if __backend:
        raise BackendError("Backend already initialized")

    try:
        modname = SUPPORTED_BACKENDS[name]
    except KeyError:
        raise ValueError(f"Not a supported backend module: '{name}'")
    # Load internal module associated with the ORM module
    supportmod = import_module(modname)
    # Backend is any object returned from load_backend
    backend = supportmod.load_backend(**kwargs)

    backend.Backend.setup()
    __backend = (backend.Backend(), (name, backend.__version__))


# TODO
# def is_valid_backend(backend): ...

# namespace imports
