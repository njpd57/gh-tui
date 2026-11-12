from __future__ import annotations

from .. import gh
from .base import TablePane
from .modals import ChoiceModal, ConfirmModal, TextViewer


class PRsPane(TablePane):
    COLUMNS = ("#", "CI", "Review", "Título", "Autor", "Rama", "Actualizado")
    repo: str | None = None

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
            def done(ok: bool | None) -> None:
                if ok:
                    self.run_worker(self._act(gh.pr_approve(repo, n), f"PR #{n} aprobado"))

            self.app.push_screen(ConfirmModal(f"¿Aprobar {repo}#{n}?"), done)

        self._with_selected(go)

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

    async def _act(self, coro, ok_msg: str, reload: bool = False) -> None:
        try:
            await coro
            self.app.notify(ok_msg)
        except gh.GhError as e:
            self.app.notify(str(e), severity="error", timeout=10)
            return
        if reload:
            self.reload()
