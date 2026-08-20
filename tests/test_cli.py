import copy
import io
import json
import re
import time
from unittest.mock import MagicMock, patch

import helper
import pytest
import toml
import yaml

from peeringdb import cli as _cli
from peeringdb import commands, util

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


def test_config_set_defaults(tmp_path):
    # `config set -n` writes the default config without prompting
    rc = _cli.main([CMD, "-C", str(tmp_path), "config", "set", "-n"])
    assert rc == 0
    assert list(tmp_path.glob("config.*"))


def test_config_set_interactive(tmp_path, monkeypatch):
    # empty answers keep defaults; the output-dir prompt defaults to the config dir
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    rc = _cli.main([CMD, "-C", str(tmp_path), "config", "set"])
    assert rc == 0
    assert list(tmp_path.glob("config.*"))


def test_sync_init_only(runcli, client):
    # --init returns before syncing
    assert runcli("sync", "--init") == 0


def test_get_unsupported_output_format(runcli, client, monkeypatch):
    def _raise(_fmt):
        raise TypeError

    monkeypatch.setattr("peeringdb.commands.munge.get_codec", _raise)
    assert runcli("get", NET0) == 1


def test_check_load_config_converts_old_schema(tmp_path):
    old = {
        "peeringdb": {"url": "https://old.example.com/api", "timeout": 5},
        "database": {
            "engine": "sqlite3",
            "name": "peeringdb.sqlite3",
            "host": "",
            "port": 0,
            "user": "",
            "password": "",
        },
    }
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(old))

    cfg = _cli.check_load_config(str(tmp_path))
    assert cfg["sync"]["url"] == "https://old.example.com/api"
    assert list(tmp_path.glob("*.bak"))  # existing file backed up during conversion


def test_server_noop(runcli):
    # no action flags -> nothing to do, exits cleanly
    assert runcli("server") == 0


def test_server_full_lifecycle(runcli, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.run", lambda *a, **k: calls.append(a))
    assert runcli("server", "--setup", "--start", "--stop") == 0
    # git clone + setup.sh + compose up + compose down
    assert len(calls) >= 3


def test_server_setup_invokes_subprocess(runcli, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.run", lambda *a, **k: calls.append((a, k)))
    assert runcli("server", "--setup") == 0
    assert calls  # git clone + setup.sh were invoked


def test_server_start_missing_dir(runcli, monkeypatch, capsys):
    def _missing(*_a, **_k):
        raise FileNotFoundError

    monkeypatch.setattr("subprocess.run", _missing)
    assert runcli("server", "--start") == 0
    out, _ = capsys.readouterr()
    assert "directory not found" in out


def test_server_stop_missing_dir(runcli, monkeypatch, capsys):
    def _missing(*_a, **_k):
        raise FileNotFoundError

    monkeypatch.setattr("subprocess.run", _missing)
    assert runcli("server", "--stop") == 0
    out, _ = capsys.readouterr()
    assert "directory not found" in out


def _sync_handle(config, **over):
    kwargs = dict(
        config=config, verbose=0, quiet=0, init=False, since=-1, fetch_private=False
    )
    kwargs.update(over)
    return commands.Sync.handle(**kwargs)


def test_sync_handle_warns_without_api_key(client, monkeypatch, capsys):
    monkeypatch.setattr(
        "peeringdb._update.Updater.update_all", lambda self, *a, **k: None
    )
    monkeypatch.setattr("peeringdb.commands.load_failed_entries", lambda config: [])

    rc = _sync_handle(copy.deepcopy(helper.CONFIG), fetch_private=True)
    assert rc == 0
    assert "api key not set" in capsys.readouterr().err


def test_sync_handle_retries_failed_entries(client, monkeypatch):
    monkeypatch.setattr(
        "peeringdb._update.Updater.update_all", lambda self, *a, **k: None
    )
    monkeypatch.setattr(
        "peeringdb.commands.load_failed_entries",
        lambda config: [{"resource_tag": "net", "pk": 1}],
    )
    retried = []
    monkeypatch.setattr(
        commands.Sync,
        "retry_failed_entries",
        lambda client, entries: retried.append(entries),
    )

    assert _sync_handle(copy.deepcopy(helper.CONFIG)) == 0
    assert retried


def test_sync_handle_logs_update_error(client, monkeypatch):
    def _raise(self, *a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr("peeringdb._update.Updater.update_all", _raise)
    monkeypatch.setattr("peeringdb.commands.load_failed_entries", lambda config: [])

    # the sync error is caught and logged, not propagated
    assert _sync_handle(copy.deepcopy(helper.CONFIG)) == 0


def test_sync_retry_failed_entries(client, monkeypatch):
    # succeeded entries are dropped; still-failing ones are retained
    calls = []

    def _update_one(res, pk):
        calls.append(pk)
        if pk == 2:
            raise RuntimeError("still failing")

    monkeypatch.setattr(client.updater, "update_one", _update_one)
    entries = [
        {"resource_tag": "net", "pk": 1, "error": "x"},
        {"resource_tag": "net", "pk": 2, "error": "y"},
    ]
    commands.Sync.retry_failed_entries(client, entries)

    assert calls == [1, 2]
    assert entries == [{"resource_tag": "net", "pk": 2, "error": "y"}]


def test_client_dump_and_load_roundtrip(client, tmp_path):
    util.client_dump(client, tmp_path)
    assert list(tmp_path.glob("*.json"))

    client.backend.delete_all()
    assert not client.tags.net.all()

    util.client_load(client, tmp_path)
    assert client.tags.net.all()


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
