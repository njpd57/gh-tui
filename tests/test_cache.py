import os
import time

from ghtui import cache


def test_put_get_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert cache.get("prs-o/r") is None
    cache.put("prs-o/r", [{"a": 1}])
    items, ts = cache.get("prs-o/r")
    assert items == [{"a": 1}] and cache.is_fresh(ts)
    assert not list(tmp_path.rglob("*.tmp"))


def test_ttl_and_corrupt(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.setenv("GHTUI_CACHE_TTL", "10")
    assert not cache.is_fresh(time.time() - 60)
    cache.put("repos", [])
    (tmp_path / "ghtui" / "repos.json").write_text("{nope")
    assert cache.get("repos") is None
    cache.clear()


def test_age_text():
    assert cache.age_text(time.time() - 120) == "2m"
