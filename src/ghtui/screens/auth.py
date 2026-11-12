from __future__ import annotations

import subprocess

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, Static

from .. import gh
from .modals import ConfirmModal


class AuthPane(Vertical):
    DEFAULT_CSS = "AuthPane { padding: 1 2; } AuthPane #auth-text { margin-top: 1; }"

    def compose(self) -> ComposeResult:
        yield Label("Cuenta de GitHub  —  [l] login · [o] logout · [r] refrescar", markup=False)
        yield Static("", id="auth-text", markup=False)

    def reload(self, force: bool = False) -> None:
        self.run_worker(self._load(), exclusive=True, group="auth")

    async def _load(self) -> None:
        self.query_one("#auth-text", Static).update("Cargando…")
        self.query_one("#auth-text", Static).update(await gh.auth_status())

    def login(self) -> None:
        with self.app.suspend():
            subprocess.run(["gh", "auth", "login", "--web"])
        self.reload()

    def logout(self) -> None:
        def done(ok: bool | None) -> None:
            if ok:
                self.run_worker(self._logout())

        self.app.push_screen(ConfirmModal("¿Cerrar sesión en github.com?"), done)

    async def _logout(self) -> None:
        try:
            await gh.auth_logout()
        except gh.GhError as e:
            self.app.notify(str(e), severity="error")
        self.reload()
