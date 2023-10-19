import logging
import os
import subprocess
import sys

import munge

import peeringdb
from peeringdb import config as cfg
from peeringdb import resource, util
from peeringdb.client import Client
from peeringdb.output._yaml import dump
from peeringdb.whois import WhoisFormat


def _handler(func):
    """Decorate a command handler"""

    def _wrapped(*a, **k):
        r = func(*a, **k)
        if r is None:
            r = 0
        return r

    return staticmethod(_wrapped)


def add_subcommands(parser, commands):
    """Add commands to a parser"""
    subps = parser.add_subparsers()
    for cmd, cls in commands:
        subp = subps.add_parser(cmd, help=cls.__doc__)
        add_args = getattr(cls, "add_arguments", None)
        if add_args:
            add_args(subp)
        handler = getattr(cls, "handle", None)
        if handler:
            subp.set_defaults(handler=handler)


class CommandGroup:
    """A group of nested subcommands."""

    def __init__(self, commands, help=None):
        """
        Arguments:
            - commands<dict>: dict of command names to handler classes
        """
        self.commands = commands
        if help:
            self.__doc__ = help

    def add_arguments(self, parser):
        add_subcommands(parser, self.commands.items())

        def _usage(**_):
            parser.print_usage()
            return 1

        parser.set_defaults(usage_handler=_usage)


class Get:
    """Get a resource"""

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("poids", nargs="+", help="Object IDs")
        parser.add_argument(
            "--depth",
            "-D",
            default=0,
            type=int,
            help="How many levels of nested objects to fetch",
        )
        parser.add_argument(
            "--output-format", "-O", default="yaml", help="Output data format"
        )
        parser.add_argument(
            "--remote",
            "-R",
            action="store_true",
            default=False,
            help="Fall back to API request if object is not found",
        )

    @_handler
    def handle(config, poids, output_format, depth, remote, **_):
        client = Client(config)
        for poid in poids:
            (tag, pk) = util.split_ref(poid)
            res = resource.get_resource(tag)
            backend = peeringdb.get_backend()
            try:
                obj = client.get(res, pk)
            except backend.object_missing_error(backend.get_concrete(res)):
                if remote:
                    obj = client.fetcher.get(res.tag, pk, depth=depth)
                else:
                    print(f"Not found: {tag}-{pk}", file=sys.stderr)
                    return 1

            dump(obj, depth, sys.stdout)


class Whois:
    """Simulate a whois lookup;
    supports
         as<ASN> : query by AS;
         ixnets<net ID> : query networks on an IX
    """

    @staticmethod
    def add_arguments(parser):
        parser.add_argument(
            "poids", nargs="+", help="Object IDs, or { as<ASN> | ixnets<net ID> }..."
        )

    @_handler
    def handle(config, poids, **_):
        client = Client(config)
        fmt = WhoisFormat()

        for poid in poids:
            (tag, key) = util.split_ref(poid)
            try:
                if tag == "as":
                    objs = client.fetcher._get("net", asn=key, depth=2)
                elif tag == "ixnets":
                    objs = client.fetcher._get("net", ix_id__in=key, depth=2)
                else:
                    objs = client.fetcher._get(tag, pk=key, depth=2)
            except Exception as e:
                print(f"Not found: {tag}={key}: {e}", file=sys.stderr)
                return 1
            if len(objs) == 0:
                print(f"Not found: {tag}={key}:", file=sys.stderr)
                return 1

            fmt.display(tag, objs[0])


class DumpConfig:
    """Output current config"""

    @staticmethod
    def add_arguments(parser):
        parser.add_argument(
            "--output-format", default="yaml", help="output data format"
        )

    @_handler
    def handle(config, output_format, **_):
        codec = munge.get_codec(output_format)()
        codec.dump(config, sys.stdout)


class PromptConfig:
    """Prompt for configuration values and save to a file"""

    @staticmethod
    def add_arguments(parser):
        parser.add_argument(
            "--output-format", default="yaml", help="output data format"
        )
        parser.add_argument(
            "--defaults",
            "-n",
            action="store_true",
            default=False,
            help="do not prompt, just write defaults to file",
        )

    @_handler
    def handle(config, defaults, config_dir, output_format, **_):
        if defaults:
            newconfig = config
            outdir = config_dir
        else:
            newconfig = cfg.prompt_config(cfg.CLIENT_SCHEMA, defaults=config)
            outdir = util.prompt("Output directory", config_dir)
        cfg.write_config(newconfig, outdir, codec=output_format)


