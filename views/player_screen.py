#!/usr/bin/env python
# -*- coding: utf-8 -*-

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Center
from textual.widgets import Static, DataTable, Button, Footer, Input
from textual.reactive import reactive
from textual.screen import Screen
from textual.message import Message

from database.models import Stream, get_session

import threading
import time
import vlc
from vlc import EventType
import yt_dlp
import logging
import os
import sys

logger = logging.getLogger(__name__)

class PlayerScreen(Screen):
    BINDINGS = [
        ("q", "app.pop_screen", "Volver"),
        ("a", "prev_stream", "Anterior"),
        ("s", "stop_playback", "Detener"),
        ("d", "next_stream", "Siguiente"),
        ("v", "toggle_volume", "Volumen"),
    ] 
    
    current_stream: reactive[dict | None] = reactive(None) 
    player: vlc.MediaPlayer | None = reactive(None)
    stream_index = 0
    all_streams: list[dict] = [] 
    streams: list[dict] = [] 
    last_click_time: float = 0

    def compose(self) -> ComposeResult:
        yield Static("Reproductor de Streams", id="screen_title")
        with Vertical(id="main_content_area"): 
            with Center():
                with Horizontal(id="search_bar_container"):
                    yield Static("Buscar por nombre:", classes="search-label")
                    yield Input(placeholder="Escribe para buscar...", id="search_input", classes="search-input")
                    yield Button("🔍 Buscar", id="perform_search", classes="search-button")

            with Center():
                yield Static("Seleccione un stream para reproducir", id="placeholder")
            
            with Center():
                yield DataTable(id="stream_table", zebra_stripes=True)
        
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#stream_table", DataTable)
        table.cursor_type = "row"
        
        table.add_column("ID", width=4) 
        table.add_column("Nombre", width=40)
        table.add_column("Categorías", width=28)
        table.add_column("Tipo", width=14) 
        
        try:
            with get_session() as session:
                all_streams_from_db = session.query(Stream).all()
                self.all_streams = [s.model_dump() for s in all_streams_from_db] 
                self.streams = list(self.all_streams)
            self.update_table_rows() 
        except Exception as e:
            logger.error(f"PlayerScreen: Error al cargar streams en on_mount: {e}", exc_info=True)
            placeholder = self.query_one("#placeholder", Static)
            placeholder.update("Error al cargar streams") 
            placeholder.visible = True
            table.visible = False 
            
        if self.streams:
            table.focus()
        else:
            self.query_one("#search_input", Input).focus()

        footer = self.query_one(Footer)
        footer.mount(
            Horizontal(
                Button("◀ Anterior", id="prev", classes="control-button"),
                Button("■ Detener", id="stop", classes="control-button"),
                Button("Siguiente ▶", id="next", classes="control-button"),
                Button("🔊", id="volume", classes="volume-button"),
                id="playback_controls_in_footer"
            )
        )
    
    def on_unmount(self) -> None:
        if self.player:
            event_manager = self.player.event_manager()
            event_manager.event_detach(EventType.MediaPlayerEndReached)
            self.player.stop()
            self.player = None

    def update_table_rows(self) -> None:
        table = self.query_one("#stream_table", DataTable)
        placeholder = self.query_one("#placeholder", Static)

        table.clear() 
        if self.streams:
            placeholder.visible = False
            table.visible = True
            
            for s_dict in self.streams:
                table.add_row(
                    str(s_dict["id"]), 
                    s_dict["nombre"], 
                    s_dict["categorias"], 
                    "🎬 Video" if s_dict["tipo"].lower() == "video" else "📡 Stream",
                )
            self.update_table_highlight() 
        else:
            table.visible = False
            placeholder.visible = True
            if self.query_one("#search_input").value:
                placeholder.update("No se encontraron resultados")
            else:
                placeholder.update("Seleccione un stream para reproducir")

    def update_table_highlight(self) -> None:
        table = self.query_one("#stream_table", DataTable)
        for row_index, stream_dict_in_list in enumerate(self.streams):
            is_current = self.current_stream and stream_dict_in_list["id"] == self.current_stream["id"]
            prefix = "▶ " if is_current else ""
            table.update_cell_at((row_index, 1), f"{prefix}{stream_dict_in_list['nombre']}")
        
        if self.current_stream:
            try:
                current_stream_index_in_filtered_list = next(
                    i for i, s in enumerate(self.streams) 
                    if s["id"] == self.current_stream["id"]
                )
                table.move_cursor(row=current_stream_index_in_filtered_list)
                table.focus()
            except StopIteration:
                pass

    @on(Button.Pressed, "#perform_search")
    def perform_search_button(self) -> None:
        search_input = self.query_one("#search_input", Input)
        self._apply_search_filter(search_input.value)

    @on(Input.Submitted, "#search_input")
    def search_input_submitted(self, event: Input.Submitted) -> None:
        self._apply_search_filter(event.value)

    def _apply_search_filter(self, search_value: str) -> None:
        search_text = search_value.strip().lower()
        
        if search_text:
            self.streams = [
                s for s in self.all_streams 
                if search_text in s.get("nombre", "").lower()
            ]
        else:
            self.streams = list(self.all_streams)

        self.update_table_rows()
        table = self.query_one("#stream_table", DataTable)
        
        if table.row_count > 0 and self.screen.focused != self.query_one("#search_input"):
            table.move_cursor(row=0)
            table.focus()

    def _playback_thread(self, stream_link: str, stream_name: str, stream_type: str) -> None:
        placeholder = self.query_one("#placeholder", Static) 
        
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            with open(os.devnull, 'w') as fnull:
                sys.stdout = fnull
                sys.stderr = fnull
                
                if self.player:
                    self.player.stop()

                instance = vlc.Instance()
                self.player = instance.media_player_new() 
                
                if stream_type.lower() == "stream":
                    media = instance.media_new(stream_link)
                    self.player.set_media(media)
                else: 
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'quiet': True,
                        'noplaylist': True,
                        'no_warnings': True,
                        'logtostderr': False, 
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(stream_link, download=False)
                        url = info['url']
                    media = instance.media_new(url)
                    self.player.set_media(media)

                event_manager = self.player.event_manager()
                event_manager.event_attach(EventType.MediaPlayerEndReached, 
                                           lambda event: self.app.call_from_thread(self._restart_current_playback))

                self.player.play()

                time.sleep(0.5) 
                
                self.app.call_from_thread(placeholder.update, f"▶ Reproduciendo: {stream_name}")
                
                logger.info(f"Reproduciendo: {stream_name} desde {stream_link}")

        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Playback Thread: Error de descarga con yt-dlp: {e}", exc_info=True)
            self.app.call_from_thread(placeholder.update, "Error: Problema al obtener audio")
        except Exception as e:
            logger.error(f"Playback Thread: Error general en la reproducción: {e}", exc_info=True)
            self.app.call_from_thread(placeholder.update, "Error en la reproducción")
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def _restart_current_playback(self) -> None:
        if self.player and self.current_stream:
            logger.info(f"Reiniciando reproducción de: {self.current_stream['nombre']}")
            self.player.set_time(0) 
            self.player.play()
            self.query_one("#placeholder", Static).update(f"▶ Reiniciando: {self.current_stream['nombre']}")
            self.update_table_highlight()
        elif not self.current_stream:
            logger.warning("No hay stream actual para reiniciar la reproducción.")
            self.query_one("#placeholder", Static).update("Reproducción finalizada.")


    def play_selected(self, row_index: int):
        if row_index < 0 or row_index >= len(self.streams):
            logger.warning(f"play_selected: Índice de stream fuera de rango: {row_index}.")
            return

        selected_stream_id = self.streams[row_index]["id"]

        stream_data: dict | None = None
        try:
            with get_session() as session:
                stream_obj = session.get(Stream, selected_stream_id) 
                if stream_obj:
                    stream_data = stream_obj.model_dump() 
        except Exception as e:
            logger.error(f"play_selected: Error al recargar el stream {selected_stream_id}: {e}", exc_info=True)
            placeholder = self.query_one("#placeholder", Static)
            placeholder.update(f"Error al cargar stream: {selected_stream_id}")
            placeholder.visible = True
            self.query_one("#stream_table", DataTable).visible = False
            return

        self.current_stream = stream_data

        if not self.current_stream:
            logger.error(f"play_selected: Stream con ID {selected_stream_id} no fue encontrado después de recargar")
            placeholder = self.query_one("#placeholder", Static)
            placeholder.update(f"Error: Stream {selected_stream_id} no encontrado. Intente de nuevo")
            placeholder.visible = True
            self.query_one("#stream_table", DataTable).visible = False
            return

        try:
            self.stream_index = next(
                i for i, s in enumerate(self.streams) 
                if s["id"] == self.current_stream["id"]
            )
        except StopIteration:
            self.stream_index = 0 

        placeholder = self.query_one("#placeholder", Static)
        placeholder.update(f"Cargando: {self.current_stream['nombre']}...")
        placeholder.visible = True
        self.query_one("#stream_table", DataTable).visible = True 
        self.update_table_highlight()

        if self.player:
            event_manager = self.player.event_manager()
            event_manager.event_detach(EventType.MediaPlayerEndReached)
            self.player.stop()
            self.player = None

        playback_thread = threading.Thread(
            target=self._playback_thread,
            args=(
                self.current_stream['link'],
                self.current_stream['nombre'],
                self.current_stream['tipo']
            ),
            daemon=True
        )
        playback_thread.start()


    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        now = time.time()
        if now - self.last_click_time < 0.5:
            self.play_selected(event.cursor_row) 
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
        if self.player:
            event_manager = self.player.event_manager()
            event_manager.event_detach(EventType.MediaPlayerEndReached)
            self.player.stop()
            self.player = None
            self.query_one("#placeholder", Static).update("Seleccione un stream para reproducir")
            self.current_stream = None
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
            self.stream_index = (self.stream_index - 1 + len(self.streams)) % len(self.streams)
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