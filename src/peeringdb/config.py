"""
PeeringDB configuration module.

This defines config schemas and related I/O.
"""

import os

import munge
from confu import generator
from confu import schema as _schema
from munge.util import recursive_update

from peeringdb._types import Value
from peeringdb.util import prompt

DEFAULT_CONFIG_DIR = "~/.peeringdb"


class ClientSchema(_schema.Schema):
    """
    Default confu schema for PeeringDB client.
    """

    class SyncSchema(_schema.Schema):
        url = _schema.Url(
            "url",
            default=os.environ.get("PDB_SYNC_URL", "https://www.peeringdb.com/api"),
        )
        cache_url = _schema.Url(
            "url",
            default=os.environ.get(
                "PDB_SYNC_CACHE_URL", "https://public.peeringdb.com"
            ),
        )
        cache_dir = _schema.Str(
            "cache_dir",
            default=os.environ.get("PDB_SYNC_CACHE_DIR", "~/.cache/peeringdb"),
        )
        user = _schema.Str(
            "user", blank=True, default=os.environ.get("PDB_SYNC_USER", "")
        )
        password = _schema.Str(
            "password", blank=True, default=os.environ.get("PDB_SYNC_PASSWORD", "")
        )
        strip_tz = _schema.Int(
            "strip_tz", default=int(os.environ.get("PDB_SYNC_STRIP_TZ", "1"))
        )
        only = _schema.List(
            "only",
            item=_schema.Str(),
            default=(
                os.environ.get("PDB_SYNC_ONLY", "").split(",")
                if os.environ.get("PDB_SYNC_ONLY")
                else []
            ),
        )
        timeout = _schema.Int(
            "timeout", default=int(os.environ.get("PDB_SYNC_TIMEOUT", "0"))
        )
        api_key = _schema.Str(
            "api_key", blank=True, default=os.environ.get("PDB_SYNC_API_KEY", "")
        )
        failed_entries = _schema.Str(
            "failed_entries",
            default=os.environ.get("FAILED_ENTRIES_FILE", "failed_entries.json"),
        )
        proxy = _schema.Str(
            "proxy", blank=True, default=os.environ.get("PDB_SYNC_PROXY", "")
        )
        lookback = _schema.Int(
            "lookback",
            default=int(os.environ.get("PDB_SYNC_LOOKBACK", "1")),
        )

    class OrmSchema(_schema.Schema):
        class OrmDbSchema(_schema.Schema):
            engine = _schema.Str(
                "engine", default=os.environ.get("PDB_ORM_DB_ENGINE", "sqlite3")
            )
            name = _schema.Str(
                "name", default=os.environ.get("PDB_ORM_DB_NAME", "peeringdb.sqlite3")
            )
            host = _schema.Str(
                "host", blank=True, default=os.environ.get("PDB_ORM_DB_HOST", "")
            )
            port = _schema.Int(
                "port", default=int(os.environ.get("PDB_ORM_DB_PORT", "0"))
            )
            user = _schema.Str(
                "user", blank=True, default=os.environ.get("PDB_ORM_DB_USER", "")
            )
            password = _schema.Str(
                "password",
                blank=True,
                default=os.environ.get("PDB_ORM_DB_PASSWORD", ""),
            )

        secret_key = _schema.Str(
            "secret_key", blank=True, default=os.environ.get("PDB_ORM_SECRET_KEY", "")
        )
        backend = _schema.Str(
            "backend", default=os.environ.get("PDB_ORM_BACKEND", "django_peeringdb")
        )
        migrate = _schema.Bool("migrate", default=True)
        database = OrmDbSchema()

    class LogSchema(_schema.Schema):
        allow_other_loggers = _schema.Int(
            "allow_other_loggers", default=os.environ.get("ALLOW_OTHER_LOGGERS", 0)
        )
        level = _schema.Str("log_level", default=os.environ.get("LOG_LEVEL", "INFO"))

    sync = SyncSchema()
    orm = OrmSchema()
    log = LogSchema()


CLIENT_SCHEMA = ClientSchema()


def default_config(
    schema: _schema.Schema = CLIENT_SCHEMA,
) -> dict[str, Value]:
    "Get default config values."
    return generator.generate(schema)
    # return confu.config.Config(schema, data=generator.generate(schemas))


def read_config(
    conf_dir: str = DEFAULT_CONFIG_DIR,
) -> dict[str, Value] | None:
    "Find and read config file for a directory, return None if not found."

    conf_path = os.path.expanduser(conf_dir)
    if not os.path.exists(conf_path):
        # only throw if not default
        if conf_dir != DEFAULT_CONFIG_DIR:
            raise OSError(f"Config directory not found at {conf_path}")

    return munge.load_datafile("config", conf_path, default=None)


