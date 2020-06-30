import pytest
import os, re, io

import helper
import peeringdb
from peeringdb import cli as _cli

CMD = 'peeringdb_test'

client = helper.client_fixture('full')

# Run with config dir
class RunCli:
    def __init__(self, c):
        self.config_dir = str(c)
    def __call__(self, *args):
        fullargs = [CMD]
        fullargs.extend(['-C', self.config_dir])
        fullargs.extend(args)
        return _cli.main(fullargs)

@pytest.fixture
def runcli(config0_dir):
    return RunCli(config0_dir)

def test_basic():
    assert _cli.main([CMD]) != 0
    assert _cli.main([CMD, '-h']) == 0

def test_version():
    assert _cli.main([CMD, '--version']) == 0

def test_config(runcli):
    assert _cli.main([CMD, '--config-dir', runcli.config_dir]) != 0
    assert runcli('config', 'show') == 0
    assert runcli('config', 'list-codecs') == 0

# todo:
# check default creation- monkeypatch to avoid clobbering user dir
# pass a config and check that it matches
# config set

NET0 = 'net7'

def test_get(runcli, client):
    assert runcli('get') != 0
    assert runcli('get', NET0) == 0
    assert runcli('get', NET0, '--depth', '1') == 0
    assert runcli('get', NET0, '-D', '2') == 0

def test_get_empty(runcli, client_empty):
    assert runcli('get', NET0) != 0
    assert runcli('get', NET0, '-R') == 0

def test_whois(runcli, client):
    assert runcli('whois') != 0
    assert runcli('whois', NET0) == 0

    assert runcli('whois', 'org7') == 0

    assert runcli('whois', 'as63312') == 0
    assert runcli('whois', 'as00000') == 1

    assert runcli('whois', 'ixnets7') == 0
    assert runcli('whois', 'ixnets0') == 1

def test_droptables(runcli, client, monkeypatch):
    # not empty before drop?
    assert client.tags.net.all()
    # pass in "yes" confirmation
    monkeypatch.setattr('sys.stdin', io.StringIO(u'yes'))
    assert runcli('drop-tables') == 0
    # empty after drop?
    assert not client.tags.net.all()

# Test client/server version errors; should fail with clean output
def test_version_check(runcli, client_empty, patch_version, patch_backend_version, capsys):
    with patch_version:
        assert runcli('get', NET0, '-R') != 0

    out, err = capsys.readouterr()
    assert err.count('\n') < 2

    with patch_backend_version:
        assert runcli('get', NET0, '-R') != 0

# Make sure CLI output is piped to stdout
@pytest.mark.output
def test_output_piping(runcli, client, capsys):
    assert runcli('sync') == 0
    out, err = capsys.readouterr()

    assert err == ''
    assert re.search('Fetching', out)
    assert re.search('Updates', out)

@pytest.mark.output
# Check sanity of output volume
def test_verbosity(runcli, client, capsys):
    assert runcli('sync', '-v') == 0
    outv, errv = capsys.readouterr()
    assert runcli('sync', '-q') == 0
    outq, errq = capsys.readouterr()

    # Verbose output should be longer
    assert len(outq) < len(outv)
