#!/usr/bin/env python
# -*- coding: utf-8 -*-

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, Input, Button, Label
from textual.screen import ModalScreen
from textual import on

class ImportJsonModal(ModalScreen[str | None]):
    CSS = """
    ImportJsonModal {
        background: $surface;
        border: round $primary;
        width: 80;
        height: auto;
        padding: 1;
    }
    ImportJsonModal > Static {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }
    ImportJsonModal Input {
        width: 100%;
        margin-bottom: 1;
    }
    ImportJsonModal Horizontal {
        height: auto;
        margin-top: 1;
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Importar Streams desde JSON", classes="modal-title")
        yield Label("Ruta del archivo JSON:")
        yield Input(id="file_path_input", placeholder="Ej: /ruta/a/streams.json")
        yield Horizontal(
            Button("📥 Importar", id="import_file", variant="primary"),
            Button("❌ Cancelar", id="cancel")
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "import_file":
            file_path = self.query_one("#file_path_input", Input).value.strip()
            if not file_path:
                self.notify("La ruta del archivo no puede estar vacía", severity="error")
                return
            self.dismiss(file_path)
        elif event.button.id == "cancel":
            self.dismiss(None)