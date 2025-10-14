import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from peeringdb import util


def test_split_ref():
    assert ("net", 20) == util.split_ref("net20")
    assert ("net", 20) == util.split_ref("NET20")
    assert ("net", 20) == util.split_ref("net 20")
    assert ("net", 20) == util.split_ref("net-20")


def test_split_ref_exc():
    with pytest.raises(ValueError):
        util.split_ref("asdf123a")
    with pytest.raises(ValueError):
        util.split_ref("123asdf")


def test_load_failed_entries_invalid_json():
    """Test that load_failed_entries handles invalid JSON gracefully."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"invalid": json,}')
        f.flush()

        config = {"sync": {"failed_entries": f.name}}

        with patch("peeringdb.util.logging.warning") as mock_warning:
            result = util.load_failed_entries(config)

            assert result == []
            mock_warning.assert_called_once()
            assert "contains invalid JSON" in str(mock_warning.call_args)
    Path(f.name).unlink()


def test_load_failed_entries_valid_json():
    """Test that load_failed_entries works correctly with valid JSON."""
    test_data = [{"resource_tag": "net", "pk": 123, "error": "test error"}]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_data, f)
        f.flush()

        config = {"sync": {"failed_entries": f.name}}

        result = util.load_failed_entries(config)
        assert result == test_data

    Path(f.name).unlink()


def test_load_failed_entries_empty_file():
    """Test that load_failed_entries handles empty files."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("")
        f.flush()

        config = {"sync": {"failed_entries": f.name}}

        result = util.load_failed_entries(config)
        assert result == []

    Path(f.name).unlink()


def test_load_failed_entries_file_not_found():
    """Test that load_failed_entries handles missing files."""
    config = {"sync": {"failed_entries": "/nonexistent/file.json"}}

    result = util.load_failed_entries(config)
    assert result == []
