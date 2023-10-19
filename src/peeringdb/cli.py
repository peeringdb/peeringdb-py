import os
import sys
from argparse import ArgumentParser

import peeringdb
from peeringdb import commands, config

COMMANDS = {
    "get": commands.Get,
    "whois": commands.Whois,
    "sync": commands.Sync,
    "config": commands.CommandGroup(
        {
            "set": commands.PromptConfig,
            "show": commands.DumpConfig,
            "list-codecs": commands.ListCodecs,
        },
        help="Configuration management",
    ),
    "drop-tables": commands.DropTables,
    "server": commands.Server,
}


def check_load_config(config_dir):
    convert = False
    loaded = config.read_config(config_dir) or {}

    if config.detect_old(loaded):
        print(
            "Found config file with pre-0.7 schema; backing up and converting to new format"
        )
        convert = True
        cfg = config.convert_old(loaded)
    else:
        cfg = config.default_config()
        config.recursive_update(cfg, loaded)

    if convert:
        config.write_config(cfg, config_dir, backup_existing=True)
    return cfg


def main(args=sys.argv):
    peeringdb._config_logs()

    parser = ArgumentParser()
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + peeringdb.__version__
    )
    parser.add_argument(
        "-C",
        "--config-dir",
        default=os.environ.get("PEERINGDB_HOME", config.DEFAULT_CONFIG_DIR),
        help="Directory containing configuration files",
    )

    cmd = commands.CommandGroup(COMMANDS)
    cmd.add_arguments(parser)

    try:
        options = parser.parse_args(args[1:])
    except SystemExit as e:
        return e.code
    cfg = check_load_config(options.config_dir)

    handler = getattr(options, "handler", options.usage_handler)
    return handler(config=cfg, **vars(options))
