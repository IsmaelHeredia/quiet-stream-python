#!/usr/bin/env python
# -*- coding: utf-8 -*-

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, DataTable, Button, Footer
from textual.reactive import reactive
from textual.screen import Screen
from textual.message import Message

from database.models import Stream, get_session

import threading
import time
import vlc
import yt_dlp
import logging

logger = logging.getLogger(__name__)

class PlaybackBar(Static):
    class PlayRequest(Message):
        def __init__(self, stream: Stream) -> None:
            self.stream = stream
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Button("◀ Anterior", id="prev", classes="control-button"),
            Button("■ Detener", id="stop", classes="control-button"),
            Button("Siguiente ▶", id="next", classes="control-button"),
            id="controls"
        )
        yield Button("🔊", id="volume", classes="volume-button")

class PlayerScreen(Screen):
    BINDINGS = [("q", "app.pop_screen", "Salir")]
    
    current_stream: reactive[dict | None] = reactive(None) 
    player: vlc.MediaPlayer | None = None
    stream_index = 0
    streams: list[dict] = [] 
    last_click_time: float = 0

    def compose(self) -> ComposeResult:
        yield Static("Seleccione un stream para reproducir", id="placeholder")
        yield DataTable(id="stream_table")
        yield PlaybackBar()
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#stream_table", DataTable)
        table.cursor_type = "row"
        table.add_columns("ID", "Nombre", "Categorías", "Tipo")
        
        try:
            with get_session() as session:
                all_streams_from_db = session.query(Stream).all()
                self.streams = [s.model_dump() for s in all_streams_from_db] 
                
                for s_dict in self.streams:
                    table.add_row(str(s_dict["id"]), s_dict["nombre"], s_dict["categorias"], s_dict["tipo"])
        except Exception as e:
            logger.error(f"PlayerScreen: Error al cargar streams en on_mount: {e}", exc_info=True)
            self.query_one("#placeholder", Static).update("Error al cargar streams.")

    def update_table_highlight(self):
        table = self.query_one("#stream_table", DataTable)
        for row_index, stream_dict_in_list in enumerate(self.streams):
            prefix = "▶ " if self.current_stream and stream_dict_in_list["id"] == self.current_stream["id"] else ""
            table.update_cell_at((row_index, 1), f"{prefix}{stream_dict_in_list['nombre']}")

    def play_selected(self, row_index: int):
        if row_index < 0 or row_index >= len(self.streams):
            logger.warning(f"play_selected: Índice de stream fuera de rango: {row_index}.")
            return

        if self.player:
            self.player.stop()

        selected_stream_id = self.streams[row_index]["id"]

        stream_data: dict | None = None
        try:
            with get_session() as session:
                stream_obj = session.get(Stream, selected_stream_id) 
                if stream_obj:
                    stream_data = stream_obj.model_dump() 
        except Exception as e:
            logger.error(f"play_selected: Error al recargar el stream {selected_stream_id}: {e}", exc_info=True)
            self.query_one("#placeholder", Static).update(f"Error al cargar stream: {selected_stream_id}")
            return

        self.current_stream = stream_data

        if not self.current_stream:
            logger.error(f"play_selected: Stream con ID {selected_stream_id} no fue encontrado después de recargar.")
            self.query_one("#placeholder", Static).update(f"Error: Stream {selected_stream_id} no encontrado. Intente de nuevo.")
            return

        self.stream_index = row_index
        self.query_one("#placeholder", Static).update(f"▶ Reproduciendo: {self.current_stream['nombre']}")
        self.update_table_highlight()

        if self.current_stream['tipo'] == "stream":
            try:
                self.player = vlc.MediaPlayer(self.current_stream['link'])
                self.player.play()
            except Exception as e:
                logger.error(f"play_selected: Error al inicializar o reproducir stream VLC: {e}", exc_info=True)
                self.query_one("#placeholder", Static).update("Error en la reproducción de stream. Verifique VLC.")
        else:
            def get_audio():
                try:
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'quiet': True,
                        'noplaylist': True,
                        'no_warnings': True,
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(self.current_stream['link'], download=False)
                        url = info['url']
                    
                    self.player = vlc.MediaPlayer(url)
                    self.player.play()
                except yt_dlp.utils.DownloadError as e:
                    logger.error(f"get_audio: Error de descarga con yt-dlp: {e}", exc_info=True)
                    self.app.call_from_thread(self.query_one("#placeholder", Static).update, "Error: Problema al obtener audio de YouTube. Enlace no válido o yt-dlp.")
                except Exception as e:
                    logger.error(f"get_audio: Error general en el hilo de reproducción de yt-dlp: {e}", exc_info=True)
                    self.app.call_from_thread(self.query_one("#placeholder", Static).update, "Error inesperado al reproducir YouTube.")

            threading.Thread(target=get_audio, daemon=True).start()
            self.query_one("#placeholder", Static).update(f"Cargando: {self.current_stream['nombre']}...")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        now = time.time()
        if now - self.last_click_time < 0.5:
            self.play_selected(event.cursor_row)
        self.last_click_time = now

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "stop":
            if self.player:
                self.player.stop()
                self.query_one("#placeholder", Static).update("Seleccione un stream para reproducir")
                self.current_stream = None
                self.update_table_highlight()
        elif event.button.id == "next":
            if self.streams:
                self.stream_index = (self.stream_index + 1) % len(self.streams)
                self.play_selected(self.stream_index)
            else:
                logger.warning("on_button_pressed: No hay streams para pasar al siguiente.")
        elif event.button.id == "prev":
            if self.streams:
                self.stream_index = (self.stream_index - 1 + len(self.streams)) % len(self.streams)
                self.play_selected(self.stream_index)
            else:
                logger.warning("on_button_pressed: No hay streams para retroceder.")
        elif event.button.id == "volume":
            if self.player:
                vol = self.player.audio_get_volume()
                new_vol = 100 if vol < 100 else 30 
                self.player.audio_set_volume(new_vol)
            else:
                logger.warning("on_button_pressed: No hay reproductor activo para cambiar el volumen.")
