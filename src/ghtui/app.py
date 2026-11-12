from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, TabbedContent, TabPane

from . import gh
from .screens.auth import AuthPane
from .screens.prs import PRsPane
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
        Binding("r", "refresh", "Refrescar"),
        Binding("slash", "filter", "Filtrar"),
        # contextual
        Binding("c", "clone", "Clonar", show=True),
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
        }[self.active]

    def _set_repo(self, repo: str, switch: bool = True) -> None:
        self.sub_title = repo
        self.query_one(PRsPane).set_repo(repo)
        self.query_one(RunsPane).set_repo(repo)
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

    def action_clone(self) -> None:
        if self.active == "repos":
            self.query_one(ReposPane).clone_selected()

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
        if self.active == "prs":
            self.query_one(PRsPane).merge()

    def action_diff(self) -> None:
        if self.active == "prs":
            self.query_one(PRsPane).diff()

    def action_rerun(self) -> None:
        if self.active == "runs":
            self.query_one(RunsPane).rerun()


def main() -> None:
    GhTui().run()
