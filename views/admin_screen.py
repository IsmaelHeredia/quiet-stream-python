#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer, Static, DataTable, Input, Button, Label
from textual.screen import Screen, ModalScreen
from textual.reactive import reactive
from textual import work
from database.models import Stream, get_session
from sqlmodel import select

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)
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
            ("tipo", "Tipo (live/video)")
        ]

        for field, label in fields:
            yield Label(label)
            input_field = Input(name=field)
            if self.stream:
                input_field.value = getattr(self.stream, field) or ""
            self.inputs[field] = input_field
            yield input_field

        yield Horizontal(
            Button("Guardar", id="save", variant="primary"),
            Button("Cancelar", id="cancel")
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            data = {k: (v.value or "").strip() for k, v in self.inputs.items()}

            if not data["nombre"]:
                self.notify("El nombre es requerido", severity="error")
                return
            if not data["link"]:
                self.notify("La URL del stream es requerida", severity="error")
                return
            if not data["categorias"]:
                self.notify("Las categorías son requeridas", severity="error")
                return
            if not data["tipo"]:
                self.notify("El tipo (live/video) es requerido", severity="error")
                return

            try:
                with get_session() as session:
                    if self.stream:
                        db_stream = session.get(Stream, self.stream.id)
                        if db_stream:
                            db_stream.nombre = data["nombre"]
                            db_stream.link = data["link"]
                            db_stream.categorias = data["categorias"]
                            db_stream.tipo = data["tipo"]
                            session.add(db_stream)
                            session.commit()
                            message = f"Stream '{db_stream.nombre}' actualizado correctamente"
                            self.dismiss(True)
                        else:
                            self.notify("Stream no encontrado en la base de datos", severity="error")
                            return
                    else:
                        stream = Stream(**data)
                        session.add(stream)
                        session.commit()
                        message = f"Stream '{stream.nombre}' agregado correctamente"
                        self.dismiss(True)
                
                self.notify(message)
                
            except Exception as e:
                logger.error(f"Error al guardar stream: {e}", exc_info=True)
                self.notify(f"Error al guardar: {str(e)}", severity="error")
                return
        elif event.button.id == "cancel":
            self.dismiss(False)

class AdminScreen(Screen):
    CSS_PATH = "../static/style.css"
    BINDINGS = [
        ("a", "add_stream", "Agregar"),
        ("e", "edit_stream", "Editar"),
        ("d", "delete_stream", "Eliminar"),
        ("q", "quit", "Salir"),
    ]

    selected_stream_id: reactive[int | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Administrador de Streams", classes="title"),
            self.build_table(),
            Footer()
        )

    def build_table(self):
        self.table = DataTable(zebra_stripes=True)
        self.table.add_columns("ID", "Nombre", "Categorías", "Tipo", "URL")
        self.refresh_table()
        return self.table

    def refresh_table(self):
        self.table.clear()
        logger.debug("Refrescando tabla de streams...")
        try:
            with get_session() as session:
                streams = session.exec(select(Stream)).all()
                for s in streams:
                    self.table.add_row(
                        str(s.id),
                        s.nombre,
                        s.categorias,
                        s.tipo,
                        s.link[:30] + "..." if s.link and len(s.link) > 30 else s.link or ""
                    )
            logger.debug(f"Tabla de streams actualizada con {len(streams)} registros.")
        except Exception as e:
            logger.error(f"Error al refrescar tabla: {e}", exc_info=True)
            self.notify(f"Error al cargar streams: {e}", severity="error")

    @work
    async def action_add_stream(self):
        modal = StreamModal("Agregar nuevo stream")
        result = await self.app.push_screen_wait(modal)
        if result:
            self.refresh_table()
            self.notify("Tabla actualizada con los cambios", timeout=2)

    @work
    async def action_edit_stream(self):
        if self.selected_stream_id is None:
            self.notify("Selecciona un stream primero", severity="warning")
            return

        with get_session() as session:
            stream = session.get(Stream, self.selected_stream_id)
            if stream:
                modal = StreamModal("Editar stream", stream=stream)
                result = await self.app.push_screen_wait(modal)
                if result:
                    self.refresh_table()
                    self.notify("Tabla actualizada con los cambios", timeout=2)
            else:
                self.notify("Stream no encontrado", severity="error")

    def action_delete_stream(self):

        if self.selected_stream_id is None:
            self.notify("Selecciona un stream primero", severity="warning")
            return

        try:
            with get_session() as session:
                stream = session.get(Stream, self.selected_stream_id)
                if stream:
                    session.delete(stream)
                    session.commit()
                    self.notify(f"Stream '{stream.nombre}' eliminado")
                    self.refresh_table()
                else:
                    self.notify("Stream no encontrado", severity="error")
        except Exception as e:
            logger.error(f"Error al eliminar stream: {e}", exc_info=True)
            self.notify(f"Error al eliminar: {e}", severity="error")

        self.selected_stream_id = None

    def action_quit(self):
        self.app.pop_screen()

    def on_mount(self):
        self.table.cursor_type = "row"
        self.refresh_table()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row = self.table.get_row(event.row_key)
        if row:
            try:
                self.selected_stream_id = int(row[0])
            except ValueError:
                self.selected_stream_id = None

class AdminApp(App):
    def on_mount(self):
        self.push_screen(AdminScreen())

if __name__ == "__main__":
    AdminApp().run()