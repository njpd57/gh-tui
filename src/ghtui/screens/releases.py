from __future__ import annotations

from .. import gh
from .base import TablePane
from .modals import ConfirmModal, CreateReleaseModal, TextViewer


class ReleasesPane(TablePane):
    COLUMNS = ("Tag", "Título", "Estado", "Publicada")
    repo: str | None = None

    def cache_key(self) -> str | None:
        return f"releases-{self.repo}" if self.repo else None

    async def fetch(self) -> list[dict]:
        if not self.repo:
            self.set_status("Selecciona un repo en la pestaña Repos (Enter)")
            return []
        return await gh.release_list(self.repo)

    def row(self, r: dict) -> tuple:
        flags = [f for f, on in (("latest", r.get("isLatest")), ("draft", r.get("isDraft")),
                                 ("pre", r.get("isPrerelease"))) if on]
        return (
            r["tagName"],
            (r.get("name") or "")[:60],
            ",".join(flags) or "-",
            (r.get("publishedAt") or r.get("createdAt") or "")[:10],
        )

    def set_repo(self, repo: str) -> None:
        self.repo = repo
        self.reload()

    def view(self) -> None:
        r = self.selected()
        if r and self.repo:
            self.run_worker(self._show(self.repo, r["tagName"]))

    async def _show(self, repo: str, tag: str) -> None:
        try:
            text = await gh.release_view(repo, tag)
        except gh.GhError as e:
            self.app.notify(str(e), severity="error")
            return
        self.app.push_screen(TextViewer(f"{repo} {tag}", text))

    def create_release(self) -> None:
        if not self.repo:
            self.app.notify("Selecciona un repo primero", severity="warning")
            return
        repo = self.repo

        def done(data: dict | None) -> None:
            if data:
                self.run_worker(self._act(gh.release_create(repo, **data), f"Release {data['tag']} creada", reload=True))

        self.app.push_screen(CreateReleaseModal(repo), done)

    def delete_release(self) -> None:
        r = self.selected()
        if not r or not self.repo:
            return
        repo, tag = self.repo, r["tagName"]

        def done(ok: bool | None) -> None:
            if ok:
                self.run_worker(self._act(gh.release_delete(repo, tag), f"Release {tag} borrada", reload=True))

        self.app.push_screen(ConfirmModal(f"¿Borrar la release {tag} de {repo}?"), done)
