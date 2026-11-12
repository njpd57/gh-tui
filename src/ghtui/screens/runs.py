from __future__ import annotations

from .. import gh
from .base import TablePane
from .modals import ConfirmModal, TextViewer


class RunsPane(TablePane):
    COLUMNS = ("ID", "", "Workflow", "Título", "Rama", "Evento", "Creado")
    repo: str | None = None

    def cache_key(self) -> str | None:
        return f"runs-{self.repo}" if self.repo else None

    async def fetch(self) -> list[dict]:
        if not self.repo:
            self.set_status("Selecciona un repo en la pestaña Repos (Enter)")
            return []
        return await gh.run_list(self.repo)

    def row(self, r: dict) -> tuple:
        return (
            r["databaseId"],
            gh.run_symbol(r.get("status", ""), r.get("conclusion", "")),
            r.get("workflowName", ""),
            (r.get("displayTitle") or "")[:60],
            r.get("headBranch", ""),
            r.get("event", ""),
            (r.get("createdAt") or "")[:16].replace("T", " "),
        )

    def set_repo(self, repo: str) -> None:
        self.repo = repo
        self.reload()

    def _sel(self):
        r = self.selected()
        return (self.repo, r["databaseId"]) if r and self.repo else None

    def view(self) -> None:
        s = self._sel()
        if s:
            self.run_worker(self._show(*s, log=False))

    def logs(self, failed_only: bool = False) -> None:
        s = self._sel()
        if s:
            self.run_worker(self._show(*s, log=True, failed_only=failed_only))

    async def _show(self, repo: str, rid: int, log: bool, failed_only: bool = False) -> None:
        self.set_status("Cargando…")
        try:
            text = await (gh.run_log(repo, rid, failed_only) if log else gh.run_view(repo, rid))
        except gh.GhError as e:
            self.app.notify(str(e), severity="error", timeout=8)
            return
        finally:
            self.set_status(self._count_text())
        self.app.push_screen(TextViewer(f"run {rid}", text))

    def rerun(self) -> None:
        s = self._sel()
        if not s:
            return

        def done(ok: bool | None) -> None:
            if ok:
                self.run_worker(self._rerun(*s))

        self.app.push_screen(ConfirmModal(f"¿Relanzar run {s[1]}?"), done)

    async def _rerun(self, repo: str, rid: int) -> None:
        try:
            await gh.run_rerun(repo, rid)
            self.app.notify(f"Run {rid} relanzado")
            self.reload(force=True)
        except gh.GhError as e:
            self.app.notify(str(e), severity="error", timeout=8)
