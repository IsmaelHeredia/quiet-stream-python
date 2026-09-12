#!/usr/bin/env python
# -*- coding: utf-8 -*-

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Center, Container
from textual.widgets import Static, Footer, RichLog
from textual.screen import Screen


HELP_TEXT = """
[bold]Quiet Stream — Ayuda[/]

[bold $success]Menú principal[/]
  Gestor de Streams   Administra tu biblioteca de streams.
  Reproductor         Reproduce streams y videos.
  Acerca de           Información sobre el programa.
  Ayuda               Esta pantalla.
  Salir               Cierra la aplicación.

  [bold]Ctrl+T[/]  Cambia el tema (Gruvbox Light / Dark).
               La elección se recuerda entre sesiones.

[bold $success]Gestor de Streams[/]
  Busca por nombre (no distingue mayúsculas de minúsculas)
  y filtra por categoría con el selector.

  [bold]a[/]  Agregar    [bold]e[/]  Editar    [bold]d[/]  Eliminar
  [bold]i[/]  Importar JSON    [bold]x[/]  Exportar JSON
  [bold]v[/]  Validar enlaces (permite detener y seleccionar)
  [bold]q[/]  Volver

  Importar: carga un archivo JSON con una lista de objetos
  (nombre, link, categorías, tipo) y omite los duplicados.
  Validar: comprueba el estado de los enlaces; podés
  detener el proceso en cualquier momento, marcar cuáles
  eliminar y confirmar los cambios.

[bold $success]Reproductor[/]
  Doble clic sobre una fila para reproducirla.
  Un solo clic mueve el cursor sin iniciar la reproducción;
  la pista que está sonando se resalta en verde.
  Podés buscar por nombre y filtrar por categoría.

  [bold]a[/]  Anterior   [bold]s[/]  Detener
  [bold]d[/]  Siguiente  [bold]v[/]  Volumen (30% / 100%)
  [bold]q[/]  Volver

  Tipos de pista: Stream (URL directa) o Video (vía yt-dlp).
  Al terminar un video, la reproducción se reinicia
  automáticamente.

[bold $success]Consejos[/]
  Los atajos de teclado funcionan incluso con el foco
  puesto en el buscador.
  La tabla se ajusta automáticamente al redimensionar
  la terminal.
  Los mensajes de VLC se silencian intencionalmente.
"""


class HelpScreen(Screen):
    BINDINGS = [
        Binding("q", "app.pop_screen", "Volver", priority=True),
        Binding("escape", "app.pop_screen", "Volver", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Static("Ayuda", id="screen_title")
        with Vertical(id="main_content_area"):
            with Center():
                with Container(id="help_card"):
                    yield RichLog(
                        id="help_log",
                        highlight=True,
                        markup=True,
                        auto_scroll=False,
                    )
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#help_log", RichLog)
        log.write(HELP_TEXT.strip())
        log.focus()