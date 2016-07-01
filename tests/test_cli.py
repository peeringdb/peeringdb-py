
from click.testing import CliRunner
import os
from peeringdb import cli


test_dir = os.path.relpath(os.path.dirname(__file__))


def test_get_deps():
    has_django = 0
    for dep in cli.get_deps('sqlite3'):
        if dep.startswith('django_peeringdb'):
            has_django += 1
    assert 1 == has_django


def test_config():
    runner = CliRunner()
    result = runner.invoke(cli.cli, ['conf_dump'], catch_exceptions=False)
#    print result.output
#    print result.exception
#    print result.exc_info
#    assert 0
