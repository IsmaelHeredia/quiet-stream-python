#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser
from pathlib import Path
import logging
import sys

CONFIG_FILE = Path("config.ini")


def load_config():
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        try:
            config.read(CONFIG_FILE)
        except configparser.Error:
            pass

    if "DEBUGGING" not in config:
        config["DEBUGGING"] = {}
    if "UI" not in config:
        config["UI"] = {}

    if "ENABLE_DEBUG_LOGGING" not in config["DEBUGGING"]:
        config["DEBUGGING"]["ENABLE_DEBUG_LOGGING"] = "false"

    if "THEME" not in config["UI"]:
        config["UI"]["THEME"] = "gruvbox-light"

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            config.write(f)
    except IOError as e:
        print(f"ERROR: No se pudo escribir el archivo de configuración '{CONFIG_FILE}': {e}")

    return config

app_config = load_config()

ENABLE_DEBUG_LOGGING = app_config.getboolean("DEBUGGING", "ENABLE_DEBUG_LOGGING", fallback=False)
CURRENT_THEME = app_config.get("UI", "THEME", fallback="gruvbox-light")


def save_theme(theme_name: str) -> None:
    try:
        config = load_config()
        config["UI"]["THEME"] = theme_name
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            config.write(f)
    except Exception as e:
        logging.getLogger(__name__).error(f"Error al guardar el tema: {e}")


def setup_logging():
    if ENABLE_DEBUG_LOGGING:
        effective_log_level = logging.DEBUG
    else:
        effective_log_level = logging.CRITICAL

    root_logger = logging.getLogger()

    if root_logger.handlers:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            if hasattr(handler, "close"):
                handler.close()

    root_logger.setLevel(effective_log_level)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler("debug.log", encoding="utf-8")
    file_handler.setLevel(effective_log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(effective_log_level)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    return logging.getLogger(__name__)

initial_logger = setup_logging()
initial_logger.info("Sistema de logging inicializado.")