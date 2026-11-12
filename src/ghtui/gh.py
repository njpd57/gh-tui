"""Single access layer to the `gh` binary."""
from __future__ import annotations

import asyncio
import json
import shutil
from typing import Any


class GhError(Exception):
    pass


async def run(*args: str, input_text: str | None = None) -> str:
    if shutil.which("gh") is None:
        raise GhError("No se encontró el binario `gh` en el PATH")
    proc = await asyncio.create_subprocess_exec(
        "gh",
        *args,
        stdin=asyncio.subprocess.PIPE if input_text is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=_env(),
    )
    out, err = await proc.communicate(input_text.encode() if input_text is not None else None)
    if proc.returncode != 0:
        raise GhError((err.decode() or out.decode()).strip() or f"gh falló ({proc.returncode})")
    return out.decode()


def _env() -> dict[str, str]:
    import os

    env = dict(os.environ)
    env["GH_PROMPT_DISABLED"] = "1"
    env["NO_COLOR"] = "1"
    return env


async def run_json(*args: str) -> Any:
    out = await run(*args)
    try:
        return json.loads(out) if out.strip() else []
    except json.JSONDecodeError as e:
        raise GhError(f"Salida JSON inválida de gh: {e}") from e


# ---- auth -----------------------------------------------------------------

async def auth_status() -> str:
    # gh writes status to stderr/stdout depending on version; GhError carries it when logged out
    try:
        return await run("auth", "status")
    except GhError as e:
        return str(e)


async def auth_logout(host: str = "github.com") -> None:
    await run("auth", "logout", "--hostname", host)


# ---- repos ----------------------------------------------------------------

REPO_FIELDS = "name,nameWithOwner,description,isPrivate,updatedAt,primaryLanguage,url"


async def repo_list(owner: str = "", limit: int = 100) -> list[dict]:
    args = ["repo", "list"]
    if owner:
        args.append(owner)
    args += ["--limit", str(limit), "--json", REPO_FIELDS]
    return await run_json(*args)


async def repo_clone(repo: str, dest: str) -> str:
    return await run("repo", "clone", repo, dest)


async def current_repo() -> str | None:
    try:
        data = await run_json("repo", "view", "--json", "nameWithOwner")
        return data.get("nameWithOwner")
    except GhError:
        return None


# ---- pull requests --------------------------------------------------------

PR_FIELDS = "number,title,author,reviewDecision,statusCheckRollup,updatedAt,isDraft,headRefName"


async def pr_list(repo: str, state: str = "open") -> list[dict]:
    return await run_json("pr", "list", "-R", repo, "--state", state, "--limit", "50", "--json", PR_FIELDS)


async def pr_view(repo: str, number: int) -> str:
    return await run("pr", "view", str(number), "-R", repo)


async def pr_diff(repo: str, number: int) -> str:
    return await run("pr", "diff", str(number), "-R", repo)


async def pr_approve(repo: str, number: int, body: str = "") -> str:
    args = ["pr", "review", str(number), "-R", repo, "--approve"]
    if body:
        args += ["--body", body]
    return await run(*args)


async def pr_merge(repo: str, number: int, method: str = "squash") -> str:
    if method not in ("squash", "merge", "rebase"):
        raise GhError(f"Método de merge inválido: {method}")
    return await run("pr", "merge", str(number), "-R", repo, f"--{method}")


# ---- workflow runs --------------------------------------------------------

RUN_FIELDS = "databaseId,displayTitle,status,conclusion,workflowName,headBranch,createdAt,event"


async def run_list(repo: str) -> list[dict]:
    return await run_json("run", "list", "-R", repo, "--limit", "30", "--json", RUN_FIELDS)


async def run_view(repo: str, run_id: int) -> str:
    return await run("run", "view", str(run_id), "-R", repo)


async def run_log(repo: str, run_id: int, failed_only: bool = False) -> str:
    return await run("run", "view", str(run_id), "-R", repo, "--log-failed" if failed_only else "--log")


async def run_rerun(repo: str, run_id: int) -> str:
    return await run("run", "rerun", str(run_id), "-R", repo)


# ---- helpers --------------------------------------------------------------

def check_state(rollup: list[dict] | None) -> str:
    """Collapse a statusCheckRollup into one symbol."""
    if not rollup:
        return "·"
    states = [(c.get("conclusion") or c.get("state") or c.get("status") or "").upper() for c in rollup]
    if any(s in ("FAILURE", "ERROR", "TIMED_OUT", "CANCELLED") for s in states):
        return "✗"
    if any(s in ("", "PENDING", "IN_PROGRESS", "QUEUED", "EXPECTED") for s in states):
        return "●"
    return "✓"


def run_symbol(status: str, conclusion: str) -> str:
    if status != "completed":
        return "●"
    return {"success": "✓", "failure": "✗", "cancelled": "⊘", "skipped": "-"}.get(conclusion, "?")
