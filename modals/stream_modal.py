#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, Input, Button, Label, RadioSet, RadioButton
from textual.screen import ModalScreen
from textual.reactive import reactive
from textual import on

from database.models import Stream, get_session
from sqlmodel import Session

from utils.functions import clean_emoji_from_string

logger = logging.getLogger(__name__)

class StreamModal(ModalScreen[bool]):
    CSS = """
    StreamModal {
        background: $surface;
        border: round $primary;
        width: 60;
        height: auto;
        padding: 1;
    }
    StreamModal > Static {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }
    StreamModal Input {
        width: 100%;
        margin-bottom: 1;
    }
    StreamModal Horizontal {
        height: auto;
        margin-top: 1;
        align: center middle;
    }
    StreamModal RadioSet {
        width: 100%;
        margin-bottom: 1;
    }
    StreamModal RadioButton {
        margin-right: 2;
    }
    """

    selected_tipo: reactive[str | None] = reactive(None)

    def __init__(self, title: str, stream: Stream = None):
        super().__init__()
        self.stream = stream
        self.title_text = title
        self.inputs = {}

    def compose(self) -> ComposeResult:
        yield Static(self.title_text, classes="modal-title")

        fields = [
            ("nombre", "Nombre"),
            ("link", "URL del stream"),
            ("categorias", "Categorías (separadas por coma)"),
        ]

        for field, label in fields:
            yield Label(label)
            input_field = Input(name=field)
            if self.stream:
                input_field.value = getattr(self.stream, field) or ""
            self.inputs[field] = input_field
            yield input_field

        yield Label("Tipo")
        with RadioSet(id="tipo_radio_set"):
            yield RadioButton("📡 Stream", id="radio_stream")
            yield RadioButton("🎬 Video", id="radio_video")

        yield Horizontal(
            Button("💾 Guardar", id="save", variant="primary"),
            Button("❌ Cancelar", id="cancel")
        )

    def on_mount(self) -> None:
        if self.stream and self.stream.tipo:
            if self.stream.tipo == "Stream":
                self.query_one("#radio_stream", RadioButton).value = True
                self.selected_tipo = "Stream"
            elif self.stream.tipo == "Video":
                self.query_one("#radio_video", RadioButton).value = True
                self.selected_tipo = "Video"
            else:
                self.query_one("#radio_stream", RadioButton).value = True
                self.selected_tipo = "Stream"
        else:
            self.query_one("#radio_stream", RadioButton).value = True
            self.selected_tipo = "Stream"

        if self.inputs:
            self.inputs[list(self.inputs.keys())[0]].focus()

    @on(RadioSet.Changed, "#tipo_radio_set")
    def radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.pressed:
            self.selected_tipo = clean_emoji_from_string(event.pressed.label.plain)
        else:
            self.selected_tipo = None

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            data = {k: (v.value or "").strip() for k, v in self.inputs.items()}
            final_selected_tipo = self.selected_tipo

            if final_selected_tipo is None:
                self.app.bell()
                self.notify("Por favor, selecciona un tipo (Stream o Video)", severity="error")
                return

            data["tipo"] = final_selected_tipo

            if not data["nombre"]:
                self.app.bell()
                self.notify("El nombre no puede estar vacío", severity="error")
                return
            if not data["link"]:
                self.app.bell()
                self.notify("El link no puede estar vacío", severity="error")
                return

            try:
                with get_session() as session:
                    if self.stream:
                        stream_to_update = session.get(Stream, self.stream.id)
                        if stream_to_update:
                            stream_to_update.nombre = data["nombre"]
                            stream_to_update.link = data["link"]
                            stream_to_update.categorias = data["categorias"]
                            stream_to_update.tipo = data["tipo"]
                            session.commit()
                            session.refresh(stream_to_update)
                            self.app.notify("Stream actualizado con éxito")
                            self.dismiss(True)
                        else:
                            self.app.bell()
                            self.notify("Error: Stream no encontrado para actualizar", severity="error")
                    else:
                        new_stream = Stream(**data)
                        session.add(new_stream)
                        session.commit()
                        session.refresh(new_stream)
                        self.app.notify("Stream creado con éxito")
                        self.dismiss(True)
            except Exception as e:
                logger.error(f"Error al guardar/actualizar stream: {e}", exc_info=True)
                self.app.bell()
                self.notify(f"Error al guardar stream: {str(e)}", severity="error")
        elif event.button.id == "cancel":
            self.dismiss(False)