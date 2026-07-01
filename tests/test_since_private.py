"""
Tests for the since_private watermark (#92).

Private objects (poc, ixlan) must sync incrementally from a watermark that
records the last --fetch-private pull — not from the public last_change.

The update_all flow is exercised with the fetcher/backend save-path mocked, so
these assert the since-selection logic deterministically without HTTP or data
fixtures.
"""

import helper

from peeringdb.client import Client


class FakeRes:
    """Minimal stand-in for a private resource class (only .tag is used)."""

    tag = "ixlan"


class FakeNet:
    """Minimal stand-in for a non-private resource."""

    tag = "net"


def _updater(cache_dir):
    client = Client(helper.CONFIG)
    up = client.updater
    up.fetcher.cache_dir = str(cache_dir)
    return up


def _mock_io(up, monkeypatch, last_change):
    """Stub out everything except the since-selection logic; capture load()."""
    calls = {}

    def fake_load(tag, since, fetch_private=False):
        calls["tag"] = tag
        calls["since"] = since
        calls["fetch_private"] = fetch_private

    monkeypatch.setattr(up.fetcher, "load", fake_load)
    monkeypatch.setattr(up.fetcher, "entries", lambda tag: [])
    monkeypatch.setattr(up.backend, "get_concrete", lambda r: object)
    monkeypatch.setattr(up.backend, "last_change", lambda c: last_change)
    monkeypatch.setattr(up, "_handle_initial_sync", lambda e, r: None)
    # #135 made _handle_incremental_sync return per-run counts that update_all
    # feeds into its "Processed" log line; the watermark logic under test is
    # unaffected, so a zeroed dict keeps the flow honest.
    monkeypatch.setattr(
        up,
        "_handle_incremental_sync",
        lambda e, r: {"created": 0, "updated": 0, "unchanged": 0},
    )
    return calls


def test_since_private_roundtrip(tmp_path):
    up = _updater(tmp_path)
    assert up._get_since_private("ixlan") is None
    up._set_since_private("ixlan", 12345)
    assert up._get_since_private("ixlan") == 12345
    # falsy timestamps are not recorded
    up._set_since_private("poc", None)
    assert up._get_since_private("poc") is None
    up._set_since_private("poc", 0)
    assert up._get_since_private("poc") is None


def test_since_private_namespaced_by_url(tmp_path):
    """A watermark set against one API URL must not leak to another URL that
    happens to share the same cache dir."""
    up = _updater(tmp_path)
    up._set_since_private("ixlan", 12345)
    assert up._get_since_private("ixlan") == 12345

    # same cache dir, different source instance -> no watermark
    up.fetcher.url = "https://other.example.com/api"
    assert up._get_since_private("ixlan") is None


def test_first_private_sync_full_fetch_then_seeds_watermark(tmp_path, monkeypatch):
    up = _updater(tmp_path)
    calls = _mock_io(up, monkeypatch, last_change=200)

    up.update_all([FakeRes()], fetch_private=True)

    # no watermark yet -> full fetch (since=None), as private data
    assert calls["since"] is None
    assert calls["fetch_private"] is True
    # watermark seeded from last_change after the save
    assert up._get_since_private("ixlan") == 200


def test_second_private_sync_resumes_from_watermark(tmp_path, monkeypatch):
    up = _updater(tmp_path)
    up._set_since_private("ixlan", 200)
    calls = _mock_io(up, monkeypatch, last_change=200)

    up.update_all([FakeRes()], fetch_private=True)

    # incremental from the watermark (windowed by the #135 lookback), not a
    # full re-fetch
    assert calls["since"] == up._since_param(200)


def test_interleaved_public_sync_does_not_move_private_watermark(tmp_path, monkeypatch):
    """The whole point of a private watermark: a non-private sync advances
    last_change, but the next private sync must resume from the last private
    pull, not last_change."""
    up = _updater(tmp_path)
    up._set_since_private("ixlan", 200)
    # a public sync has since bumped last_change to 500
    calls = _mock_io(up, monkeypatch, last_change=500)

    up.update_all([FakeRes()], fetch_private=True)

    # fetch resumes from the private watermark (200), NOT last_change (500),
    # windowed by the #135 lookback
    assert calls["since"] == up._since_param(200)
    # and after the pull, the watermark advances to the new last_change
    assert up._get_since_private("ixlan") == 500


def test_empty_db_full_fetches_and_ignores_stale_watermark(tmp_path, monkeypatch):
    """After a DB wipe, last_change is None -> always full fetch, so a stale
    watermark can never truncate a sync into an empty table."""
    up = _updater(tmp_path)
    up._set_since_private("ixlan", 999)
    calls = _mock_io(up, monkeypatch, last_change=None)

    up.update_all([FakeRes()], fetch_private=True)

    assert calls["since"] is None  # full fetch despite the stale 999 watermark


def test_explicit_since_overrides_private_watermark(tmp_path, monkeypatch):
    """An explicit --since N is a manual override and wins over the watermark."""
    up = _updater(tmp_path)
    up._set_since_private("ixlan", 200)
    calls = _mock_io(up, monkeypatch, last_change=999)

    up.update_all([FakeRes()], since=50, fetch_private=True)

    # uses the explicit since (50), not the watermark (200) or last_change
    # (999), windowed by the #135 lookback
    assert calls["since"] == up._since_param(50)
    # explicit --since must NOT advance the watermark: it may skip private rows
    # in (watermark, N], so a later default sync must still resume from 200.
    assert up._get_since_private("ixlan") == 200


def test_first_private_over_populated_db_saves_incrementally(tmp_path, monkeypatch):
    """A first private fetch (watermark unset) over an already-populated DB must
    full-FETCH but incremental-SAVE — save mode is keyed off DB state, so it
    never hits the bulk_create UNIQUE collision."""
    up = _updater(tmp_path)
    seen = {}

    monkeypatch.setattr(
        up.fetcher,
        "load",
        lambda tag, since, fetch_private=False: seen.__setitem__("since", since),
    )
    monkeypatch.setattr(up.fetcher, "entries", lambda tag: [])
    monkeypatch.setattr(up.backend, "get_concrete", lambda r: object)
    monkeypatch.setattr(up.backend, "last_change", lambda c: 500)  # DB populated
    monkeypatch.setattr(
        up, "_handle_initial_sync", lambda e, r: seen.__setitem__("mode", "initial")
    )

    def fake_incremental(e, r):
        seen["mode"] = "incremental"
        # #135: update_all consumes the returned counts for its log line
        return {"created": 0, "updated": 0, "unchanged": 0}

    monkeypatch.setattr(up, "_handle_incremental_sync", fake_incremental)

    up.update_all([FakeRes()], fetch_private=True)

    assert seen["since"] is None  # full fetch (no watermark yet)
    assert seen["mode"] == "incremental"  # incremental save (DB populated)


def test_non_private_does_not_touch_watermark(tmp_path, monkeypatch):
    """Non-private resources sync from last_change and never read/write the
    private watermark, even under --fetch-private."""
    up = _updater(tmp_path)
    calls = _mock_io(up, monkeypatch, last_change=500)

    up.update_all([FakeNet()], fetch_private=True)

    # last_change (500) windowed by the #135 lookback, not a watermark
    assert calls["since"] == up._since_param(500)
    assert up._get_since_private("net") is None  # nothing recorded
