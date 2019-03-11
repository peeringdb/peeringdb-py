from __future__ import print_function
import sys
import calendar
import logging
from argparse import ArgumentParser

import munge
import peeringdb
from peeringdb import resource, util, config as cfg
from peeringdb.client import Client
from peeringdb.whois import WhoisFormat
from peeringdb.output._yaml import dump
from peeringdb.config import prompt_config, write_config


def _handler(func):
    "Decorate a command handler"

    def _wrapped(*a, **k):
        r = func(*a, **k)
        if r is None: r = 0
        return r

    return staticmethod(_wrapped)


def add_subcommands(parser, commands):
    "Add commands to a parser"
    subps = parser.add_subparsers()
    for cmd, cls in commands:
        subp = subps.add_parser(cmd, help=cls.__doc__)
        add_args = getattr(cls, 'add_arguments', None)
        if add_args:
            add_args(subp)
        handler = getattr(cls, 'handle', None)
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
    "Get a resource"

    @staticmethod
    def add_arguments(parser):
        parser.add_argument('poids', nargs='+', help='Object IDs')
        parser.add_argument('--depth', '-D', default=0, type=int,
                            help='How many levels of nested objects to fetch')
        parser.add_argument('--output-format', '-O', default='yaml',
                            help='Output data format')
        parser.add_argument(
            '--remote', '-R', action='store_true', default=False,
            help='Fall back to API request if object is not found')

    @_handler
    def handle(config, poids, output_format, depth, remote, **_):
        client = Client(config)
        for poid in poids:
            (tag, pk) = util.split_ref(poid)
            res = resource.get_resource(tag)
            B = peeringdb.get_backend()
            try:
                obj = client.get(res, pk)
            except B.object_missing_error(B.get_concrete(res)) as e:
                if remote:
                    obj = client.fetch(res, pk, depth)[0]
                else:
                    print('Not found: {}-{}'.format(tag, pk), file=sys.stderr)
                    return 1

            dump(obj, depth, sys.stdout)


def _lookup_tag(tag, key, getfunc):
    if tag == 'as':
        return getfunc(resource.Network, asn=key)
    elif tag == 'ixnets':
        return getfunc(resource.Network, ix_id__in=key)
    else:
        return getfunc(resource.get_resource(tag), id=key)


class Whois:
    """Simulate a whois lookup;
       supports
            as<ASN> : query by AS;
            ixnets<net ID> : query networks on an IX
    """

    @staticmethod
    def add_arguments(parser):
        parser.add_argument(
            'poids', nargs='+',
            help='Object IDs, or { as<ASN> | ixnets<net ID> }...')

    @_handler
    def handle(config, poids, **_):
        client = Client(config)

        def get(res, **kwargs):
            objs = client.fetch_all(res, depth=2, **kwargs)
            if not objs:
                raise peeringdb.sync.NotFoundException
            return objs

        fmt = WhoisFormat()
        for poid in poids:
            (tag, key) = util.split_ref(poid)
            try:
                data = _lookup_tag(tag, key, get)
            except peeringdb.sync.NotFoundException:
                print('Not found: resource for {}={}'.format(tag, key),
                      file=sys.stderr)
                return 1
            fmt.display(tag, data[0])


class DumpConfig:
    """ Output current config """

    @staticmethod
    def add_arguments(parser):
        parser.add_argument('--output-format', default='yaml',
                            help='output data format')

    @_handler
    def handle(config, output_format, **_):
        codec = munge.get_codec(output_format)()
        codec.dump(config, sys.stdout)


class PromptConfig:
    """ Prompt for configuration values and save to a file """

    @staticmethod
    def add_arguments(parser):
        parser.add_argument('--output-format', default='yaml',
                            help='output data format')
        parser.add_argument('--defaults', '-n', action='store_true',
                            default=False,
                            help='do not prompt, just write defaults to file')

    @_handler
    def handle(config, defaults, config_dir, output_format, **_):
        if defaults:
            newconfig = config
            outdir = config_dir
        else:
            newconfig = cfg.prompt_config(cfg.CLIENT_SCHEMA, defaults=config)
            outdir = util.prompt('Output directory', config_dir)
        cfg.write_config(newconfig, outdir, codec=output_format)


class ListCodecs:
    "List available codecs"

    @_handler
    def handle(**_):
        print(' '.join(munge.codec.list_codecs()))


class Sync:
    "Synchronize local tables to PeeringDB"

    @staticmethod
    def add_arguments(parser):
        parser.add_argument('-v', '--verbose', action='count',
                            help='Be more verbose')
        parser.add_argument('-q', '--quiet', action='count',
                            help='Be more quiet')
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Do not actually perform updates')
        # parser.add_argument('--only', action='append', default=[],
        #                     help='Only process this table')
        # parser.add_argument('--limit', type=int, default=0,
        #                     help="Limit objects retrieved, retrieve all if 0 (default)")
        parser.add_argument('--init', action='store_true', default=False,
                            help='Only initialize the database; do not sync')

    @_handler
    def handle(config, verbose, quiet, init, **kwargs):
        rs = resource.all_resources()
        # if only: rs = [resource.get_resource(tag) for tag in only]

        loglvl = 1 + (verbose or 0) - (quiet or 0)
        if loglvl > 1:
            peeringdb._config_logs(logging.DEBUG)
        if loglvl < 1:
            peeringdb._config_logs(logging.WARNING)

        client = Client(config, **kwargs)
        # todo verify table schema
        if init: return

        if loglvl >= 0:
            print("Syncing to", config['sync']['url'])

        client.update_all(rs)


class DropTables:
    "Drop all database tables"

    @_handler
    def handle(config, **_):
        client = Client(config)
        B = peeringdb.get_backend()
        B.delete_all()
