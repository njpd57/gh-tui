from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, OptionList, RichLog, Select, TextArea


class ConfirmModal(ModalScreen[bool]):
    BINDINGS = [Binding("escape", "dismiss(False)", "Cancelar")]
    DEFAULT_CSS = """
    ConfirmModal { align: center middle; }
    ConfirmModal > Vertical { width: 60; height: auto; border: thick $primary; padding: 1 2; background: $surface; }
    ConfirmModal Horizontal { height: auto; margin-top: 1; }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.message)
            with Horizontal():
                yield Button("Sí", id="yes", variant="primary")
                yield Button("No", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")


class InputModal(ModalScreen[str | None]):
    BINDINGS = [Binding("escape", "dismiss(None)", "Cancelar")]
    DEFAULT_CSS = """
    InputModal { align: center middle; }
    InputModal > Vertical { width: 70; height: auto; border: thick $primary; padding: 1 2; background: $surface; }
    """

    def __init__(self, prompt: str, value: str = "", allow_empty: bool = False) -> None:
        """Con allow_empty, Enter sobre texto vacío devuelve "" (Esc sigue devolviendo None)."""
        super().__init__()
        self.prompt, self.value, self.allow_empty = prompt, value, allow_empty

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.prompt)
            yield Input(value=self.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        self.dismiss(text if (text or self.allow_empty) else None)


class ChoiceModal(ModalScreen[str | None]):
    BINDINGS = [Binding("escape", "dismiss(None)", "Cancelar")]
    DEFAULT_CSS = """
    ChoiceModal { align: center middle; }
    ChoiceModal > Vertical { width: 40; height: auto; border: thick $primary; padding: 1 2; background: $surface; }
    """

    def __init__(self, prompt: str, options: list[str]) -> None:
        super().__init__()
        self.prompt, self.options = prompt, options

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.prompt)
            yield OptionList(*self.options)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(self.options[event.option_index])


class CreateRepoModal(ModalScreen["dict | None"]):
    BINDINGS = [Binding("escape", "dismiss(None)", "Cancelar")]
    DEFAULT_CSS = """
    CreateRepoModal { align: center middle; }
    CreateRepoModal > Vertical { width: 70; height: auto; max-height: 95%; border: thick $primary; padding: 1 2; background: $surface; overflow-y: auto; }
    CreateRepoModal Horizontal { height: auto; margin-top: 1; }
    CreateRepoModal .err { color: $error; height: auto; }
    """

    VISIBILITY = [("Privado", "private"), ("Público", "public"), ("Interno (orgs)", "internal")]
    GITIGNORE = ["Python", "Node", "Go", "Rust", "Java", "C++"]
    LICENSES = [("MIT", "mit"), ("Apache 2.0", "apache-2.0"), ("GPL 3.0", "gpl-3.0"), ("BSD 3", "bsd-3-clause")]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Nuevo repo (usa org/nombre para una organización)")
            yield Input(placeholder="nombre", id="name")
            yield Input(placeholder="descripción (opcional)", id="desc")
            yield Select(self.VISIBILITY, value="private", allow_blank=False, id="vis")
            yield Select([(g, g) for g in self.GITIGNORE],prompt=".gitignore: ninguno", id="gitignore")
            yield Select(self.LICENSES, prompt="Licencia: ninguna", id="license")
            yield Checkbox("Añadir README", id="readme")
            yield Checkbox("Clonar tras crear (en el directorio actual)", id="clone")
            yield Label("", classes="err")
            with Horizontal():
                yield Button("Crear", id="create", variant="primary")
                yield Button("Cancelar", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#name", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self._submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            self._submit()
        else:
            self.dismiss(None)

    def _submit(self) -> None:
        name = self.query_one("#name", Input).value.strip()
        if not name or any(c.isspace() for c in name):
            self.query_one(".err", Label).update("El nombre es obligatorio y no puede tener espacios")
            return

        def sel(id_: str) -> str:
            # «ninguno» es un centinela de Textual (cambia según versión): solo valen str reales
            v = self.query_one(f"#{id_}", Select).value
            return v if isinstance(v, str) else ""

        self.dismiss({
            "name": name,
            "description": self.query_one("#desc", Input).value.strip(),
            "visibility": sel("vis") or "private",
            "gitignore": sel("gitignore"),
            "license": sel("license"),
            "readme": self.query_one("#readme", Checkbox).value,
            "clone": self.query_one("#clone", Checkbox).value,
        })


class CreatePRModal(ModalScreen["dict | None"]):
    BINDINGS = [Binding("escape", "dismiss(None)", "Cancelar")]
    DEFAULT_CSS = """
    CreatePRModal { align: center middle; }
    CreatePRModal > Vertical { width: 80; height: auto; max-height: 95%; border: thick $primary; padding: 1 2; background: $surface; overflow-y: auto; }
    CreatePRModal Horizontal { height: auto; margin-top: 1; }
    CreatePRModal TextArea { height: 8; }
    CreatePRModal .err { color: $error; height: auto; }
    """

    def __init__(self, repo: str, head: str = "") -> None:
        super().__init__()
        self.repo, self.head = repo, head

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"Nuevo PR en {self.repo}")
            yield Input(placeholder="título", id="title")
            yield TextArea(id="body")
            yield Input(value=self.head, placeholder="rama origen (head), p. ej. usuario:rama", id="head")
            yield Input(placeholder="rama destino (base, opcional)", id="base")
            yield Checkbox("Borrador", id="draft")
            yield Label("", classes="err")
            with Horizontal():
                yield Button("Crear", id="create", variant="primary")
                yield Button("Cancelar", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#title", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "create":
            self.dismiss(None)
            return
        title = self.query_one("#title", Input).value.strip()
        head = self.query_one("#head", Input).value.strip()
        if not title or not head:
            self.query_one(".err", Label).update("Título y rama origen son obligatorios")
            return
        self.dismiss({
            "title": title,
            "body": self.query_one("#body", TextArea).text.strip(),
            "head": head,
            "base": self.query_one("#base", Input).value.strip(),
            "draft": self.query_one("#draft", Checkbox).value,
        })


class CreateReleaseModal(ModalScreen["dict | None"]):
    BINDINGS = [Binding("escape", "dismiss(None)", "Cancelar")]
    DEFAULT_CSS = """
    CreateReleaseModal { align: center middle; }
    CreateReleaseModal > Vertical { width: 80; height: auto; max-height: 95%; border: thick $primary; padding: 1 2; background: $surface; overflow-y: auto; }
    CreateReleaseModal Horizontal { height: auto; margin-top: 1; }
    CreateReleaseModal TextArea { height: 8; }
    CreateReleaseModal .err { color: $error; height: auto; }
    """

    def __init__(self, repo: str) -> None:
        super().__init__()
        self.repo = repo

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"Nueva release en {self.repo}  (notas vacías = generadas automáticamente)")
            yield Input(placeholder="tag, p. ej. v1.0.0", id="tag")
            yield Input(placeholder="título (opcional)", id="title")
            yield TextArea(id="notes")
            yield Checkbox("Borrador", id="draft")
            yield Checkbox("Pre-release", id="pre")
            yield Label("", classes="err")
            with Horizontal():
                yield Button("Crear", id="create", variant="primary")
                yield Button("Cancelar", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#tag", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "create":
            self.dismiss(None)
            return
        tag = self.query_one("#tag", Input).value.strip()
        if not tag or any(c.isspace() for c in tag):
            self.query_one(".err", Label).update("El tag es obligatorio y no puede tener espacios")
            return
        self.dismiss({
            "tag": tag,
            "title": self.query_one("#title", Input).value.strip(),
            "notes": self.query_one("#notes", TextArea).text.strip(),
            "draft": self.query_one("#draft", Checkbox).value,
            "prerelease": self.query_one("#pre", Checkbox).value,
        })


class TextViewer(ModalScreen[None]):
    BINDINGS = [Binding("escape,q", "dismiss(None)", "Cerrar")]
    DEFAULT_CSS = """
    TextViewer { align: center middle; }
    TextViewer > Vertical { width: 95%; height: 90%; border: thick $primary; background: $surface; }
    TextViewer Label { padding: 0 1; }
    """

    def __init__(self, title: str, text: str) -> None:
        super().__init__()
        self.title_text, self.text = title, text

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"{self.title_text}  (Esc/q para cerrar)")
            yield RichLog(highlight=False, markup=False, wrap=False)

    def on_mount(self) -> None:
        self.query_one(RichLog).write(self.text or "(vacío)")
