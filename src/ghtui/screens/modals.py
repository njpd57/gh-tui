from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList, RichLog


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

    def __init__(self, prompt: str, value: str = "") -> None:
        super().__init__()
        self.prompt, self.value = prompt, value

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.prompt)
            yield Input(value=self.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)


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
