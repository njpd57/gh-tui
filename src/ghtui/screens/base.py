from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Input, Label

from .. import gh


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

    def reload(self) -> None:
        self.run_worker(self._load(), exclusive=True, group=f"load-{self.id}")

    async def _load(self) -> None:
        self.set_status("Cargando…")
        try:
            self.items = await self.fetch()
        except gh.GhError as e:
            self.items = []
            self.set_status(f"Error: {e}".splitlines()[0])
            self.app.notify(str(e), severity="error", timeout=8)
        else:
            self.set_status(f"{len(self.items)} elementos")
        self.render_rows()

    def render_rows(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        needle = self.filter_text.lower()
        self._shown = [i for i in self.items if needle in self.haystack(i).lower()]
        for n, item in enumerate(self._shown):
            table.add_row(*self.row(item), key=str(n))

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

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.query_one(DataTable).focus()
