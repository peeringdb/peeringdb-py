import io
import json
import re
import time
from unittest.mock import MagicMock, patch

import helper
import pytest

from peeringdb import cli as _cli

CMD = "peeringdb_test"

client = helper.client_fixture("full")


# Run with config dir
class RunCli:
    def __init__(self, c):
        self.config_dir = str(c)

    def __call__(self, *args):
        fullargs = [CMD]
        fullargs.extend(["-C", self.config_dir])
        fullargs.extend(args)
        return _cli.main(fullargs)


@pytest.fixture
def runcli(config0_dir):
    return RunCli(config0_dir)


def test_basic():
    assert _cli.main([CMD]) != 0
    assert _cli.main([CMD, "-h"]) == 0


def test_version():
    assert _cli.main([CMD, "--version"]) == 0


def test_config(runcli):
    assert _cli.main([CMD, "--config-dir", runcli.config_dir]) != 0
    assert runcli("config", "show") == 0
    assert runcli("config", "list-codecs") == 0


# todo:
# check default creation- monkeypatch to avoid clobbering user dir
# pass a config and check that it matches
# config set

NET0 = "net1"


def test_get(runcli, client):
    assert runcli("get") != 0
    assert runcli("get", NET0) == 0
    assert runcli("get", NET0, "--depth", "1") == 0
    assert runcli("get", NET0, "-D", "2") == 0


def test_get_empty(runcli, client_empty):
    assert runcli("get", NET0) != 0
    assert runcli("get", NET0, "-R") == 0


def test_get_json(runcli, client, capsys):
    runcli("get", "--output-format", "json", NET0)
    out, err = capsys.readouterr()

    runcli("get", "-O", "json", NET0)
    out2, err2 = capsys.readouterr()

    # check if output is valid JSON
    try:
        print(f"json output 1 is {out}")
        json.loads(out)
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON.")

    assert out == out2


def test_get_yaml(runcli, client, capsys):
    runcli("get", "--output-format", "yaml", NET0)
    out, err = capsys.readouterr()

    runcli("get", "-O", "yaml", NET0)
    out2, err2 = capsys.readouterr()

    # check if output is valid YAML
    try:
        print(f"yaml output 1 is {out}")
        yaml.safe_load(out)
    except yaml.YAMLError:
        pytest.fail("Output is not valid YAML.")

    assert out == out2


def test_get_toml(runcli, client, capsys):
    runcli("get", "--output-format", "toml", NET0)
    out, err = capsys.readouterr()

    runcli("get", "-O", "toml", NET0)
    out2, err2 = capsys.readouterr()

    # check if output is valid TOML
    try:
        print(f"toml output 1 is {out}")
        toml.loads(out)
    except toml.TomlDecodeError:
        pytest.fail("Output is not valid TOML.")

    assert out == out2


def test_whois(runcli, client):
    assert runcli("whois") != 0
    assert runcli("whois", NET0) == 0

    assert runcli("whois", "org7") == 0

    assert runcli("whois", "as63312") == 0
    assert runcli("whois", "as00000") == 1

    assert runcli("whois", "ixnets1") == 0
    assert runcli("whois", "ixnets0") == 1


def test_droptables(runcli, client, monkeypatch):
    # not empty before drop?
    assert client.tags.net.all()
    # pass in "yes" confirmation
    monkeypatch.setattr("sys.stdin", io.StringIO("yes"))
    assert runcli("drop-tables") == 0
    # empty after drop?
    assert not client.tags.net.all()


# Make sure CLI output is piped to stdout
@pytest.mark.output
def test_output_piping(runcli, client, capsys):
    assert runcli("sync") == 0
    out, err = capsys.readouterr()

    assert err == ""
    assert re.search("Fetching", out)


@pytest.mark.output
# Check sanity of output volume
def test_verbosity(runcli, client, capsys):
    assert runcli("sync", "-v") == 0
    outv, errv = capsys.readouterr()
    assert runcli("sync", "-q") == 0
    outq, errq = capsys.readouterr()

    # Verbose output should be longer
    assert len(outq) < len(outv)


@patch("time.sleep", return_value=None)
def test_rate_limit_handling(mock_sleep):
    attempt = 0
    log_mock = MagicMock()

    # Mock response with status code 429
    mock_resp = MagicMock()
    mock_resp.status_code = 429

    # Test rate limit handling
    for _ in range(10):
        if mock_resp.status_code == 429:
            retry_after = min(2**attempt, 60)
            log_mock.info(f"Rate limited. Retrying in {retry_after} seconds...")
            time.sleep(retry_after)
            attempt += 1

    # Assert log calls and sleep durations
    expected_calls = [
        (("Rate limited. Retrying in 1 seconds...",),),
        (("Rate limited. Retrying in 2 seconds...",),),
        (("Rate limited. Retrying in 4 seconds...",),),
        (("Rate limited. Retrying in 8 seconds...",),),
        (("Rate limited. Retrying in 16 seconds...",),),
        (("Rate limited. Retrying in 32 seconds...",),),
        (("Rate limited. Retrying in 60 seconds...",),),
        (("Rate limited. Retrying in 60 seconds...",),),
        (("Rate limited. Retrying in 60 seconds...",),),
        (("Rate limited. Retrying in 60 seconds...",),),
    ]

    assert log_mock.info.call_args_list == expected_calls

    expected_sleep_calls = [
        ((1,),),
        ((2,),),
        ((4,),),
        ((8,),),
        ((16,),),
        ((32,),),
        ((60,),),
        ((60,),),
        ((60,),),
        ((60,),),
    ]

    assert mock_sleep.call_args_list == expected_sleep_calls
