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

ALL = 100_000  # gh paginates internally up to --limit

REPO_FIELDS = "name,nameWithOwner,description,isPrivate,isArchived,updatedAt,primaryLanguage,url"


async def repo_list(owner: str = "", limit: int = ALL) -> list[dict]:
    args = ["repo", "list"]
    if owner:
        args.append(owner)
    args += ["--limit", str(limit), "--json", REPO_FIELDS]
    return await run_json(*args)


async def repo_clone(repo: str, dest: str) -> str:
    return await run("repo", "clone", repo, dest)


async def repo_create(
    name: str,
    visibility: str = "private",
    description: str = "",
    readme: bool = False,
    gitignore: str = "",
    license: str = "",
    clone: bool = False,
) -> str:
    if visibility not in ("public", "private", "internal"):
        raise GhError(f"Visibilidad inválida: {visibility}")
    if not name or any(c.isspace() for c in name):
        raise GhError("Nombre de repo inválido")
    args = ["repo", "create", name, f"--{visibility}"]
    if description:
        args += ["--description", description]
    if readme:
        args.append("--add-readme")
    if gitignore:
        args += ["--gitignore", gitignore]
    if license:
        args += ["--license", license]
    if clone:
        args.append("--clone")
    return await run(*args)


async def repo_delete(repo: str) -> str:
    return await run("repo", "delete", repo, "--yes")


async def repo_archive(repo: str, archive: bool = True) -> str:
    return await run("repo", "archive" if archive else "unarchive", repo, "--yes")


async def repo_rename(repo: str, new_name: str) -> str:
    if not new_name or any(c.isspace() or c == "/" for c in new_name):
        raise GhError("Nombre nuevo inválido (sin espacios ni «/»)")
    return await run("repo", "rename", new_name, "-R", repo, "--yes")


async def repo_set_visibility(repo: str, visibility: str) -> str:
    if visibility not in ("public", "private", "internal"):
        raise GhError(f"Visibilidad inválida: {visibility}")
    base = ["repo", "edit", repo, "--visibility", visibility]
    try:
        return await run(*base, "--accept-visibility-change-consequences")
    except GhError as e:
        if "unknown flag" in str(e):  # gh antiguo no conoce el flag
            return await run(*base)
        raise


async def repo_set_description(repo: str, description: str) -> str:
    return await run("repo", "edit", repo, "--description", description)


async def current_repo() -> str | None:
    try:
        data = await run_json("repo", "view", "--json", "nameWithOwner")
        return data.get("nameWithOwner")
    except GhError:
        return None


# ---- pull requests --------------------------------------------------------

PR_FIELDS = "number,title,author,reviewDecision,statusCheckRollup,updatedAt,isDraft,headRefName"


async def pr_list(repo: str, state: str = "open", limit: int = ALL) -> list[dict]:
    return await run_json("pr", "list", "-R", repo, "--state", state, "--limit", str(limit), "--json", PR_FIELDS)


async def pr_view(repo: str, number: int) -> str:
    return await run("pr", "view", str(number), "-R", repo)


async def pr_diff(repo: str, number: int) -> str:
    return await run("pr", "diff", str(number), "-R", repo)


async def pr_approve(repo: str, number: int, body: str = "") -> str:
    args = ["pr", "review", str(number), "-R", repo, "--approve"]
    if body:
        args += ["--body", body]
    return await run(*args)


async def pr_create(
    repo: str, title: str, body: str = "", head: str = "", base: str = "", draft: bool = False
) -> str:
    if not title.strip():
        raise GhError("El título es obligatorio")
    args = ["pr", "create", "-R", repo, "--title", title, "--body", body]
    if head:
        args += ["--head", head]
    if base:
        args += ["--base", base]
    if draft:
        args.append("--draft")
    return await run(*args)


async def pr_request_changes(repo: str, number: int, body: str) -> str:
    if not body.strip():
        raise GhError("Pedir cambios requiere un comentario")
    return await run("pr", "review", str(number), "-R", repo, "--request-changes", "--body", body)


async def pr_comment(repo: str, number: int, body: str) -> str:
    if not body.strip():
        raise GhError("El comentario está vacío")
    return await run("pr", "comment", str(number), "-R", repo, "--body", body)


async def pr_ready(repo: str, number: int, ready: bool = True) -> str:
    args = ["pr", "ready", str(number), "-R", repo]
    if not ready:
        args.append("--undo")
    return await run(*args)


