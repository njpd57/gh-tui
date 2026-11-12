from __future__ import annotations

from .. import gh
from .base import TablePane


class NotifsPane(TablePane):
    COLUMNS = ("", "Repo", "Tipo", "Título", "Motivo", "Actualizada")
    loaded = False

    def cache_key(self) -> str | None:
        return "notifs"

    async def fetch(self) -> list[dict]:
        return await gh.notifications()

    def row(self, n: dict) -> tuple:
        subj = n.get("subject") or {}
        return (
            "●" if n.get("unread") else " ",
            (n.get("repository") or {}).get("full_name", ""),
            subj.get("type", ""),
            (subj.get("title") or "")[:70],
            n.get("reason", ""),
            (n.get("updated_at") or "")[:16].replace("T", " "),
        )

    def ensure_loaded(self) -> None:
        """Carga perezosa: solo la primera vez que se abre la pestaña."""
        if not self.loaded:
            self.loaded = True
            self.reload()

    def mark_read(self) -> None:
        n = self.selected()
        if n:
            self.run_worker(self._act(gh.notification_read(n["id"]), "Marcada como leída", reload=True))

    def mark_all_read(self) -> None:
        self.run_worker(self._act(gh.notifications_read_all(), "Todas marcadas como leídas", reload=True))
