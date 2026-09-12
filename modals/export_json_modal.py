#!/usr/bin/env python
# -*- coding: utf-8 -*-

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, Input, Button, Label
from textual.screen import ModalScreen


class ExportJsonModal(ModalScreen[str | None]):
    CSS = """
    ExportJsonModal {
        background: $surface;
        border: round $primary;
        width: 80;
        height: auto;
        padding: 1;
    }
    ExportJsonModal > Static {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }
    ExportJsonModal Input {
        width: 100%;
        margin-bottom: 1;
    }
    ExportJsonModal Horizontal {
        height: auto;
        margin-top: 1;
        align: center middle;
    }
    ExportJsonModal Button {
        margin-left: 1;
        margin-right: 1;
    }
    ExportJsonModal Button:focus {
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Exportar Streams a JSON", classes="modal-title")
        yield Label("Nombre del archivo JSON (ej: streams_backup.json):")
        yield Input(
            id="file_name_input",
            placeholder="streams_backup.json",
            value="streams_backup.json",
        )
        yield Horizontal(
            Button("Exportar", id="export_file", variant="success"),
            Button("Cancelar", id="cancel", variant="primary"),
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "export_file":
            file_name = self.query_one("#file_name_input", Input).value.strip()
            if not file_name:
                self.notify(
                    "El nombre del archivo no puede estar vacío", severity="error"
                )
                return
            if not file_name.lower().endswith(".json"):
                file_name += ".json"
            self.dismiss(file_name)
        elif event.button.id == "cancel":
            self.dismiss(None)