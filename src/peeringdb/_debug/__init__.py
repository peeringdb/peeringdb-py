import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

# import pdb

if TYPE_CHECKING:
    from django.core.exceptions import ValidationError

    from peeringdb.backend import Interface


def log_validation_errors(
    backend: "Interface", e: "ValidationError", obj: object, k: str
) -> None:
    log = logging.getLogger("peeringdb.sync")
    log.debug(f"{e} : errors: {e.message_dict}")
    for k, v in e.message_dict.items():
        field = backend.get_field(obj, k)
        try:
            log.debug(f"{k}: {getattr(obj, k)}, dict: {field.__dict__}")
        except backend.object_missing_error():
            log.debug(f"{k}: Missing Object, dict: {field.__dict__}")


def try_or_debug(f: Callable[[], object]) -> object:
    try:
        return f()
    except Exception:
        # pdb.set_trace() ???
        raise
