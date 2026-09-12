#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import json
from pathlib import Path
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, Center
from textual.widgets import Footer, Static, DataTable, Input, Button, Select
from textual.screen import Screen
from textual.reactive import reactive
from textual import work, on
from sqlmodel import select

from database.models import Stream, get_session
from utils.config_manager import ENABLE_DEBUG_LOGGING

from modals.confirmation_modal import ConfirmationModal
from modals.stream_modal import StreamModal
from modals.import_json_modal import ImportJsonModal
from modals.export_json_modal import ExportJsonModal
from modals.stream_validation_modal import StreamValidationModal

if ENABLE_DEBUG_LOGGING:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
logger = logging.getLogger(__name__)


class AdminScreen(Screen):
    CSS_PATH = "../static/style.css"
    BINDINGS = [
        Binding("a", "add_stream", "Agregar", priority=True),
        Binding("e", "edit_stream", "Editar", priority=True),
        Binding("d", "delete_stream", "Eliminar", priority=True),
        Binding("i", "import_streams", "Importar JSON", priority=True),
        Binding("x", "export_streams", "Exportar JSON", priority=True),
        Binding("v", "validate_streams", "Validar Streams", priority=True),
        Binding("q", "go_back", "Volver", priority=True),
    ]

    selected_stream_id: reactive[int | None] = reactive(None)
    all_streams: list[dict] = []
    filtered_streams: reactive[list[dict]] = reactive([])
    active_category: str = "all"

    def compose(self) -> ComposeResult:
        yield Static("Gestor de Streams", id="screen_title")
        with Vertical(id="admin_main_content_area"):
            with Center(id="search_section"):
                with Horizontal(id="search_bar_container"):
                    yield Static("Buscar:", classes="search-label")
                    yield Input(
                        placeholder="Nombre...",
                        id="search_input",
                        classes="search-input",
                    )
                    yield Select(
                        [("Todas", "all")],
                        id="category_select",
                        value="all",
                        prompt="Categoría",
                        classes="category-select",
                    )
                    yield Button("Buscar", id="perform_search", classes="search-button")

            with Center():
                with Horizontal(id="admin_actions_bar"):
                    yield Button("Agregar", id="btn_add", variant="success")
                    yield Button("Editar", id="btn_edit", variant="primary")
                    yield Button("Eliminar", id="btn_delete", variant="error")
                    yield Button("Importar", id="btn_import", variant="warning")
                    yield Button("Exportar", id="btn_export", variant="warning")
                    yield Button("Validar", id="btn_validate", variant="default")

            with Center(id="table_section"):
                yield Static("Cargando streams...", id="placeholder")
                yield DataTable(id="stream_table", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#stream_table", DataTable)
        table.cursor_type = "row"
        table.add_column("ID", key="id", width=5)
        table.add_column("Nombre", key="nombre", width=40)
        table.add_column("Categorías", key="categorias", width=28)
        table.add_column("Tipo", key="tipo", width=14)
        self._set_responsive_columns()
        self._load_all_streams()

        if self.filtered_streams:
            table.focus()
        else:
            self.query_one("#perform_search", Button).focus()

    def on_resize(self, event) -> None:
        self._set_responsive_columns()

    def _set_responsive_columns(self) -> None:
        try:
            table = self.query_one("#stream_table", DataTable)
            available = max(30, table.size.width - 4)

            table.columns["id"].width = max(4, int(available * 0.06))
            table.columns["nombre"].width = max(12, int(available * 0.48))
            table.columns["categorias"].width = max(10, int(available * 0.30))
            table.columns["tipo"].width = max(8, int(available * 0.16))
            table.refresh()
        except Exception:
            pass

    def _extract_categories(self) -> list[str]:
        cats: set[str] = set()
        for s in self.all_streams:
            raw = s.get("categorias") or ""
            for part in raw.split(","):
                part = part.strip()
                if part:
                    cats.add(part)
        return sorted(cats, key=str.lower)

    def _populate_category_select(self) -> None:
        select_widget = self.query_one("#category_select", Select)
        options = [("Todas", "all")]
        for cat in self._extract_categories():
            options.append((cat, cat))
        select_widget.set_options(options)
        select_widget.value = "all"
        self.active_category = "all"

    def watch_filtered_streams(
        self, old_streams: list[dict], new_streams: list[dict]
    ) -> None:
        table = self.query_one("#stream_table", DataTable)
        placeholder = self.query_one("#placeholder", Static)
        table.clear()
        if new_streams:
            placeholder.visible = False
            table.visible = True
            for s_dict in new_streams:
                table.add_row(
                    str(s_dict["id"]),
                    s_dict["nombre"],
                    s_dict["categorias"],
                    "Video" if s_dict["tipo"].lower() == "video" else "Stream",
                    key=str(s_dict["id"]),
                )
            self._set_responsive_columns()
            if table.row_count > 0 and self.screen.focused != self.query_one(
                "#search_input"
            ):
                table.move_cursor(row=0)
                table.focus()
        else:
            table.visible = False
            placeholder.visible = True
            has_search = bool(self.query_one("#search_input").value.strip())
            has_cat = self.active_category != "all"
            if has_search or has_cat:
                placeholder.update("No se encontraron resultados para la búsqueda")
            else:
                placeholder.update("No hay streams en la base de datos")

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        try:
            stream_id = int(event.row_key.value)
            self.selected_stream_id = stream_id
        except ValueError:
            self.selected_stream_id = None
            logger.error(f"Error al convertir row_key a int: {event.row_key}")

    @on(Button.Pressed, "#perform_search")
    def perform_search_button(self) -> None:
        search_input = self.query_one("#search_input", Input)
        self._apply_search_filter(search_input.value)

    @on(Input.Submitted, "#search_input")
    def search_input_submitted(self, event: Input.Submitted) -> None:
        self._apply_search_filter(event.value)

    @on(Select.Changed, "#category_select")
    def on_category_changed(self, event: Select.Changed) -> None:
        if event.value is Select.BLANK:
            self.active_category = "all"
        else:
            self.active_category = str(event.value)
        search_input = self.query_one("#search_input", Input)
        self._apply_search_filter(search_input.value)

    def _apply_search_filter(self, search_value: str) -> None:
        search_text = search_value.strip().lower()
        filtered = list(self.all_streams)

        if self.active_category and self.active_category != "all":
            cat_lower = self.active_category.lower()
            filtered = [
                s
                for s in filtered
                if cat_lower in (s.get("categorias") or "").lower()
            ]

        if search_text:
            filtered = [
                s
                for s in filtered
                if search_text in (s.get("nombre") or "").lower()
            ]

        self.filtered_streams = filtered

    def _load_all_streams(self) -> None:
        try:
            with get_session() as session:
                streams_from_db = session.exec(select(Stream)).all()
                self.all_streams = [s.model_dump() for s in streams_from_db]
                self._populate_category_select()
                self.filtered_streams = list(self.all_streams)
                logger.debug(f"Todos los streams cargados: {len(self.all_streams)}.")
        except Exception as e:
            logger.error(f"Error al cargar todos los streams: {e}", exc_info=True)
            self.query_one("#placeholder", Static).update("Error al cargar streams")
            self.query_one("#placeholder", Static).visible = True
            self.query_one("#stream_table", DataTable).visible = False

    def refresh_table(self):
        self._load_all_streams()
        self.set_timer(0.05, self._set_responsive_columns)

    def action_go_back(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn_add")
    def on_btn_add(self) -> None:
        self.action_add_stream()

    @on(Button.Pressed, "#btn_edit")
    def on_btn_edit(self) -> None:
        self.action_edit_stream()

    @on(Button.Pressed, "#btn_delete")
    def on_btn_delete(self) -> None:
        self.action_delete_stream()

    @on(Button.Pressed, "#btn_import")
    def on_btn_import(self) -> None:
        self.action_import_streams()

    @on(Button.Pressed, "#btn_export")
    def on_btn_export(self) -> None:
        self.action_export_streams()

    @on(Button.Pressed, "#btn_validate")
    def on_btn_validate(self) -> None:
        self.action_validate_streams()

    @work
    async def action_add_stream(self):
        modal = StreamModal("Agregar nuevo stream")
        result = await self.app.push_screen_wait(modal)
        if result:
            self.refresh_table()

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
            else:
                self.notify("Stream no encontrado", severity="error")
                self.selected_stream_id = None

    @work
    async def action_delete_stream(self):
        if self.selected_stream_id is None:
            self.notify("Selecciona un stream primero", severity="warning")
            return

        stream_name = ""
        try:
            with get_session() as session:
                stream_to_delete = session.get(Stream, self.selected_stream_id)
                if stream_to_delete:
                    stream_name = stream_to_delete.nombre
                else:
                    self.notify("Stream no encontrado", severity="error")
                    self.selected_stream_id = None
                    return
        except Exception as e:
            logger.error(
                f"Error al obtener stream para confirmación: {e}", exc_info=True
            )
            self.notify(f"Error al preparar eliminación: {e}", severity="error")
            return

        confirm_modal = ConfirmationModal(
            f"¿Estás seguro de que quieres eliminar el stream '{stream_name}'?"
        )
        result = await self.app.push_screen_wait(confirm_modal)

        if result:
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
            finally:
                self.selected_stream_id = None
        else:
            self.selected_stream_id = None

    @work
    async def action_import_streams(self):
        modal = ImportJsonModal()
        file_path = await self.app.push_screen_wait(modal)

        if file_path:
            path = Path(file_path)
            if not path.exists():
                self.notify(f"El archivo '{file_path}' no existe", severity="error")
                return
            if not path.is_file():
                self.notify(f"La ruta '{file_path}' no es un archivo", severity="error")
                return
            if path.suffix.lower() != ".json":
                self.notify(
                    f"El archivo '{file_path}' no es un archivo JSON válido",
                    severity="error",
                )
                return

            imported_count = 0
            skipped_count = 0
            total_in_file = 0

            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if not isinstance(data, list):
                    self.notify(
                        "El archivo JSON debe contener una lista de streams",
                        severity="error",
                    )
                    return

                total_in_file = len(data)
                self.notify(
                    f"Procesando {total_in_file} streams desde '{file_path}'...",
                    timeout=3,
                )

                with get_session() as session:
                    for stream_data in data:
                        required_fields = ["nombre", "link", "categorias", "tipo"]
                        if not all(field in stream_data for field in required_fields):
                            logger.warning(
                                f"Stream con campos faltantes, saltando: {stream_data}"
                            )
                            skipped_count += 1
                            continue

                        if not all(
                            isinstance(stream_data.get(field), str)
                            and stream_data.get(field).strip()
                            for field in required_fields
                        ):
                            logger.warning(
                                f"Stream con datos inválidos, saltando: {stream_data}"
                            )
                            skipped_count += 1
                            continue

                        existing_stream = session.exec(
                            select(Stream).where(
                                (Stream.nombre == stream_data["nombre"].strip())
                                | (Stream.link == stream_data["link"].strip())
                            )
                        ).first()

                        if existing_stream:
                            logger.info(
                                f"Stream '{stream_data['nombre']}' ya existe, saltando"
                            )
                            skipped_count += 1
                        else:
                            try:
                                new_stream = Stream(
                                    nombre=stream_data["nombre"].strip(),
                                    link=stream_data["link"].strip(),
                                    categorias=stream_data["categorias"].strip(),
                                    tipo=stream_data["tipo"].strip(),
                                )
                                session.add(new_stream)
                                session.commit()
                                session.refresh(new_stream)
                                imported_count += 1
                                logger.info(
                                    f"Stream '{new_stream.nombre}' importado correctamente"
                                )
                            except Exception as db_e:
                                logger.error(
                                    f"Error al insertar stream '{stream_data.get('nombre', 'N/A')}': {db_e}",
                                    exc_info=True,
                                )
                                skipped_count += 1
                                session.rollback()

                self.notify(
                    f"Importación completada: {imported_count} streams agregados, "
                    f"{skipped_count} saltados de {total_in_file} en el archivo",
                    severity="info",
                    timeout=5,
                )
                self.refresh_table()

            except FileNotFoundError:
                self.notify(
                    f"Archivo no encontrado en la ruta '{file_path}'", severity="error"
                )
            except json.JSONDecodeError:
                self.notify(
                    f"El archivo '{file_path}' no es un JSON válido", severity="error"
                )
            except Exception as e:
                logger.error(
                    f"Error inesperado durante la importación: {e}", exc_info=True
                )
                self.notify(
                    f"Error inesperado durante la importación: {str(e)}",
                    severity="error",
                )

    @work
    async def action_export_streams(self):
        modal = ExportJsonModal()
        file_name = await self.app.push_screen_wait(modal)

        if file_name:
            path = Path(file_name)

            try:
                with get_session() as session:
                    streams = session.exec(select(Stream)).all()

                streams_data = [s.model_dump() for s in streams]

                with open(path, "w", encoding="utf-8") as f:
                    json.dump(streams_data, f, indent=4, ensure_ascii=False)

                self.notify(
                    f"Exportación completada: {len(streams_data)} streams exportados a '{file_name}'",
                    severity="info",
                    timeout=5,
                )

            except Exception as e:
                logger.error(
                    f"Error durante la exportación de streams: {e}", exc_info=True
                )
                self.notify(f"Error al exportar streams: {str(e)}", severity="error")

    @work
    async def action_validate_streams(self):
        all_streams_data = []
        try:
            with get_session() as session:
                streams_from_db = session.exec(select(Stream)).all()
                all_streams_data = [s.model_dump() for s in streams_from_db]
        except Exception as e:
            logger.error(
                f"Error al obtener streams para validación: {e}", exc_info=True
            )
            self.notify(f"Error al cargar streams para validar: {e}", severity="error")
            return

        if not all_streams_data:
            self.notify("No hay streams para validar", severity="info")
            return

        validation_modal = StreamValidationModal(streams_to_validate=all_streams_data)
        broken_streams_data = await self.app.push_screen_wait(validation_modal)

        if not broken_streams_data:
            self.notify(
                "Validación finalizada. No se eliminó ningún stream.",
                severity="info",
            )
            self.refresh_table()
            return

        broken_count = len(broken_streams_data)
        broken_stream_names = [
            stream.get("nombre", "Desconocido") for stream in broken_streams_data
        ]

        display_limit = 10
        names_to_display = broken_stream_names[:display_limit]
        names_str = "\n".join([f"- {name}" for name in names_to_display])
        if len(broken_stream_names) > display_limit:
            names_str += f"\n...y {len(broken_stream_names) - display_limit} más."

        message = (
            f"Se eliminarán {broken_count} stream(s) seleccionado(s):\n\n"
            f"{names_str}\n\n"
            "¿Confirmás la eliminación?"
        )
        confirm_delete_modal = ConfirmationModal(message)
        confirm_delete_result = await self.app.push_screen_wait(confirm_delete_modal)

        if confirm_delete_result:
            deleted_count = 0
            try:
                with get_session() as session:
                    for stream_data in broken_streams_data:
                        stream_id = stream_data.get("id")
                        if stream_id is not None:
                            db_stream = session.get(Stream, stream_id)
                            if db_stream:
                                session.delete(db_stream)
                                deleted_count += 1
                                logger.info(
                                    f"Eliminado stream no funcional: {db_stream.nombre}"
                                )
                            else:
                                logger.warning(
                                    f"Stream con ID {stream_id} no encontrado para eliminación"
                                )
                        else:
                            logger.warning(
                                f"Stream sin ID, no se puede eliminar: {stream_data}"
                            )
                    session.commit()
                self.notify(
                    f"{deleted_count} stream(s) eliminado(s)",
                    severity="info",
                    timeout=3,
                )
                self.refresh_table()
            except Exception as e:
                logger.error(
                    f"Error al eliminar streams no funcionales: {e}",
                    exc_info=True,
                )
                self.notify(
                    f"Error al eliminar streams: {e}",
                    severity="error",
                )
        else:
            self.notify("Eliminación cancelada", severity="info")

        self.refresh_table()