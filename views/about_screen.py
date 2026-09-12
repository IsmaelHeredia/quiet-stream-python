#!/usr/bin/env python
# -*- coding: utf-8 -*-

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Center
from textual.widgets import Static, Footer, Rule
from textual.screen import Screen


class AboutScreen(Screen):
    BINDINGS = [
        Binding("q", "app.pop_screen", "Volver", priority=True),
        Binding("escape", "app.pop_screen", "Volver", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Static("Acerca de", id="screen_title")
        with Vertical(id="main_content_area"):
            with Center():
                with Vertical(id="about_card"):
                    yield Static("QUIET STREAM", classes="about-name")
                    yield Static("1.0", classes="about-version")
                    yield Rule(classes="about-rule")
                    yield Static(
                        "Gestor y reproductor de streams de audio y\n"
                        "video para la terminal.",
                        classes="about-desc",
                    )
                    yield Static(
                        "Organizá tu biblioteca, importá y exportá en JSON,\n"
                        "validá tus enlaces y reproducí con VLC y yt-dlp,\n"
                        "todo sin salir de la consola.",
                        classes="about-desc",
                    )
                    yield Rule(classes="about-rule")
                    yield Static("AUTOR", classes="about-label")
                    yield Static("Ismael Heredia", classes="about-author")
                    yield Static(
                        "Textual  ·  SQLModel  ·  Python",
                        classes="about-tech",
                    )
        yield Footer()