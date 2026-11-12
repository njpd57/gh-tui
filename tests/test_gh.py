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


async def test_repo_create_args(monkeypatch):
    seen = []

    async def fake(*a, **k):
        seen.append(a)
        return ""

    monkeypatch.setattr(gh, "run", fake)
    await gh.repo_create("o/r")
    await gh.repo_create("r", "public", "desc", True, "Python", "mit", True)
    assert seen[0] == ("repo", "create", "o/r", "--private")
    assert seen[1] == ("repo", "create", "r", "--public", "--description", "desc", "--add-readme",
                       "--gitignore", "Python", "--license", "mit", "--clone")


async def test_repo_create_validation():
    with pytest.raises(gh.GhError):
        await gh.repo_create("a b")
    with pytest.raises(gh.GhError):
        await gh.repo_create("r", "secret")


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


async def test_new_repo_modal(monkeypatch, tmp_path):
    from ghtui.screens.modals import CreateRepoModal

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    created = []

    async def empty(*a, **k):
        return []

    async def none():
        return None

    async def status():
        return "ok"

    async def create(**kw):
        created.append(kw)
        return ""

    monkeypatch.setattr(gh, "repo_list", empty)
    monkeypatch.setattr(gh, "current_repo", none)
    monkeypatch.setattr(gh, "auth_status", status)
    monkeypatch.setattr(gh, "repo_create", create)
    app = GhTui()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()
        assert isinstance(app.screen, CreateRepoModal)
        await pilot.press("enter")  # nombre vacío: no cierra
        await pilot.pause()
        assert isinstance(app.screen, CreateRepoModal)
        await pilot.press(*"demo", "enter")
        await pilot.pause()
        assert not isinstance(app.screen, CreateRepoModal)
        assert created and created[0]["name"] == "demo" and created[0]["visibility"] == "private"
        # regresión: «ninguno» no debe filtrarse como plantilla de gitignore/licencia
        assert created[0]["gitignore"] == "" and created[0]["license"] == ""


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


async def test_new_commands_args(monkeypatch):
    seen = []

    async def fake(*a, **k):
        seen.append(a)
        return ""

    monkeypatch.setattr(gh, "run", fake)
    await gh.repo_delete("o/r")
    await gh.repo_archive("o/r", False)
    await gh.repo_rename("o/r", "n")
    await gh.pr_create("o/r", "t", "b", "feat", "main", True)
    await gh.pr_ready("o/r", 3, ready=False)
    await gh.run_cancel("o/r", 9)
    await gh.workflow_run("o/r", "5", "dev")
    await gh.release_create("o/r", "v1")
    assert seen == [
        ("repo", "delete", "o/r", "--yes"),
        ("repo", "unarchive", "o/r", "--yes"),
        ("repo", "rename", "n", "-R", "o/r", "--yes"),
        ("pr", "create", "-R", "o/r", "--title", "t", "--body", "b", "--head", "feat", "--base", "main", "--draft"),
        ("pr", "ready", "3", "-R", "o/r", "--undo"),
        ("run", "cancel", "9", "-R", "o/r"),
        ("workflow", "run", "5", "-R", "o/r", "--ref", "dev"),
        ("release", "create", "v1", "-R", "o/r", "--title", "v1", "--generate-notes"),
    ]


async def test_new_commands_validation():
    for coro in (gh.repo_rename("o/r", "a/b"), gh.pr_create("o/r", " "), gh.pr_comment("o/r", 1, ""),
                 gh.pr_request_changes("o/r", 1, ""), gh.release_create("o/r", "v 1"), gh.search("x", "q"),
                 gh.search("repos", " "), gh.repo_set_visibility("o/r", "x")):
        with pytest.raises(gh.GhError):
            await coro


def test_parse_accounts_and_format_search():
    txt = "github.com\n  ✓ Logged in to github.com account alice (keyring)\n  ✓ Logged in to github.com account bob (keyring)"
    assert gh.parse_accounts(txt) == ["alice", "bob"]
    out = gh.format_search("issues", [{"repository": {"nameWithOwner": "o/r"}, "number": 2, "state": "open", "title": "t"}])
    assert out == "o/r#2  [open]  t"
    assert gh.format_search("code", []) == "(sin resultados)"