async def pr_merge(repo: str, number: int, method: str = "squash") -> str:
    if method not in ("squash", "merge", "rebase"):
        raise GhError(f"Método de merge inválido: {method}")
    return await run("pr", "merge", str(number), "-R", repo, f"--{method}")


# ---- workflow runs --------------------------------------------------------

RUN_FIELDS = "databaseId,displayTitle,status,conclusion,workflowName,headBranch,createdAt,event"


async def run_list(repo: str, limit: int = ALL) -> list[dict]:
    return await run_json("run", "list", "-R", repo, "--limit", str(limit), "--json", RUN_FIELDS)


async def run_view(repo: str, run_id: int) -> str:
    return await run("run", "view", str(run_id), "-R", repo)


async def run_log(repo: str, run_id: int, failed_only: bool = False) -> str:
    return await run("run", "view", str(run_id), "-R", repo, "--log-failed" if failed_only else "--log")


async def run_rerun(repo: str, run_id: int) -> str:
    return await run("run", "rerun", str(run_id), "-R", repo)


async def run_cancel(repo: str, run_id: int) -> str:
    return await run("run", "cancel", str(run_id), "-R", repo)


async def workflow_list(repo: str) -> list[dict]:
    return await run_json("workflow", "list", "-R", repo, "--json", "id,name,path,state")


async def workflow_run(repo: str, workflow: str, ref: str = "") -> str:
    args = ["workflow", "run", workflow, "-R", repo]
    if ref:
        args += ["--ref", ref]
    return await run(*args)


# ---- releases -------------------------------------------------------------

RELEASE_FIELDS = "tagName,name,isDraft,isPrerelease,isLatest,publishedAt,createdAt"


async def release_list(repo: str, limit: int = ALL) -> list[dict]:
    return await run_json("release", "list", "-R", repo, "--limit", str(limit), "--json", RELEASE_FIELDS)


async def release_view(repo: str, tag: str) -> str:
    return await run("release", "view", tag, "-R", repo)


async def release_create(
    repo: str, tag: str, title: str = "", notes: str = "", draft: bool = False, prerelease: bool = False
) -> str:
    if not tag or any(c.isspace() for c in tag):
        raise GhError("Tag inválido")
    args = ["release", "create", tag, "-R", repo, "--title", title or tag]
    args += ["--notes", notes] if notes else ["--generate-notes"]
    if draft:
        args.append("--draft")
    if prerelease:
        args.append("--prerelease")
    return await run(*args)


async def release_delete(repo: str, tag: str) -> str:
    return await run("release", "delete", tag, "-R", repo, "--yes")


# ---- notifications --------------------------------------------------------

async def notifications() -> list[dict]:
    return await run_json("api", "notifications?per_page=100")


async def notification_read(thread_id: str) -> None:
    await run("api", "-X", "PATCH", f"notifications/threads/{thread_id}")


async def notifications_read_all() -> None:
    await run("api", "-X", "PUT", "notifications")


# ---- search ---------------------------------------------------------------

SEARCH_KINDS = {
    "repos": "fullName,description,stargazersCount,isPrivate",
    "issues": "repository,number,title,state",
    "prs": "repository,number,title,state",
    "code": "repository,path",
}


async def search(kind: str, query: str, limit: int = 50) -> list[dict]:
    if kind not in SEARCH_KINDS:
        raise GhError(f"Tipo de búsqueda inválido: {kind}")
    if not query.strip():
        raise GhError("Consulta vacía")
    return await run_json("search", kind, query, "--limit", str(limit), "--json", SEARCH_KINDS[kind])


def format_search(kind: str, items: list[dict]) -> str:
    lines = []
    for i in items:
        repo = (i.get("repository") or {}).get("nameWithOwner", "")
        if kind == "repos":
            lock = " 🔒" if i.get("isPrivate") else ""
            lines.append(f"{i['fullName']}{lock}  ★{i.get('stargazersCount', 0)}  {i.get('description') or ''}")
        elif kind == "code":
            lines.append(f"{repo}  {i.get('path', '')}")
        else:
            lines.append(f"{repo}#{i['number']}  [{i.get('state', '')}]  {i.get('title', '')}")
    return "\n".join(lines) or "(sin resultados)"


# ---- accounts -------------------------------------------------------------

def parse_accounts(status_text: str) -> list[str]:
    import re

    seen: list[str] = []
    for m in re.finditer(r"account (\S+)", status_text):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


async def auth_switch(user: str, host: str = "github.com") -> None:
    await run("auth", "switch", "--user", user, "--hostname", host)


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
