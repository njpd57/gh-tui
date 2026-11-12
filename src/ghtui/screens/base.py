from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Input, Label

from .. import cache, gh


class TablePane(Vertical):
    """A filterable DataTable with async loading. Subclasses set COLUMNS and implement fetch/row."""

    COLUMNS: tuple[str, ...] = ()
    DEFAULT_CSS = """
    TablePane .status { height: 1; color: $text-muted; padding: 0 1; }
    TablePane Input { display: none; }
    TablePane Input.-show { display: block; }
    TablePane DataTable { height: 1fr; }
    """

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self.items: list[dict] = []
        self.filter_text = ""

    def compose(self) -> ComposeResult:
        yield Label("", classes="status")
        yield Input(placeholder="filtrar…", id="filter")
        yield DataTable(cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(*self.COLUMNS)

    # -- to implement
    async def fetch(self) -> list[dict]:
        raise NotImplementedError

    def row(self, item: dict) -> tuple:
        raise NotImplementedError

    def haystack(self, item: dict) -> str:
        return " ".join(str(v) for v in self.row(item))

    # -- machinery
    def set_status(self, text: str) -> None:
        self.query_one(".status", Label).update(text)

    def cache_key(self) -> str | None:
        return None

    def reload(self, force: bool = False) -> None:
        self.run_worker(self._load(force), exclusive=True, group=f"load-{self.id}")

    def _count_text(self) -> str:
        total, shown = len(self.items), len(getattr(self, "_shown", self.items))
        return f"{shown} de {total} elementos" if shown != total else f"{total} elementos"

    async def _load(self, force: bool = False) -> None:
        key = self.cache_key()
        cached = cache.get(key) if key else None
        if cached:
            items, ts = cached
            self.items = items
            self.render_rows()
            age = cache.age_text(ts)
            if not force and cache.is_fresh(ts):
                self.set_status(f"{self._count_text()} (caché hace {age})")
                return
            self.set_status(f"{self._count_text()} (caché hace {age}) · actualizando…")
        else:
            self.set_status("Cargando…")
        try:
            fetched = await self.fetch()
        except gh.GhError as e:
            msg = (str(e).splitlines() or ["error"])[0]
            if cached:
                self.set_status(f"{self._count_text()} (caché; error al actualizar: {msg})")
            else:
                self.items = []
                self.render_rows()
                self.set_status(f"Error: {msg}")
            self.app.notify(str(e), severity="error", timeout=8)
            return
        if key:
            cache.put(key, fetched)
        changed = fetched != self.items
        self.items = fetched
        if changed or not cached:
            self.render_rows()
        self.set_status(self._count_text())

    def render_rows(self) -> None:
        table = self.query_one(DataTable)
        prev = table.cursor_row
        table.clear()
        needle = self.filter_text.lower()
        self._shown = [i for i in self.items if needle in self.haystack(i).lower()]
        for n, item in enumerate(self._shown):
            table.add_row(*self.row(item), key=str(n))
        if self._shown and prev:
            table.move_cursor(row=min(prev, len(self._shown) - 1))

    def selected(self) -> dict | None:
        table = self.query_one(DataTable)
        if not table.row_count:
            return None
        try:
            key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
            return self._shown[int(key)]
        except Exception:
            return None

    def start_filter(self) -> None:
        inp = self.query_one("#filter", Input)
        inp.add_class("-show")
        inp.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        self.filter_text = event.value
        self.render_rows()
        self.set_status(self._count_text())

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.query_one(DataTable).focus()
