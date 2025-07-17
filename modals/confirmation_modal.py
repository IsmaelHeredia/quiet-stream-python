#!/usr/bin/env python
# -*- coding: utf-8 -*-

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Horizontal
from textual.widgets import Static, Button

class ConfirmationModal(ModalScreen[bool]):

    CSS = """
    ConfirmationModal {
        background: $surface;
        border: round $primary;
        width: 60;
        height: auto;
        padding: 1;
    }
    ConfirmationModal > Static {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }
    ConfirmationModal Horizontal {
        height: auto;
        margin-top: 1;
        align: center middle;
    }
    ConfirmationModal Button {
        margin-left: 1;
        margin-right: 1;
    }
    """

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(True)
        elif event.button.id == "cancel":
            self.dismiss(False)

    def compose(self) -> ComposeResult:
        yield Static(self.message, classes="modal-title")
        yield Horizontal(
            Button("✅ Sí", id="confirm", variant="error"),
            Button("⛔ No", id="cancel")
        )