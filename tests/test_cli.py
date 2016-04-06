
import datetime
import pytest

from click.testing import CliRunner
import os
import peeringdb
from peeringdb import cli
import pytest


test_dir = os.path.relpath(os.path.dirname(__file__))

def test_get_deps():
    assert ['django_peeringdb'] == cli.get_deps('sqlite3')


def test_config():
    runner = CliRunner()
    result = runner.invoke(cli.cli, ['conf_dump'], catch_exceptions=False)
    print result.output
    print result.exception
    print result.exc_info
    assert 0

