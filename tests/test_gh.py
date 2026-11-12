import json

import pytest

from ghtui import gh
from ghtui.app import GhTui


def test_check_state():
    assert gh.check_state(None) == "·"
    assert gh.check_state([{"conclusion": "SUCCESS"}]) == "✓"
    assert gh.check_state([{"conclusion": "SUCCESS"}, {"conclusion": "FAILURE"}]) == "✗"
    assert gh.check_state([{"status": "IN_PROGRESS", "conclusion": ""}]) == "●"


def test_run_symbol():
    assert gh.run_symbol("completed", "success") == "✓"
    assert gh.run_symbol("in_progress", "") == "●"


async def test_run_json_and_errors(monkeypatch):
    async def fake(*a, **k):
        return json.dumps([{"number": 1}])

    monkeypatch.setattr(gh, "run", fake)
    assert await gh.run_json("x") == [{"number": 1}]


async def test_bad_merge_method():
    with pytest.raises(gh.GhError):
        await gh.pr_merge("o/r", 1, "yolo")


async def test_app_navigation(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    async def repos(*a, **k):
        return [{"name": "r", "nameWithOwner": "o/r", "isPrivate": False, "updatedAt": "2026-01-01T00:00:00Z",
                 "primaryLanguage": None, "description": "d", "url": "u"}]

    async def prs(repo, state="open"):
        return [{"number": 3, "title": "t", "author": {"login": "a"}, "reviewDecision": "", "statusCheckRollup": [],
                 "updatedAt": "2026-01-01T00:00:00Z", "isDraft": False, "headRefName": "b"}]

    async def runs(repo):
        return []

    async def none():
        return None

    async def status():
        return "ok"

    monkeypatch.setattr(gh, "repo_list", repos)
    monkeypatch.setattr(gh, "pr_list", prs)
    monkeypatch.setattr(gh, "run_list", runs)
    monkeypatch.setattr(gh, "current_repo", none)
    monkeypatch.setattr(gh, "auth_status", status)
    app = GhTui()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.active == "prs"
        assert app.sub_title == "o/r"
        await pilot.press("4")
        assert app.active == "runs"


async def test_lists_have_no_small_limit(monkeypatch):
    seen = []

    async def fake(*a):
        seen.append(a)
        return []

    monkeypatch.setattr(gh, "run_json", fake)
    await gh.repo_list()
    await gh.pr_list("o/r")
    await gh.run_list("o/r")
    assert all(str(gh.ALL) in a for a in seen) and gh.ALL >= 10_000
