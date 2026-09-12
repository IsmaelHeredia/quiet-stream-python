#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, Input, Button, Label, Select
from textual.screen import ModalScreen
from textual import on

from database.models import Stream, get_session

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
    StreamModal Select {
        width: 100%;
        margin-bottom: 1;
    }
    StreamModal Horizontal {
        height: auto;
        margin-top: 1;
        align: center middle;
    }
    StreamModal Button {
        margin-left: 1;
        margin-right: 1;
    }
    StreamModal Button:focus {
        text-style: bold;
    }
    """

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
        initial_tipo = "stream"
        if self.stream and self.stream.tipo:
            t = self.stream.tipo.lower().strip()
            if t == "video":
                initial_tipo = "video"
            else:
                initial_tipo = "stream"

        yield Select(
            [("Stream", "stream"), ("Video", "video")],
            id="tipo_select",
            value=initial_tipo,
            prompt="Tipo",
            allow_blank=False,
        )

        yield Horizontal(
            Button("Guardar", id="save", variant="success"),
            Button("Cancelar", id="cancel", variant="primary"),
        )

    def on_mount(self) -> None:
        if self.inputs:
            self.inputs[list(self.inputs.keys())[0]].focus()

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            data = {k: (v.value or "").strip() for k, v in self.inputs.items()}

            tipo_select = self.query_one("#tipo_select", Select)
            if tipo_select.value is Select.BLANK or tipo_select.value is None:
                self.app.bell()
                self.notify(
                    "Por favor, selecciona un tipo (Stream o Video)",
                    severity="error",
                )
                return

            data["tipo"] = str(tipo_select.value).strip().lower()
            if data["tipo"] not in ("stream", "video"):
                data["tipo"] = "stream"

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
                            self.notify(
                                "Error: Stream no encontrado para actualizar",
                                severity="error",
                            )
                    else:
                        new_stream = Stream(**data)
                        session.add(new_stream)
                        session.commit()
                        session.refresh(new_stream)
                        self.app.notify("Stream creado con éxito")
                        self.dismiss(True)
            except Exception as e:
                logger.error(
                    f"Error al guardar/actualizar stream: {e}", exc_info=True
                )
                self.app.bell()
                self.notify(f"Error al guardar stream: {str(e)}", severity="error")

        elif event.button.id == "cancel":
            self.dismiss(False)