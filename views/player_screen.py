#!/usr/bin/env python
# -*- coding: utf-8 -*-

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, Center
from textual.widgets import Static, DataTable, Button, Footer, Input, Select
from textual.reactive import reactive
from textual.screen import Screen

from database.models import Stream, get_session
from sqlmodel import select

import threading
import time
import vlc
import yt_dlp
import logging

logger = logging.getLogger(__name__)


def _truncate(text: str, max_len: int = 60) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


class PlayerScreen(Screen):
    BINDINGS = [
        Binding("q", "app.pop_screen", "Volver", priority=True),
        Binding("a", "prev_stream", "Anterior", priority=True),
        Binding("s", "stop_playback", "Detener", priority=True),
        Binding("d", "next_stream", "Siguiente", priority=True),
        Binding("v", "toggle_volume", "Volumen", priority=True),
    ]
    current_stream: reactive[dict | None] = reactive(None)
    player: vlc.MediaPlayer | None = reactive(None)
    stream_index = 0
    all_streams: list[dict] = []
    streams: list[dict] = []
    last_click_time: float = 0
    active_category: str = "all"
    _play_token: int = 0
    _pending_stream: dict | None = None
    _playback_timer = None

    def compose(self) -> ComposeResult:
        yield Static("Reproductor de Streams", id="screen_title")
        with Vertical(id="player_main_content_area"):
            with Center():
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

            with Center(id="table_section"):
                yield Static(
                    "Seleccione un stream para reproducir (doble clic)",
                    id="placeholder",
                )
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

        try:
            with get_session() as session:
                all_streams_from_db = session.exec(select(Stream)).all()
                self.all_streams = [s.model_dump() for s in all_streams_from_db]
                self.streams = list(self.all_streams)
                self._populate_category_select()
                self.update_table_rows()
        except Exception as e:
            logger.error(
                f"PlayerScreen: Error al cargar streams en on_mount: {e}",
                exc_info=True,
            )
            placeholder = self.query_one("#placeholder", Static)
            placeholder.update("Error al cargar streams")
            placeholder.visible = True
            table.visible = False

        if self.streams:
            table.focus()
        else:
            self.query_one("#perform_search", Button).focus()

        footer = self.query_one(Footer)
        footer.mount(
            Horizontal(
                Button("Anterior", id="prev", classes="control-button"),
                Button("Detener", id="stop", classes="control-button"),
                Button("Siguiente", id="next", classes="control-button"),
                Button("Volumen", id="volume", classes="volume-button"),
                id="playback_controls_in_footer",
            )
        )

        self._playback_timer = self.set_interval(1.0, self._poll_playback_state)

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

    def on_unmount(self) -> None:
        self._play_token += 1
        if self._playback_timer is not None:
            try:
                self._playback_timer.stop()
            except Exception:
                pass
            self._playback_timer = None
        self._stop_player_quiet()

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

    def _apply_filters(self) -> None:
        search_text = self.query_one("#search_input", Input).value.strip().lower()

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

        self.streams = filtered
        self.update_table_rows()

    def _idle_placeholder_message(self) -> str:
        if not self.all_streams:
            return "No hay streams en la base de datos"
        has_search = bool(self.query_one("#search_input", Input).value.strip())
        has_cat = self.active_category != "all"
        if not self.streams and (has_search or has_cat):
            return "No se encontraron resultados"
        if not self.streams:
            return "No hay streams en la base de datos"
        return "Seleccione un stream para reproducir (doble clic)"

    def _stop_player_quiet(self) -> None:
        if not self.player:
            return
        try:
            self.player.stop()
        except Exception:
            pass
        self.player = None

    def _on_playback_failed(self, message: str, token: int | None = None) -> None:
        if token is not None and token != self._play_token:
            return
        self._stop_player_quiet()
        self.current_stream = None
        self._pending_stream = None
        placeholder = self.query_one("#placeholder", Static)
        placeholder.visible = True
        placeholder.update(message)
        self.update_table_highlight()

    def _on_playback_success(self, stream_data: dict, token: int) -> None:
        if token != self._play_token:
            return
        self.current_stream = stream_data
        self._pending_stream = None
        name = stream_data.get("nombre", "")
        self.query_one("#placeholder", Static).update(
            f"Reproduciendo: {_truncate(name)}"
        )
        self.update_table_highlight()

    def _poll_playback_state(self) -> None:
        if not self.player or not self.current_stream:
            return
        try:
            state = self.player.get_state()
        except Exception:
            return

        if state == vlc.State.Ended:
            self._restart_current_playback()
        elif state == vlc.State.Error:
            name = self.current_stream.get("nombre", "")
            self._on_playback_failed(
                f"Error: no se pudo reproducir «{_truncate(name, 40)}»"
            )

    def update_table_rows(self) -> None:
        table = self.query_one("#stream_table", DataTable)
        placeholder = self.query_one("#placeholder", Static)

        table.clear()
        placeholder.visible = True

        if self.streams:
            table.visible = True
            for s_dict in self.streams:
                table.add_row(
                    str(s_dict["id"]),
                    s_dict["nombre"],
                    s_dict["categorias"],
                    "Video" if s_dict["tipo"].lower() == "video" else "Stream",
                )
            self.update_table_highlight()
            if self.current_stream:
                placeholder.update(
                    f"Reproduciendo: {_truncate(self.current_stream['nombre'])}"
                )
            elif self._pending_stream:
                placeholder.update(
                    f"Cargando: {_truncate(self._pending_stream['nombre'])}..."
                )
            else:
                placeholder.update(self._idle_placeholder_message())
            if self.screen.focused != self.query_one("#search_input"):
                table.focus()
        else:
            table.visible = False
            placeholder.update(self._idle_placeholder_message())

        self._set_responsive_columns()

    def update_table_highlight(self) -> None:
        table = self.query_one("#stream_table", DataTable)

        for row_index, stream_dict_in_list in enumerate(self.streams):
            is_current = (
                self.current_stream
                and stream_dict_in_list["id"] == self.current_stream["id"]
            )
            name = stream_dict_in_list["nombre"]

            if is_current:
                cell = f"[bold $success]▶ {name}[/]"
            else:
                cell = name

            table.update_cell_at((row_index, 1), cell)

    @on(Button.Pressed, "#perform_search")
    def perform_search_button(self) -> None:
        self._apply_filters()

    @on(Input.Submitted, "#search_input")
    def search_input_submitted(self, event: Input.Submitted) -> None:
        self._apply_filters()

    @on(Select.Changed, "#category_select")
    def on_category_changed(self, event: Select.Changed) -> None:
        if event.value is Select.BLANK:
            self.active_category = "all"
        else:
            self.active_category = str(event.value)
        self._apply_filters()

    def _playback_thread(
        self,
        stream_link: str,
        stream_name: str,
        stream_type: str,
        stream_data: dict,
        token: int,
    ) -> None:
        def fail(msg: str) -> None:
            try:
                self.app.call_from_thread(self._on_playback_failed, msg, token)
            except Exception:
                logger.error("No se pudo notificar fallo de reproducción a la UI")

        try:
            if token != self._play_token:
                return

            instance = vlc.Instance(
                "--quiet",
                "--intf",
                "dummy",
                "--no-video-title-show",
                "--verbose",
                "0",
                "--no-stats",
                "--no-media-library",
                "--network-caching=3000",
            )
            player = instance.media_player_new()

            if token != self._play_token:
                return

            if stream_type.lower() == "stream":
                media = instance.media_new(stream_link)
                player.set_media(media)
            else:
                ydl_opts = {
                    "format": "bestaudio/best",
                    "quiet": True,
                    "noplaylist": True,
                    "no_warnings": True,
                    "socket_timeout": 15,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(stream_link, download=False)
                    if not info or not info.get("url"):
                        raise yt_dlp.utils.DownloadError(
                            "No se pudo obtener URL de audio"
                        )
                    url = info["url"]
                if token != self._play_token:
                    return
                media = instance.media_new(url)
                player.set_media(media)

            if token != self._play_token:
                return

            self.player = player

            result = player.play()
            if result == -1:
                fail(f"Error: no se pudo iniciar «{_truncate(stream_name, 40)}»")
                return

            is_video = stream_type.lower() == "video"
            timeout_s = 25.0 if is_video else 15.0
            deadline = time.time() + timeout_s
            ok = False

            while time.time() < deadline:
                if token != self._play_token:
                    try:
                        player.stop()
                    except Exception:
                        pass
                    return

                state = player.get_state()

                if state == vlc.State.Playing:
                    ok = True
                    break

                if state == vlc.State.Error:
                    break

                if state in (vlc.State.Ended, vlc.State.Stopped):
                    if time.time() + 0.5 >= deadline:
                        break
                    time.sleep(0.25)
                    continue

                time.sleep(0.25)

            if token != self._play_token:
                try:
                    player.stop()
                except Exception:
                    pass
                return

            if not ok:
                try:
                    player.stop()
                except Exception:
                    pass
                fail(
                    f"Error: el stream no responde «{_truncate(stream_name, 40)}»"
                )
                return

            self.app.call_from_thread(
                self._on_playback_success, stream_data, token
            )
            logger.info(f"Reproduciendo: {stream_name} desde {stream_link}")

        except yt_dlp.utils.DownloadError as e:
            logger.error(
                f"Playback Thread: Error de descarga con yt-dlp: {e}",
                exc_info=True,
            )
            fail("Error: no se pudo obtener el audio del video")
        except Exception as e:
            logger.error(
                f"Playback Thread: Error general en la reproducción: {e}",
                exc_info=True,
            )
            fail("Error en la reproducción")

    def _restart_current_playback(self) -> None:
        if self.player and self.current_stream:
            logger.info(
                f"Reiniciando reproducción de: {self.current_stream['nombre']}"
            )
            try:
                self.player.set_time(0)
                self.player.play()
            except Exception as e:
                logger.error(f"Error al reiniciar: {e}")
                self._on_playback_failed("Error al reiniciar la reproducción")
                return
            self.query_one("#placeholder", Static).update(
                f"Reiniciando: {_truncate(self.current_stream['nombre'])}"
            )
            self.update_table_highlight()

    def play_selected(self, row_index: int):
        if row_index < 0 or row_index >= len(self.streams):
            logger.warning(
                f"play_selected: Índice de stream fuera de rango: {row_index}."
            )
            return

        selected_stream_id = self.streams[row_index]["id"]

        stream_data: dict | None = None
        try:
            with get_session() as session:
                stream_obj = session.get(Stream, selected_stream_id)
                if stream_obj:
                    stream_data = stream_obj.model_dump()
        except Exception as e:
            logger.error(
                f"play_selected: Error al recargar el stream {selected_stream_id}: {e}",
                exc_info=True,
            )
            self._on_playback_failed(f"Error al cargar stream: {selected_stream_id}")
            return

        if not stream_data:
            self._on_playback_failed(
                f"Error: stream {selected_stream_id} no encontrado"
            )
            return

        try:
            self.stream_index = next(
                i for i, s in enumerate(self.streams) if s["id"] == stream_data["id"]
            )
        except StopIteration:
            self.stream_index = 0

        self._play_token += 1
        token = self._play_token
        self._stop_player_quiet()
        self.current_stream = None
        self._pending_stream = stream_data
        self.update_table_highlight()

        placeholder = self.query_one("#placeholder", Static)
        placeholder.update(f"Cargando: {_truncate(stream_data['nombre'])}...")
        placeholder.visible = True
        self.query_one("#stream_table", DataTable).visible = True

        playback_thread = threading.Thread(
            target=self._playback_thread,
            args=(
                stream_data["link"],
                stream_data["nombre"],
                stream_data["tipo"],
                stream_data,
                token,
            ),
            daemon=True,
        )
        playback_thread.start()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        now = time.time()
        if now - self.last_click_time < 0.5:
            self.play_selected(event.cursor_row)
        else:
            self.set_timer(0.05, self.update_table_highlight)
        self.last_click_time = now

    def action_prev_stream(self) -> None:
        self._handle_prev_stream()

    def action_stop_playback(self) -> None:
        self._handle_stop_playback()

    def action_next_stream(self) -> None:
        self._handle_next_stream()

    def action_toggle_volume(self) -> None:
        self._handle_toggle_volume()

    def _handle_stop_playback(self) -> None:
        self._play_token += 1
        self._stop_player_quiet()
        self.current_stream = None
        self._pending_stream = None
        self.query_one("#placeholder", Static).update(self._idle_placeholder_message())
        self.update_table_highlight()

    def _handle_next_stream(self) -> None:
        if self.streams:
            self.stream_index = (self.stream_index + 1) % len(self.streams)
            self.play_selected(self.stream_index)
            self.query_one("#stream_table", DataTable).focus()
        else:
            logger.warning("No hay streams para pasar al siguiente")

    def _handle_prev_stream(self) -> None:
        if self.streams:
            self.stream_index = (
                self.stream_index - 1 + len(self.streams)
            ) % len(self.streams)
            self.play_selected(self.stream_index)
            self.query_one("#stream_table", DataTable).focus()
        else:
            logger.warning("No hay streams para retroceder")

    def _handle_toggle_volume(self) -> None:
        if self.player:
            vol = self.player.audio_get_volume()
            new_vol = 100 if vol < 100 else 30
            self.player.audio_set_volume(new_vol)
        else:
            logger.warning("No hay reproductor activo para cambiar el volumen")

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "stop":
            self._handle_stop_playback()
        elif event.button.id == "next":
            self._handle_next_stream()
        elif event.button.id == "prev":
            self._handle_prev_stream()
        elif event.button.id == "volume":
            self._handle_toggle_volume()