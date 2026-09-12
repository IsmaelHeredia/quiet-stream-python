#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import asyncio
import httpx
import yt_dlp
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, Button, Label, SelectionList
from textual.widgets.selection_list import Selection
from textual.screen import ModalScreen
from textual import work

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

class StreamValidationModal(ModalScreen[list[dict]]):

    CSS = """
    StreamValidationModal {
        background: $surface;
        border: round $primary;
        width: 90;
        height: 30;
        padding: 1;
    }
    StreamValidationModal > Static {
        width: 100%;
        content-align: center middle;
        text-style: bold;
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
        margin-top: 0;
        margin-bottom: 1;
        text-style: italic;
    }
    StreamValidationModal #broken_list {
        width: 100%;
        height: 1fr;
        min-height: 8;
        border: solid $primary;
        display: none;
    }
    StreamValidationModal #broken_list.-visible {
        display: block;
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
    StreamValidationModal Button:focus {
        text-style: bold;
    }
    """

    def __init__(self, streams_to_validate: list[dict]):
        super().__init__()
        self.streams_to_validate = streams_to_validate
        self.broken_streams: list[dict] = []
        self._cancelled = False
        self.validation_task = None
        self._broken_by_id: dict[int, dict] = {}

    def compose(self) -> ComposeResult:
        yield Static("Validando Streams...", id="modal_title", classes="modal-title")
        yield Label("Iniciando validación...", id="status_label")
        yield Label("", id="results_label")
        yield SelectionList[int](id="broken_list")
        yield Horizontal(
            Button("Detener", id="stop", variant="error"),
            Button(
                "Eliminar seleccionados",
                id="delete_selected",
                variant="error",
                disabled=True,
            ),
            Button("Cerrar", id="close", variant="primary", disabled=True),
        )

    def on_mount(self) -> None:
        self.validation_task = self.run_validation()

    def _show_broken_list(self) -> None:
        selection_list = self.query_one("#broken_list", SelectionList)
        selection_list.clear_options()
        self._broken_by_id.clear()

        for stream in self.broken_streams:
            sid = stream.get("id")
            if sid is None:
                continue
            sid = int(sid)
            self._broken_by_id[sid] = stream
            name = stream.get("nombre", "N/A")
            link = stream.get("link", "")
            short_link = link if len(link) <= 40 else link[:37] + "..."
            prompt = f"{name}  —  {short_link}"
            selection_list.add_option(Selection(prompt, sid, True))

        if self.broken_streams:
            selection_list.add_class("-visible")
            selection_list.focus()
            self.query_one("#delete_selected", Button).disabled = False
        else:
            selection_list.remove_class("-visible")
            self.query_one("#delete_selected", Button).disabled = True

    def _get_selected_broken(self) -> list[dict]:
        selection_list = self.query_one("#broken_list", SelectionList)
        selected_ids = selection_list.selected
        return [
            self._broken_by_id[sid]
            for sid in selected_ids
            if sid in self._broken_by_id
        ]

    @work(exclusive=True, group="stream_validation")
    async def run_validation(self) -> None:
        status_label = self.query_one("#status_label", Label)
        results_label = self.query_one("#results_label", Label)
        close_button = self.query_one("#close", Button)
        stop_button = self.query_one("#stop", Button)
        delete_button = self.query_one("#delete_selected", Button)
        title = self.query_one("#modal_title", Static)

        close_button.disabled = True
        delete_button.disabled = True
        stop_button.disabled = False
        self._cancelled = False
        self.broken_streams = []

        total_streams = len(self.streams_to_validate)

        if total_streams == 0:
            status_label.update("No hay streams para validar")
            results_label.update("")
            stop_button.disabled = True
            close_button.disabled = False
            return

        for i, stream_data in enumerate(self.streams_to_validate):
            if self._cancelled:
                break

            stream_name = stream_data.get("nombre", "N/A")
            stream_link = stream_data.get("link", "")
            stream_tipo = stream_data.get("tipo", "stream")

            status_label.update(
                f"Validando: {stream_name} ({i + 1}/{total_streams})"
            )

            is_functional = await self.check_stream_link(stream_link, stream_tipo)
            if self._cancelled:
                break

            if not is_functional:
                self.broken_streams.append(stream_data)
                logger.warning(
                    f"Stream no funcional: {stream_name} - {stream_link}"
                )
            else:
                logger.info(
                    f"Stream funcional: {stream_name} - {stream_link}"
                )

            await asyncio.sleep(0.01)

        stop_button.disabled = True
        close_button.disabled = False

        if self._cancelled:
            title.update("Validación detenida")
            status_label.update("Validación detenida por el usuario")
            results_label.update(
                f"{len(self.broken_streams)} no funcionales detectados. "
                "Marcá los que querés eliminar."
            )
        else:
            title.update("Validación completada")
            status_label.update("Validación completada")
            if self.broken_streams:
                results_label.update(
                    f"{len(self.broken_streams)} de {total_streams} no funcionales. "
                    "Desmarcá los que querés conservar."
                )
            else:
                results_label.update("Todos los streams son funcionales")

        self._show_broken_list()

    def _check_video_with_ytdlp(self, url: str) -> bool:
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
            "socket_timeout": 20,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if not info:
                return False
            if info.get("url"):
                return True
            formats = info.get("formats") or []
            for fmt in formats:
                if fmt.get("url") and (
                    fmt.get("acodec") not in (None, "none")
                    or fmt.get("vcodec") in (None, "none")
                    or "audio" in (fmt.get("format") or "").lower()
                ):
                    return True
            return bool(formats)
        except Exception as e:
            logger.error(f"yt-dlp validación falló para {url}: {e}")
            return False

    async def check_stream_http(self, url: str, timeout: float) -> bool:
        headers = {
            "User-Agent": USER_AGENT,
            "Icy-MetaData": "1",
            "Accept": "*/*",
            "Connection": "close",
        }

        try:
            async with httpx.AsyncClient(
                headers=headers,
                follow_redirects=True,
                timeout=timeout,
            ) as client:
                async with client.stream("GET", url) as response:
                    code = response.status_code

                    if code == 404 or code >= 500:
                        return False

                    try:
                        async for chunk in response.aiter_bytes(chunk_size=4096):
                            if chunk:
                                return True
                            break
                    except Exception:
                        return 200 <= code < 400

                    if 200 <= code < 400:
                        return True
                    if code in (401, 403, 405):
                        return True

                    return False

        except httpx.TimeoutException:
            logger.error(f"Timeout al validar URL ({timeout}s): {url}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Error de conexión al validar URL {url}: {e}")
            return False
        except Exception as e:
            logger.error(
                f"Error inesperado al validar URL {url}: {e}", exc_info=True
            )
            return False

    async def check_stream_link(self, url: str, tipo: str = "stream") -> bool:
        if not url:
            return False

        is_video = (tipo or "stream").lower() == "video"

        if is_video:
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(self._check_video_with_ytdlp, url),
                    timeout=25.0,
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout yt-dlp (25s) al validar video: {url}")
                return False
            except Exception as e:
                logger.error(f"Error validando video {url}: {e}", exc_info=True)
                return False

        return await self.check_stream_http(url, timeout=15.0)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "stop":
            self._cancelled = True
            self.query_one("#status_label", Label).update("Deteniendo...")
            event.button.disabled = True

        elif event.button.id == "delete_selected":
            selected = self._get_selected_broken()
            if not selected:
                self.notify(
                    "No hay streams seleccionados para eliminar",
                    severity="warning",
                )
                return
            self.dismiss(selected)

        elif event.button.id == "close":
            self._cancelled = True
            if self.validation_task and not self.validation_task.is_finished:
                self.validation_task.cancel()
            self.dismiss([])