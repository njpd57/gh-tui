from __future__ import annotations

import os
from pathlib import Path

from .. import gh
from .base import TablePane
from .modals import ChoiceModal, ConfirmModal, CreateRepoModal, InputModal


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
            ("🔒" if r.get("isPrivate") else "público") + (" 📦" if r.get("isArchived") else ""),
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

    def create_repo(self) -> None:
        def done(data: dict | None) -> None:
            if data:
                self.run_worker(self._act(gh.repo_create(**data), f"Repo {data['name']} creado", reload=True))

        self.app.push_screen(CreateRepoModal(), done)

    def delete_repo(self) -> None:
        r = self.selected()
        if not r:
            return
        name = r["nameWithOwner"]

        def typed(text: str | None) -> None:
            if text != name:
                if text is not None:
                    self.app.notify("El nombre no coincide; no se borró nada", severity="warning")
                return
            self.run_worker(self._act(gh.repo_delete(name), f"Repo {name} borrado", reload=True))

        def confirmed(ok: bool | None) -> None:
            if ok:
                self.app.push_screen(InputModal(f"Escribe «{name}» para confirmar el borrado:"), typed)

        self.app.push_screen(ConfirmModal(f"¿BORRAR {name}? No se puede deshacer."), confirmed)

    def toggle_archive(self) -> None:
        r = self.selected()
        if not r:
            return
        name, archive = r["nameWithOwner"], not r.get("isArchived")
        verb = "Archivar" if archive else "Desarchivar"

        def done(ok: bool | None) -> None:
            if ok:
                self.run_worker(self._act(
                    gh.repo_archive(name, archive), f"{name} {'archivado' if archive else 'desarchivado'}", reload=True))

        self.app.push_screen(ConfirmModal(f"¿{verb} {name}?"), done)

    def rename(self) -> None:
        r = self.selected()
        if not r:
            return
        name = r["nameWithOwner"]

        def done(new: str | None) -> None:
            if new and new != r["name"]:
                self.run_worker(self._act(gh.repo_rename(name, new), f"{name} renombrado a {new}", reload=True))

        self.app.push_screen(InputModal(f"Nuevo nombre para {name}:", r["name"]), done)

    def change_visibility(self) -> None:
        r = self.selected()
        if not r:
            return
        name = r["nameWithOwner"]

        def chosen(vis: str | None) -> None:
            if not vis:
                return

            def done(ok: bool | None) -> None:
                if ok:
                    self.run_worker(self._act(gh.repo_set_visibility(name, vis), f"{name} ahora es {vis}", reload=True))

            self.app.push_screen(ConfirmModal(f"¿Cambiar {name} a {vis}?"), done)

        self.app.push_screen(ChoiceModal(f"Visibilidad de {name}", ["public", "private", "internal"]), chosen)

    def edit_description(self) -> None:
        r = self.selected()
        if not r:
            return
        name = r["nameWithOwner"]

        def done(text: str | None) -> None:
            if text is not None:
                self.run_worker(self._act(gh.repo_set_description(name, text), "Descripción actualizada", reload=True))

        self.app.push_screen(InputModal(f"Descripción de {name}:", r.get("description") or "", allow_empty=True), done)

    def open_browser(self) -> None:
        r = self.selected()
        if r:
            self.run_worker(gh.run("repo", "view", r["nameWithOwner"], "--web"))
