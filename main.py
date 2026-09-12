#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Quiet Stream 1.0
# Written by Ismael Heredia

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Footer, Button, Static
from textual.theme import Theme
from views.admin_screen import AdminScreen
from views.player_screen import PlayerScreen
from views.about_screen import AboutScreen
from views.help_screen import HelpScreen

from database.models import create_db_and_tables
from database.seed import seed_data

import logging
from utils.config_manager import ENABLE_DEBUG_LOGGING, CURRENT_THEME, save_theme

logger = logging.getLogger(__name__)

GRUVBOX_LIGHT = Theme(
    name="gruvbox-light",
    primary="#076678",
    secondary="#427b58",
    warning="#b57614",
    error="#9d0006",
    success="#79740e",
    accent="#af3a03",
    foreground="#3c3836",
    background="#fbf1c7",
    surface="#ebdbb2",
    panel="#d5c4a1",
    dark=False,
    variables={
        "block-cursor-foreground": "#fbf1c7",
        "block-cursor-background": "#98971a",
        "input-selection-background": "#98971a50",
        "button-color-foreground": "#fbf1c7",
    },
)

class StreamPlayerApp(App):
    CSS_PATH = "static/style.css"
    TITLE = "Quiet Stream"

    BINDINGS = [
        ("ctrl+t", "toggle_theme", "Tema"),
    ]

    def on_mount(self):
        self.register_theme(GRUVBOX_LIGHT)

        saved_theme = (
            CURRENT_THEME
            if CURRENT_THEME in ("gruvbox-light", "gruvbox")
            else "gruvbox-light"
        )
        self.theme = saved_theme

        try:
            create_db_and_tables()
            seed_data()
        except Exception as e:
            logger.critical(f"Error inicial: {e}")
            self.exit(message=f"Error crítico: {e}")
        self.set_focus(None)

    def action_toggle_theme(self) -> None:
        if self.theme == "gruvbox-light":
            new_theme = "gruvbox"
        else:
            new_theme = "gruvbox-light"
        self.theme = new_theme
        save_theme(new_theme)

    def compose(self) -> ComposeResult:
        yield Static("Quiet Stream", id="screen_title")
        with VerticalScroll(id="main_content_area"):
            yield Container(
                Button("Gestor de Streams", id="admin_btn", variant="primary"),
                Button("Reproductor", id="player_btn", variant="success"),
                Button("Acerca de", id="about_btn", variant="warning"),
                Button("Ayuda", id="help_btn", variant="default"),
                Button("Salir", id="exit_btn", variant="error"),
                id="botonera",
            )
            yield Static("Desarrollado por: Ismael Heredia", id="author_info")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "admin_btn":
            self.push_screen(AdminScreen())
        elif button_id == "player_btn":
            self.push_screen(PlayerScreen())
        elif button_id == "about_btn":
            self.push_screen(AboutScreen())
        elif button_id == "help_btn":
            self.push_screen(HelpScreen())
        elif button_id == "exit_btn":
            self.exit()

if __name__ == "__main__":
    app = StreamPlayerApp()
    app.run()