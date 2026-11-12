from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, TabbedContent, TabPane

from . import gh
from .screens.auth import AuthPane
from .screens.modals import ChoiceModal, InputModal, TextViewer
from .screens.notifs import NotifsPane
from .screens.prs import PRsPane
from .screens.releases import ReleasesPane
from .screens.repos import ReposPane
from .screens.runs import RunsPane


class GhTui(App):
    TITLE = "gh-tui"
    BINDINGS = [
        Binding("q", "quit", "Salir"),
        Binding("1", "tab('auth')", "Cuenta"),
        Binding("2", "tab('repos')", "Repos"),
        Binding("3", "tab('prs')", "PRs"),
        Binding("4", "tab('runs')", "Pipelines"),
        Binding("5", "tab('releases')", "Releases"),
        Binding("6", "tab('notifs')", "Notifs"),
        Binding("r", "refresh", "Refrescar"),
        Binding("slash", "filter", "Filtrar"),
        # contextual
        Binding("c", "clone", "Clonar", show=True),
        Binding("n", "new", "Nuevo"),
        Binding("S", "search", "Buscar"),
        Binding("s", "switch_account", "Cambiar cuenta"),
        Binding("x", "cancel_or_changes", "Cancelar/Pedir cambios"),
        Binding("t", "toggle_draft", "Draft/Ready"),
        Binding("C", "comment", "Comentar"),
        Binding("w", "workflow", "Lanzar workflow"),
        Binding("D", "delete", "Borrar"),
        Binding("A", "archive", "Archivar"),
        Binding("N", "rename", "Renombrar"),
        Binding("v", "visibility", "Visibilidad"),
        Binding("E", "edit_desc", "Editar descr."),
        Binding("M", "mark_all", "Marcar todas"),
        Binding("o", "open_or_logout", "Abrir/Logout"),
        Binding("l", "login_or_logs", "Login/Logs"),
        Binding("a", "approve", "Aprobar"),
        Binding("m", "merge", "Merge"),
        Binding("d", "diff", "Diff"),
        Binding("f", "failed_logs", "Logs fallidos"),
        Binding("R", "rerun", "Rerun"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="repos"):
            with TabPane("1 Cuenta", id="auth"):
                yield AuthPane()
            with TabPane("2 Repos", id="repos"):
                yield ReposPane(id="repos-pane")
            with TabPane("3 PRs", id="prs"):
                yield PRsPane(id="prs-pane")
            with TabPane("4 Pipelines", id="runs"):
                yield RunsPane(id="runs-pane")
            with TabPane("5 Releases", id="releases"):
                yield ReleasesPane(id="releases-pane")
            with TabPane("6 Notifs", id="notifs"):
                yield NotifsPane(id="notifs-pane")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(AuthPane).reload()
        self.query_one(ReposPane).reload()
        self.run_worker(self._default_repo())

    async def _default_repo(self) -> None:
        repo = await gh.current_repo()
        if repo:
            self._set_repo(repo, switch=False)

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if self.active == "notifs":
            self.query_one(NotifsPane).ensure_loaded()
        self.call_after_refresh(self._focus_table)

    def _focus_table(self) -> None:
        try:
            self.query_one(f"#{self.active}-pane DataTable", DataTable).focus()
        except Exception:
            pass

    # -- helpers
    @property
    def active(self) -> str:
        return self.query_one(TabbedContent).active

    def _pane(self):
        return {
            "auth": AuthPane,
            "repos": ReposPane,
            "prs": PRsPane,
            "runs": RunsPane,
            "releases": ReleasesPane,
            "notifs": NotifsPane,
        }[self.active]

    def _set_repo(self, repo: str, switch: bool = True) -> None:
        self.sub_title = repo
        self.query_one(PRsPane).set_repo(repo)
        self.query_one(RunsPane).set_repo(repo)
        self.query_one(ReleasesPane).set_repo(repo)
        if switch:
            self.query_one(TabbedContent).active = "prs"

    # -- actions
    def action_tab(self, name: str) -> None:
        self.query_one(TabbedContent).active = name

    def action_refresh(self) -> None:
        self.query_one(self._pane()).reload(force=True)

    def action_filter(self) -> None:
        if self.active != "auth":
            self.query_one(self._pane()).start_filter()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.action_enter()

    def action_enter(self) -> None:
        if self.active == "repos":
            r = self.query_one(ReposPane).selected()
            if r:
                self._set_repo(r["nameWithOwner"])
        elif self.active == "prs":
            self.query_one(PRsPane).view()
        elif self.active == "runs":
            self.query_one(RunsPane).view()
        elif self.active == "releases":
            self.query_one(ReleasesPane).view()
        elif self.active == "notifs":
            self.query_one(NotifsPane).mark_read()

    def action_clone(self) -> None:
        if self.active == "repos":
            self.query_one(ReposPane).clone_selected()

    def _dispatch(self, **by_tab: str) -> None:
        """Llama al método de la pestaña activa que corresponda a la tecla (si lo hay)."""
        name = by_tab.get(self.active)
        if name:
            getattr(self.query_one(self._pane()), name)()

    def reload_all(self) -> None:
        """Tras cambiar de cuenta: vuelve a cargar todo con la caché ya limpia."""
        for pane in (ReposPane, PRsPane, RunsPane, ReleasesPane):
            self.query_one(pane).reload(force=True)
        self.query_one(NotifsPane).loaded = False

    def action_new(self) -> None:
        self._dispatch(repos="create_repo", prs="create_pr", releases="create_release")

    def action_switch_account(self) -> None:
        self._dispatch(auth="switch")

    def action_cancel_or_changes(self) -> None:
        self._dispatch(prs="request_changes", runs="cancel")

    def action_toggle_draft(self) -> None:
        self._dispatch(prs="toggle_draft")

    def action_comment(self) -> None:
        self._dispatch(prs="comment")

    def action_workflow(self) -> None:
        self._dispatch(runs="dispatch_workflow")

    def action_delete(self) -> None:
        self._dispatch(repos="delete_repo", releases="delete_release")

    def action_archive(self) -> None:
        self._dispatch(repos="toggle_archive")

    def action_rename(self) -> None:
        self._dispatch(repos="rename")

    def action_visibility(self) -> None:
        self._dispatch(repos="change_visibility")

    def action_edit_desc(self) -> None:
        self._dispatch(repos="edit_description")

    def action_mark_all(self) -> None:
        self._dispatch(notifs="mark_all_read")

    def action_search(self) -> None:
        kinds = ["repos", "issues", "prs", "code"]

        def kind_chosen(kind: str | None) -> None:
            if not kind:
                return

            def query_done(q: str | None) -> None:
                if q:
                    self.run_worker(self._search(kind, q))

            self.push_screen(InputModal(f"Buscar en {kind}:"), query_done)

        self.push_screen(ChoiceModal("Buscar en GitHub", kinds), kind_chosen)

    async def _search(self, kind: str, query: str) -> None:
        self.notify(f"Buscando «{query}»…", timeout=2)
        try:
            items = await gh.search(kind, query)
        except gh.GhError as e:
            self.notify(str(e), severity="error", timeout=10)
            return
        self.push_screen(TextViewer(f"{kind}: {query} ({len(items)})", gh.format_search(kind, items)))

    def action_open_or_logout(self) -> None:
        if self.active == "repos":
            self.query_one(ReposPane).open_browser()
        elif self.active == "auth":
            self.query_one(AuthPane).logout()

    def action_login_or_logs(self) -> None:
        if self.active == "auth":
            self.query_one(AuthPane).login()
        elif self.active == "runs":
            self.query_one(RunsPane).logs()

    def action_failed_logs(self) -> None:
        if self.active == "runs":
            self.query_one(RunsPane).logs(failed_only=True)

    def action_approve(self) -> None:
        if self.active == "prs":
            self.query_one(PRsPane).approve()

    def action_merge(self) -> None:
        self._dispatch(prs="merge", notifs="mark_read")

    def action_diff(self) -> None:
        if self.active == "prs":
            self.query_one(PRsPane).diff()

    def action_rerun(self) -> None:
        if self.active == "runs":
            self.query_one(RunsPane).rerun()


def main() -> None:
    GhTui().run()
