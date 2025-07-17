#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Quiet Stream 1.0
# pip install textual
# pip install sqlmodel
# Written by Ismael Heredia

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer, Button, Static
from views.admin_screen import AdminScreen
from views.player_screen import PlayerScreen

from database.models import create_db_and_tables
from database.seed import seed_data

import logging
from utils.config_manager import ENABLE_DEBUG_LOGGING

logger = logging.getLogger(__name__)

class StreamPlayerApp(App):
    CSS_PATH = "static/style.css"
    TITLE = "Quiet Stream"

    def on_mount(self):
        try:
            create_db_and_tables()
            seed_data()
        except Exception as e:
            logger.critical(f"Error inicial: {e}")
            self.exit(message=f"Error crítico: {e}")
        self.set_focus(None) 

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Container(
                Button("💻 Gestor de Streams", id="admin_btn", variant="primary"),
                Button("🎵 Reproductor", id="player_btn", variant="success"),
                Button("🛑 Salir", id="exit_btn", variant="error"),
                id="botonera"
            ),
            Static("Desarrollado por: Ismael Heredia", id="author_info"),
            id="main_content_area"
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "admin_btn":
            self.push_screen(AdminScreen())
        elif button_id == "player_btn":
            self.push_screen(PlayerScreen())
        elif button_id == "exit_btn":
            self.exit()

if __name__ == "__main__":
    app = StreamPlayerApp()
    app.run()