"""
PeeringDB configuration module.

This defines config schemas and related I/O.
"""
import logging
import os

import munge
from munge.util import recursive_update

from confu import schema as _schema, generator

from peeringdb.util import prompt

DEFAULT_CONFIG_DIR = '~/.peeringdb'


class ClientSchema(_schema.Schema):
    """
    Default confu schema for PeeringDB client.
    """

    class SyncSchema(_schema.Schema):
        url = _schema.Url('url', default='https://www.peeringdb.com/api')
        user = _schema.Str('user', blank=True, default='')
        password = _schema.Str('password', blank=True, default='')
        strip_tz = _schema.Int('strip_tz', default=1)  # FIXME no boolean?
        only = _schema.List('only', item=_schema.Str(), default=[])
        timeout = _schema.Int('timeout', default=0)

    class OrmSchema(_schema.Schema):
        class OrmDbSchema(_schema.Schema):
            engine = _schema.Str('engine', default='sqlite3')
            name = _schema.Str('name', default='peeringdb.sqlite3')
            host = _schema.Str('host', blank=True, default='')
            port = _schema.Int('port', default=0)
            user = _schema.Str('user', blank=True, default='')
            password = _schema.Str('password', blank=True, default='')

        secret_key = _schema.Str('secret_key', blank=True, default='')
        backend = _schema.Str('backend', default='django_peeringdb')
        migrate = _schema.Bool('migrate', default=True)
        database = OrmDbSchema()

    sync = SyncSchema()
    orm = OrmSchema()


CLIENT_SCHEMA = ClientSchema()


def default_config(schema=CLIENT_SCHEMA):
    "Get default config values."
    return generator.generate(schema)
    # return confu.config.Config(schema, data=generator.generate(schemas))


def read_config(conf_dir=DEFAULT_CONFIG_DIR):
    "Find and read config file for a directory, return None if not found."

    conf_path = os.path.expanduser(conf_dir)
    if not os.path.exists(conf_path):
        # only throw if not default
        if conf_dir != DEFAULT_CONFIG_DIR:
            raise IOError("Config directory not found at %s" % (conf_path, ))

    return munge.load_datafile('config', conf_path, default=None)


def load_config(conf_dir=DEFAULT_CONFIG_DIR, schema=CLIENT_SCHEMA):
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
        url = _schema.Url('url', default='https://www.peeringdb.com/api')
        user = _schema.Str('user', blank=True, default='')
        password = _schema.Str('password', blank=True, default='')
        timeout = _schema.Int('timeout', default=0)

    class DatabaseSchema(_schema.Schema):
        engine = _schema.Str('engine', default='sqlite3')
        name = _schema.Str('name', default='peeringdb.sqlite3')
        host = _schema.Str('host', blank=True, default='')
        port = _schema.Int('port', default=0)
        user = _schema.Str('user', blank=True, default='')
        password = _schema.Str('password', blank=True, default='')

    __config_dir__ = _schema.Str('__config_dir__', blank=True, default='')
    peeringdb = PeeringDBSchema()
    database = DatabaseSchema()


_OLD_SCHEMA = _OldClientSchema()


def detect_old(data):
    "Check for a config file with old schema"
    if not data:
        return False
    ok, errors, warnings = _schema.validate(_OLD_SCHEMA, data)
    return ok and not (errors or warnings)


def convert_old(data):
    "Convert config data with old schema to new schema"
    ret = default_config()
    ret['sync'].update(data.get('peeringdb', {}))
    ret['orm']['database'].update(data.get('database', {}))
    return ret


def write_config(data, conf_dir=DEFAULT_CONFIG_DIR, codec="yaml",
                 backup_existing=False):
    """
    Write config values to a file.

    Arguments:
        - conf_dir<str>: path to output directory
        - codec<str>: output field format
        - backup_existing<bool>: if a config file exists,
            make a copy before overwriting
    """
    if not codec:
        codec = 'yaml'
    codec = munge.get_codec(codec)()
    conf_dir = os.path.expanduser(conf_dir)
    if not os.path.exists(conf_dir):
        os.mkdir(conf_dir)

    # Check for existing file, back up if necessary
    outpath = os.path.join(conf_dir, 'config.' + codec.extensions[0])
    if backup_existing and os.path.exists(outpath):
        os.rename(outpath, outpath + '.bak')
    codec.dump(data, open(outpath, 'w'))


def prompt_config(sch, defaults=None, path=None):
    """
    Utility function to recursively prompt for config values

    Arguments:
        - defaults<dict>: default values used for empty inputs
        - path<str>: path to prepend to config keys (eg. "path.keyname")
    """
    out = {}
    for name, attr in sch.attributes():
        fullpath = name
        if path:
            fullpath = '{}.{}'.format(path, name)
        if defaults is None:
            defaults = {}
        default = defaults.get(name)
        if isinstance(attr, _schema.Schema):
            # recurse on sub-schema
            value = prompt_config(attr, defaults=default, path=fullpath)
        else:
            if default is None:
                default = attr.default
            if default is None:
                default = ''
            value = prompt(fullpath, default)
        out[name] = value

    return sch.validate(out)


# def old_to_new(old_config):
#     "Migrate an old-schema config to new schema"
#     _OLD_SCHEMA.validate(old_config)