class ListCodecs:
    """List available codecs"""

    @_handler
    def handle(**_):
        print(" ".join(munge.codec.list_codecs()))


class Sync:
    """Synchronize local tables to PeeringDB"""

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("-v", "--verbose", action="count", help="Be more verbose")
        parser.add_argument("-q", "--quiet", action="count", help="Be more quiet")
        parser.add_argument(
            "--fetch-private",
            action="store_true",
            default=False,
            help="Fetch private data (needs API key set)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Do not actually perform updates",
        )
        # parser.add_argument('--only', action='append', default=[],
        #                     help='Only process this table')
        # parser.add_argument('--limit', type=int, default=0,
        #                     help="Limit objects retrieved, retrieve all if 0 (default)")
        parser.add_argument(
            "--init",
            action="store_true",
            default=False,
            help="Only initialize the database; do not sync",
        )
        parser.add_argument(
            "--since",
            action="store",
            default=-1,
            type=int,
            help="Only fetch updates since when (<0 for since last sync)",
        )

    @_handler
    def handle(config, verbose, quiet, init, since, **kwargs):
        rs = resource.all_resources()
        # if only: rs = [resource.get_resource(tag) for tag in only]

        loglvl = 1 + (verbose or 0) - (quiet or 0)
        if loglvl > 1:
            peeringdb._config_logs(logging.DEBUG)
        if loglvl < 1:
            peeringdb._config_logs(logging.WARNING)

        client = Client(config, **kwargs)
        # todo verify table schema
        if init:
            return

        if loglvl >= 0:
            print("Syncing to", config["sync"]["url"])

        if since < 0:
            since = None

        # if fetch-private and PDB_SYNC_API_KEY isn't set, warn
        if kwargs["fetch_private"] and not config["sync"].get("api_key"):
            print()
            print(
                "Warning: api key not set, private data will not be fetched. Set it either directly in the config or provide via the PDB_SYNC_API_KEY environment variable.",
                file=sys.stderr,
            )
            print()
            kwargs["fetch_private"] = False

        client.updater.update_all(rs, since, fetch_private=kwargs["fetch_private"])


class DropTables:
    """Drop all database tables"""

    @_handler
    def handle(config, **_):
        Client(config)
        backend = peeringdb.get_backend()
        backend.delete_all()


class Server:
    """Configure Peeringdb Server"""

    @staticmethod
    def add_arguments(parser):
        parser.add_argument(
            "--setup",
            action="store_true",
            default=False,
            help="Build and setup peeringdb server container",
        )
        parser.add_argument(
            "--start",
            action="store_true",
            default=False,
            help="Start peeringdb server container",
        )
        parser.add_argument(
            "--stop",
            action="store_true",
            default=False,
            help="Stop peeringdb server container",
        )

    @_handler
    def handle(config, setup, start, stop, **_):
        parent_directory = os.path.abspath(os.path.join(os.getcwd()))
        clone_path = os.path.join(parent_directory, "peeringdb_server")

        if setup:
            # Clone the GitHub repository
            # TODO: use latest release? (peeringdb server currently does no publish releases, just tags)
            # TODO: use git module instead of subprocess?
            print("Setup-----------")
            subprocess.run(
                [
                    "git",
                    "clone",
                    "https://github.com/peeringdb/peeringdb.git",
                    clone_path,
                ]
            )

            # Run setup.sh inside the cloned repository
            subprocess.run(["./Ctl/local/setup.sh"], cwd=clone_path)

        if start:
            try:
                subprocess.run(["./Ctl/local/compose.sh", "up", "-d"], cwd=clone_path)
            except FileNotFoundError:
                print(
                    f"{clone_path} directory not found, make sure that you already run 'peeringdb server --setup'"
                )

        if stop:
            try:
                subprocess.run(["./Ctl/local/compose.sh", "down"], cwd=clone_path)
            except FileNotFoundError:
                print(
                    f"{clone_path} directory not found, make sure that you already run 'peeringdb server --setup'"
                )
