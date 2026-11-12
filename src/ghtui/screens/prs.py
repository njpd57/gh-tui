from __future__ import annotations

import asyncio

from .. import gh
from .base import TablePane
from .modals import ChoiceModal, ConfirmModal, CreatePRModal, InputModal, TextViewer


async def _current_branch() -> str:
    """Rama git del directorio actual ('' si no es un repo o está en HEAD desacoplado)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--abbrev-ref", "HEAD",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        out, _ = await proc.communicate()
    except OSError:
        return ""
    branch = out.decode().strip() if proc.returncode == 0 else ""
    return "" if branch == "HEAD" else branch


class PRsPane(TablePane):
    COLUMNS = ("#", "CI", "Review", "Título", "Autor", "Rama", "Actualizado")
    repo: str | None = None

    def cache_key(self) -> str | None:
        return f"prs-{self.repo}" if self.repo else None

    async def fetch(self) -> list[dict]:
        if not self.repo:
            self.set_status("Selecciona un repo en la pestaña Repos (Enter)")
            return []
        return await gh.pr_list(self.repo)

    def row(self, p: dict) -> tuple:
        title = ("[draft] " if p.get("isDraft") else "") + p["title"]
        return (
            p["number"],
            gh.check_state(p.get("statusCheckRollup")),
            p.get("reviewDecision") or "-",
            title[:70],
            (p.get("author") or {}).get("login", ""),
            p.get("headRefName", ""),
            (p.get("updatedAt") or "")[:10],
        )

    def set_repo(self, repo: str) -> None:
        self.repo = repo
        self.reload()

    def _with_selected(self, fn) -> None:
        p = self.selected()
        if p and self.repo:
            fn(self.repo, p["number"])

    def view(self) -> None:
        self._with_selected(lambda r, n: self.run_worker(self._show(r, n, False)))

    def diff(self) -> None:
        self._with_selected(lambda r, n: self.run_worker(self._show(r, n, True)))

    async def _show(self, repo: str, n: int, diff: bool) -> None:
        try:
            text = await (gh.pr_diff(repo, n) if diff else gh.pr_view(repo, n))
        except gh.GhError as e:
            self.app.notify(str(e), severity="error")
            return
        self.app.push_screen(TextViewer(f"{repo}#{n}", text))

    def approve(self) -> None:
        def go(repo: str, n: int) -> None:
            def body(text: str | None) -> None:
                if text is not None:
                    self.run_worker(self._act(gh.pr_approve(repo, n, text), f"PR #{n} aprobado"))

            def done(ok: bool | None) -> None:
                if ok:
                    self.app.push_screen(
                        InputModal("Comentario de la aprobación (Enter vacío = sin comentario):", allow_empty=True), body)

            self.app.push_screen(ConfirmModal(f"¿Aprobar {repo}#{n}?"), done)

        self._with_selected(go)

    def _ask_and_do(self, prompt: str, fn, ok_msg: str) -> None:
        def go(repo: str, n: int) -> None:
            def done(text: str | None) -> None:
                if text:
                    self.run_worker(self._act(fn(repo, n, text), ok_msg.format(n=n), reload=True))

            self.app.push_screen(InputModal(prompt.format(repo=repo, n=n)), done)

        self._with_selected(go)

    def request_changes(self) -> None:
        self._ask_and_do("Pedir cambios en {repo}#{n} — motivo:", gh.pr_request_changes, "Cambios solicitados en #{n}")

    def comment(self) -> None:
        self._ask_and_do("Comentario para {repo}#{n}:", gh.pr_comment, "Comentario añadido a #{n}")

    def toggle_draft(self) -> None:
        p = self.selected()
        if not p or not self.repo:
            return
        repo, n, is_draft = self.repo, p["number"], bool(p.get("isDraft"))
        msg = f"PR #{n} listo para revisión" if is_draft else f"PR #{n} vuelto a borrador"
        self.run_worker(self._act(gh.pr_ready(repo, n, ready=is_draft), msg, reload=True))

    def create_pr(self) -> None:
        if not self.repo:
            self.app.notify("Selecciona un repo primero", severity="warning")
            return
        self.run_worker(self._create_pr(self.repo))

    async def _create_pr(self, repo: str) -> None:
        branch = await _current_branch()

        def done(data: dict | None) -> None:
            if data:
                self.run_worker(self._act(gh.pr_create(repo, **data), "PR creado", reload=True))

        self.app.push_screen(CreatePRModal(repo, branch), done)

    def merge(self) -> None:
        def go(repo: str, n: int) -> None:
            def chosen(method: str | None) -> None:
                if not method:
                    return

                def done(ok: bool | None) -> None:
                    if ok:
                        self.run_worker(self._act(gh.pr_merge(repo, n, method), f"PR #{n} mergeado ({method})", reload=True))

                self.app.push_screen(ConfirmModal(f"¿Merge ({method}) de {repo}#{n}?"), done)

            self.app.push_screen(ChoiceModal("Método de merge", ["squash", "merge", "rebase"]), chosen)

        self._with_selected(go)