def load_config(
    conf_dir: str = DEFAULT_CONFIG_DIR, schema: _schema.Schema = CLIENT_SCHEMA
) -> dict[str, Value]:
    """
    Load config files from the specified directory, using defaults for missing values.
    Directory should contain a file named config.<ext> where <ext> is a
    supported config file format.
    """
    data = default_config(schema)
    config = read_config(conf_dir)
    if config:
        recursive_update(data, config)
    return data


class _OldClientSchema(_schema.Schema):
    class PeeringDBSchema(_schema.Schema):
        url = _schema.Url("url", default="https://www.peeringdb.com/api")
        user = _schema.Str("user", blank=True, default="")
        password = _schema.Str("password", blank=True, default="")
        timeout = _schema.Int("timeout", default=0)

    class DatabaseSchema(_schema.Schema):
        engine = _schema.Str("engine", default="sqlite3")
        name = _schema.Str("name", default="peeringdb.sqlite3")
        host = _schema.Str("host", blank=True, default="")
        port = _schema.Int("port", default=0)
        user = _schema.Str("user", blank=True, default="")
        password = _schema.Str("password", blank=True, default="")

    __config_dir__ = _schema.Str("__config_dir__", blank=True, default="")
    peeringdb = PeeringDBSchema()
    database = DatabaseSchema()


_OLD_SCHEMA = _OldClientSchema()


def detect_old(data: dict[str, Value] | None) -> bool:
    "Check for a config file with old schema"
    if not data:
        return False
    ok, errors, warnings = _schema.validate(_OLD_SCHEMA, data)
    return ok and not (errors or warnings)


def convert_old(
    data: dict[str, Value],
) -> dict[str, Value]:
    "Convert config data with old schema to new schema"
    ret = default_config()
    sync = ret["sync"]
    old_peeringdb = data.get("peeringdb", {})
    if isinstance(sync, dict) and isinstance(old_peeringdb, dict):
        sync.update(old_peeringdb)
    orm = ret["orm"]
    if isinstance(orm, dict):
        orm_database = orm.get("database", {})
        old_database = data.get("database", {})
        if isinstance(orm_database, dict) and isinstance(old_database, dict):
            orm_database.update(old_database)
    return ret


def write_config(
    data: dict[str, Value],
    conf_dir: str = DEFAULT_CONFIG_DIR,
    codec: str = "yaml",
    backup_existing: bool = False,
) -> None:
    """
    Write config values to a file.

    Arguments:
        - conf_dir<str>: path to output directory
        - codec<str>: output field format
        - backup_existing<bool>: if a config file exists,
            make a copy before overwriting
    """
    codec_obj = munge.get_codec(codec or "yaml")()
    conf_dir = os.path.expanduser(conf_dir)
    if not os.path.exists(conf_dir):
        os.mkdir(conf_dir)

    # Check for existing file, back up if necessary
    outpath = os.path.join(conf_dir, "config." + codec_obj.extensions[0])
    if backup_existing and os.path.exists(outpath):
        os.rename(outpath, outpath + ".bak")
    codec_obj.dump(data, open(outpath, "w"))


def prompt_config(
    sch: _schema.Schema,
    defaults: dict[str, Value] | None = None,
    path: str | None = None,
) -> dict[str, Value]:
    """
    Utility function to recursively prompt for config values

    Arguments:
        - defaults<dict>: default values used for empty inputs
        - path<str>: path to prepend to config keys (eg. "path.keyname")
    """
    out: dict[str, Value] = {}
    if defaults is None:
        defaults = {}
    for name, attr in sch.attributes():
        fullpath = name
        if path:
            fullpath = f"{path}.{name}"
        default = defaults.get(name)
        if isinstance(attr, _schema.Schema):
            # recurse on sub-schema
            sub_defaults = default if isinstance(default, dict) else None
            out[name] = prompt_config(attr, defaults=sub_defaults, path=fullpath)
        else:
            resolved: Value
            if default is not None:
                resolved = default
            elif attr.default is not None:
                resolved = attr.default
            else:
                resolved = ""
            # confu scalar defaults may be str/int/bool/list; prompt() only needs a
            # display string. An empty answer keeps the raw default (its original
            # type), which matters for non-str fields (e.g. the "only" list).
            display_default = resolved if isinstance(resolved, str) else str(resolved)
            entered = prompt(fullpath, display_default)
            if entered is None or entered == display_default:
                out[name] = resolved
            else:
                out[name] = entered

    return sch.validate(out)


# def old_to_new(old_config):
#     "Migrate an old-schema config to new schema"
#     _OLD_SCHEMA.validate(old_config)
