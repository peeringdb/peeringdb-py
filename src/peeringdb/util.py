import json
import logging
import re
import resource as sys_resource
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union, cast

from django.core import serializers

if TYPE_CHECKING:
    from peeringdb.backend import Field, Interface
    from peeringdb.client import Client


def load_failed_entries(
    config: dict[str, Union[str, dict]],
) -> list[dict[str, Union[str, int]]]:
    """
    Load a list of failed entries from the failed entries file

    Returns:
        list: a list of failed entries
    """
    sync_config = config["sync"]
    failed_entries_file = (
        sync_config.get("failed_entries") if isinstance(sync_config, dict) else None
    )

    if failed_entries_file is None:
        return []
    try:
        with open(failed_entries_file) as f:
            data = f.read()
            if data:
                return json.loads(data)
            else:
                return []
    except FileNotFoundError:
        return []


def save_failed_entries(
    config: dict[str, Union[str, dict]], entries: list[dict[str, Union[str, int]]]
) -> None:
    """
    Save a list of failed entries to the failed entries file

    Args:
        entries (list): a list of failed entries
    """
    sync_config = config["sync"]
    failed_entries_file = (
        sync_config.get("failed_entries") if isinstance(sync_config, dict) else None
    )

    if failed_entries_file is None:
        return
    with open(failed_entries_file, "w") as f:
        json.dump(entries, f, indent=4)


def log_error(
    config: dict[str, Union[str, dict]],
    resource_tag: str,
    pk: Union[int, str],
    error_message: str,
) -> None:
    """
    Log an error and save the failed entry to the failed entries file

    Args:
        resource_tag (str): the resource tag
        pk (int): the primary key of the failed entry
        error_message (str): the error message
    """
    logging.error(f"Error syncing {resource_tag}-{pk}: {error_message}")
    failed_entries = load_failed_entries(config)

    new_entry = {"resource_tag": resource_tag, "pk": pk, "error": error_message}
    if new_entry not in failed_entries:
        failed_entries.append(new_entry)
        save_failed_entries(config, failed_entries)


def split_ref(string: str) -> tuple[str, int]:
    """splits a string into (tag, id)"""
    re_tag = re.compile(r"^(?P<tag>[a-zA-Z]+)[\s-]*(?P<pk>\d+)$")
    m = re_tag.search(string)
    if not m:
        raise ValueError(f"unable to split string '{string}'")

    return (m.group("tag").lower(), int(m.group("pk")))


def pretty_speed(value: Union[int, str, None]) -> str:
    if not value:
        return ""
    try:
        value = int(value)
        if value >= 1000000:
            return "%dT" % (value / 10**6)
        elif value >= 1000:
            return "%dG" % (value / 10**3)
        else:
            return "%dM" % value
    except ValueError:
        return str(value)


def group_fields(
    backend: "Interface", concrete: Optional[type]
) -> dict[str, dict[str, "Field"]]:
    """Partition a concrete's fields into groups based on type"""
    groups = ("scalars", "single_refs", "many_refs")
    ret: dict[str, dict[str, Field]] = {kind: {} for kind in groups}
    if concrete is None:
        return ret
    fields = backend.get_fields(concrete)
    # Cast to the expected type to help mypy understand the iteration
    field_list = cast("list[Field]", fields)
    for field in field_list:
        name = getattr(field, "name", None)
        if name is None:
            continue
        field_info = backend.is_field_related(concrete, name)
        if isinstance(field_info, tuple) and len(field_info) == 2:
            related, multiple = field_info
        else:
            related, multiple = False, False

        if related:
            if multiple:
                group = ret["many_refs"]
            else:
                group = ret["single_refs"]
        else:
            group = ret["scalars"]

        group[name] = field
    return ret


def limit_mem(limit: int = (4 * 1024**3)) -> None:
    """Set soft memory limit"""
    rsrc = sys_resource.RLIMIT_DATA
    soft, hard = sys_resource.getrlimit(rsrc)
    sys_resource.setrlimit(rsrc, (limit, hard))  # 4GB
    softnew, _ = sys_resource.getrlimit(rsrc)
    assert softnew == limit

    _log = logging.getLogger(__name__)
    _log.debug("Set soft memory limit: %s => %s", soft, softnew)


def client_dump(client: "Client", path: Path) -> None:
    """Serialize all objects into JSON files in directory"""
    assert path.is_dir(), path
    tags_all: list = getattr(client.tags, "all", lambda: [])()
    for q in tags_all:
        q_all: list = getattr(q, "all", lambda: [])()
        ser = serializers.serialize("json", q_all)
        tag = getattr(getattr(q, "res", None), "tag", "unknown")
        outpath = path / f"{tag}.json"
        with open(outpath, "w") as out:
            print(f"Writing {outpath}")
            j = json.loads(ser)
            json.dump(j, out, indent=4, sort_keys=True)
            # out.write(ser)


def client_load(client: "Client", path: Path) -> None:
    """Deserialize from JSON files under directory"""
    tags_all: list = getattr(client.tags, "all", lambda: [])()
    for q in tags_all:
        tag = getattr(getattr(q, "res", None), "tag", "unknown")
        respath = path / f"{tag}.json"
        with open(str(respath)) as fin:
            des = serializers.deserialize("json", fin)
            for obj in des:
                obj.save()


def get_log_level(level_str: str) -> Optional[int]:
    """
    Convert a string log level to its corresponding logging module level.
    """
    levels = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }
    return levels.get(level_str.strip().upper())


def prompt(msg: str, default: Optional[str] = None) -> Optional[str]:
    "Prompt for input"
    if default is not None:
        msg = f"{msg} ({repr(default)})"
    msg = f"{msg}: "
    try:
        s: Optional[str] = input(msg)
    except KeyboardInterrupt:
        exit(1)
    except EOFError:
        s = ""
    if not s:
        s = default
    return s


def str_to_bool(value: str) -> bool:
    if value in ["y", "yes", "t", "true", "on", "1"]:
        return True
    elif value in ["n", "no", "f", "false", "off", "0"]:
        return False
    raise ValueError
