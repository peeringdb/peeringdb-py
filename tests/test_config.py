import contextlib
import tempfile

import pytest

try:
    from tempfile import TemporaryDirectory
except ImportError:
    import shutil

    @contextlib.contextmanager
    def temporary_directory():  # noqa: N802
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path)

    TemporaryDirectory = temporary_directory


from confu import schema as _schema

from peeringdb import config


# Check round-tripping of config
def test_default_config():
    default_cfg = config.default_config()
    with TemporaryDirectory() as path:
        cfg = config.load_config(path)
    assert default_cfg == cfg


def test_load_config(config0_dir):
    with pytest.raises(IOError):
        config.load_config("nonexistent")

    c = config.load_config(config0_dir)
    default_cfg = config.default_config()
    assert c["sync"] != default_cfg["sync"]
    assert c["sync"]["timeout"] == 60
    assert c["sync"]["strip_tz"] == default_cfg["sync"]["strip_tz"]
    assert c["sync"]["url"] != default_cfg["sync"]["url"]


def test_write():
    with TemporaryDirectory() as td:
        default_cfg = config.default_config()
        config.write_config(default_cfg, td)


def test_schema_migration():
    "Test that old config files are successfully detected and converted to new schema"

    old_data = {
        "peeringdb": {
            "url": "https://test.peeringdb.com/api",
            "user": "dude",
            "password": "12345",
            "timeout": 5,
        },
        "database": {
            "engine": "sqlite3",
            "name": "peeringdb.sqlite3",
            "host": "",
            "port": 9000,
            "user": "guy",
            "password": "abc",
        },
    }
    new_data = {
        "sync": {
            "api_key": "",
            "url": "https://test.peeringdb.com/api",
            "cache_url": "https://public.peeringdb.com",
            "cache_dir": "~/.cache/peeringdb",
            "user": "dude",
            "password": "12345",
            "timeout": 5,
            "only": [],
            "strip_tz": 1,
            "failed_entries": "failed_entries.json",
            "proxy": "",
            "lookback": 1,
        },
        "orm": {
            "backend": "django_peeringdb",
            "secret_key": "",
            "migrate": True,
            "database": {
                "engine": "sqlite3",
                "name": "peeringdb.sqlite3",
                "host": "",
                "port": 9000,
                "user": "guy",
                "password": "abc",
            },
        },
        "log": {"allow_other_loggers": 0, "level": "INFO"},
    }

    # Test detection
    assert config.detect_old(old_data)
    assert not config.detect_old(new_data)
    # Try partial data
    old_part = {
        "peeringdb": {
            "url": "https://test.peeringdb.com/api",
            "timeout": 10,
        }
    }
    assert config.detect_old(old_part)
    # empty case
    assert not config.detect_old({})

    # Test conversion
    conv_data = config.convert_old(old_data)
    assert config.CLIENT_SCHEMA.validate(conv_data)
    assert not config.detect_old(conv_data)
    assert conv_data == new_data

    conv_part = config.convert_old(old_part)
    assert config.CLIENT_SCHEMA.validate(conv_part)


@contextlib.contextmanager
def _patch_input(mp, inputs):
    def _input(_):
        return inputs.pop()

    with mp.context() as m:
        m.setattr("builtins.input", _input)
        yield


def test_proxy_in_default_config():
    cfg = config.default_config()
    assert "proxy" in cfg["sync"]
    assert cfg["sync"]["proxy"] == ""


def test_proxy_roundtrip():
    with TemporaryDirectory() as td:
        cfg = config.default_config()
        cfg["sync"]["proxy"] = "http://proxy.example.com:3128"
        config.write_config(cfg, td)
        loaded = config.load_config(td)
    assert loaded["sync"]["proxy"] == "http://proxy.example.com:3128"


def test_prompt_config_keeps_defaults_on_empty(monkeypatch):
    """Empty answers fall back to the schema defaults (and validate)."""
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    result = config.prompt_config(config.CLIENT_SCHEMA)

    assert config.CLIENT_SCHEMA.validate(result)
    default = config.default_config()
    assert result["sync"]["url"] == default["sync"]["url"]
    assert result["sync"]["timeout"] == default["sync"]["timeout"]
    # non-str default (list) is preserved as its original type, not stringified
    assert result["sync"]["only"] == []


def test_prompt_config_uses_entered_value(monkeypatch):
    """A non-empty answer for a nested field is used; others keep defaults."""

    def _input(prompt_text):
        return "alice" if prompt_text.startswith("sync.user") else ""

    monkeypatch.setattr("builtins.input", _input)
    result = config.prompt_config(config.CLIENT_SCHEMA)

    assert result["sync"]["user"] == "alice"
    assert result["sync"]["url"] == config.default_config()["sync"]["url"]


def test_prompt_config_uses_supplied_defaults(monkeypatch):
    """Supplied defaults are offered (and kept) when the user answers empty."""
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    custom = config.default_config()
    custom["sync"]["user"] = "bob"

    result = config.prompt_config(config.CLIENT_SCHEMA, defaults=custom)
    assert result["sync"]["user"] == "bob"


def test_prompt_config_empty_string_fallback(monkeypatch):
    """A schema attr with no default falls back to an empty string."""

    class _S(_schema.Schema):
        x = _schema.Str("x", default=None, blank=True)

    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    result = config.prompt_config(_S())
    assert result["x"] == ""


def test_write_config_creates_missing_dir(tmp_path):
    target = tmp_path / "newdir"
    config.write_config(config.default_config(), str(target))
    assert target.exists()
    assert list(target.glob("config.*"))


def test_write_config_backs_up_existing(tmp_path):
    config.write_config(config.default_config(), str(tmp_path))
    config.write_config(config.default_config(), str(tmp_path), backup_existing=True)
    assert list(tmp_path.glob("*.bak"))
