from __future__ import annotations

import os
from pathlib import Path

from .. import gh
from .base import TablePane
from .modals import InputModal


class ReposPane(TablePane):
    COLUMNS = ("Repo", "Vis.", "Lenguaje", "Actualizado", "Descripción")

    def cache_key(self) -> str | None:
        return "repos"

    async def fetch(self) -> list[dict]:
        return await gh.repo_list()

    def row(self, r: dict) -> tuple:
        lang = (r.get("primaryLanguage") or {}).get("name", "")
        return (
            r["nameWithOwner"],
            "🔒" if r.get("isPrivate") else "público",
            lang,
            (r.get("updatedAt") or "")[:10],
            (r.get("description") or "")[:60],
        )

    def clone_selected(self) -> None:
        r = self.selected()
        if not r:
            return
        default = str(Path(os.environ.get("GHTUI_CLONE_DIR", Path.home() / "Proyects")) / r["name"])

        def done(dest: str | None) -> None:
            if dest:
                self.run_worker(self._clone(r["nameWithOwner"], os.path.expanduser(dest)))

        self.app.push_screen(InputModal(f"Clonar {r['nameWithOwner']} en:", default), done)

    async def _clone(self, repo: str, dest: str) -> None:
        self.set_status(f"Clonando {repo}…")
        try:
            await gh.repo_clone(repo, dest)
            self.app.notify(f"Clonado en {dest}")
        except gh.GhError as e:
            self.app.notify(str(e), severity="error", timeout=10)
        self.set_status(self._count_text())

    def open_browser(self) -> None:
        r = self.selected()
        if r:
            self.run_worker(gh.run("repo", "view", r["nameWithOwner"], "--web"))
