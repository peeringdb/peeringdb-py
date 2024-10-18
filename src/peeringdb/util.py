import json
import logging
import re

from django.core import serializers

from peeringdb import resource


def load_failed_entries(config):
    """
    Load a list of failed entries from the failed entries file

    Returns:
        list: a list of failed entries
    """

    FAILED_ENTRIES_FILE = config["sync"].get("failed_entries")

    try:
        with open(FAILED_ENTRIES_FILE) as f:
            data = f.read()
            if data:
                return json.loads(data)
            else:
                return []
    except FileNotFoundError:
        return []


def save_failed_entries(config, entries):
    """
    Save a list of failed entries to the failed entries file

    Args:
        entries (list): a list of failed entries
    """
    FAILED_ENTRIES_FILE = config["sync"].get("failed_entries")

    with open(FAILED_ENTRIES_FILE, "w") as f:
        json.dump(entries, f, indent=4)


def log_error(config, resource_tag, pk, error_message):
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


def split_ref(string):
    """splits a string into (tag, id)"""
    re_tag = re.compile(r"^(?P<tag>[a-zA-Z]+)[\s-]*(?P<pk>\d+)$")
    m = re_tag.search(string)
    if not m:
        raise ValueError(f"unable to split string '{string}'")

    return (m.group("tag").lower(), int(m.group("pk")))


def pretty_speed(value):
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
        return value


def group_fields(B, concrete):
    """Partition a concrete's fields into groups based on type"""
    groups = ("scalars", "single_refs", "many_refs")
    ret = {kind: {} for kind in groups}
    fields = B.get_fields(concrete)
    for field in fields:
        name = field.name
        related, multiple = B.is_field_related(concrete, name)

        if related:
            if multiple:
                group = ret["many_refs"]
            else:
                group = ret["single_refs"]
        else:
            group = ret["scalars"]

        group[name] = field
    return ret


def limit_mem(limit=(4 * 1024**3)):
    """Set soft memory limit"""
    rsrc = resource.RLIMIT_DATA
    soft, hard = resource.getrlimit(rsrc)
    resource.setrlimit(rsrc, (limit, hard))  # 4GB
    softnew, _ = resource.getrlimit(rsrc)
    assert softnew == limit

    _log = logging.getLogger(__name__)
    _log.debug("Set soft memory limit: %s => %s", soft, softnew)


def client_dump(client, path):
    """Serialize all objects into JSON files in directory"""
    assert path.is_dir(), path
    for q in client.tags.all():
        ser = serializers.serialize("json", q.all())
        outpath = path / f"{q.res.tag}.json"
        with open(outpath, "w") as out:
            print(f"Writing {outpath}")
            j = json.loads(ser)
            json.dump(j, out, indent=4, sort_keys=True)
            # out.write(ser)


def client_load(client, path):
    """Deserialize from JSON files under directory"""
    for q in client.tags.all():
        respath = path / f"{q.res.tag}.json"
        with open(str(respath)) as fin:
            des = serializers.deserialize("json", fin)
            for obj in des:
                obj.save()


def get_log_level(level_str):
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


def prompt(msg, default=None):
    "Prompt for input"
    if default is not None:
        msg = f"{msg} ({repr(default)})"
    msg = f"{msg}: "
    try:
        s = input(msg)
    except KeyboardInterrupt:
        exit(1)
    except EOFError:
        s = ""
    if not s:
        s = default
    return s


def str_to_bool(value):
    if value in ["y", "yes", "t", "true", "on", "1"]:
        return True
    elif value in ["n", "no", "f", "false", "off", "0"]:
        return False
    raise ValueError
