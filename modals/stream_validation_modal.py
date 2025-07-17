#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import asyncio
import httpx
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, Button, ProgressBar, Label
from textual.screen import ModalScreen
from textual import on, work

logger = logging.getLogger(__name__)

class StreamValidationModal(ModalScreen[list[dict]]):

    CSS = """
    StreamValidationModal {
        background: $surface;
        border: round $primary;
        width: 80;
        height: 25;
        padding: 1;
    }
    StreamValidationModal > Static {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }
    StreamValidationModal #progress_bar {
        width: 100%;
        margin-top: 1;
        margin-bottom: 1;
    }
    StreamValidationModal #status_label {
        width: 100%;
        content-align: center middle;
        margin-bottom: 1;
    }
    StreamValidationModal #results_label {
        width: 100%;
        content-align: center middle;
        margin-top: 1;
        text-style: italic;
    }
    StreamValidationModal Horizontal {
        height: auto;
        margin-top: 1;
        align: center middle;
    }
    StreamValidationModal Button {
        margin-left: 1;
        margin-right: 1;
    }
    """

    def __init__(self, streams_to_validate: list[dict]):
        super().__init__()
        self.streams_to_validate = streams_to_validate
        self.broken_streams: list[dict] = []
        self.validation_task = None

    def compose(self) -> ComposeResult:
        yield Static("Validando Streams...", classes="modal-title")
        yield Label("Iniciando validación...", id="status_label")
        yield Label("", id="results_label")
        yield Horizontal(
            Button("🚪 Cerrar", id="close", variant="primary")
        )

    def on_mount(self) -> None:
        self.validation_task = self.run_validation()

    @work(exclusive=True, group="stream_validation")
    async def run_validation(self) -> None:
        status_label = self.query_one("#status_label", Label)
        results_label = self.query_one("#results_label", Label)
        close_button = self.query_one("#close", Button)
        close_button.disabled = True

        total_streams = len(self.streams_to_validate)
        self.broken_streams = []

        if total_streams == 0:
            status_label.update("No hay streams para validar")
            close_button.disabled = False
            self.dismiss(self.broken_streams)
            return

        for i, stream_data in enumerate(self.streams_to_validate):
            stream_name = stream_data.get("nombre", "N/A")
            stream_link = stream_data.get("link", "")

            status_label.update(f"Validando: {stream_name} ({i + 1}/{total_streams})")

            is_functional = await self.check_stream_link(stream_link)
            if not is_functional:
                self.broken_streams.append(stream_data)
                logger.warning(f"Stream no funcional: {stream_name} - {stream_link}")
            else:
                logger.info(f"Stream funcional: {stream_name} - {stream_link}")

            await asyncio.sleep(0.01)

        status_label.update("Validación completada")
        results_label.update(f"Resultado: {len(self.broken_streams)} de {total_streams} streams no funcionales")
        close_button.disabled = False
        self.dismiss(self.broken_streams)

    async def check_stream_link(self, url: str) -> bool:
        if not url:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.head(url, timeout=5)
            return 200 <= response.status_code < 400
        except httpx.TimeoutException:
            logger.error(f"Timeout al validar URL: {url}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Error de conexión al validar URL {url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al validar URL {url}: {e}", exc_info=True)
            return False

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            if self.validation_task and not self.validation_task.is_finished:
                self.validation_task.cancel()
            self.dismiss(self.broken_streams)