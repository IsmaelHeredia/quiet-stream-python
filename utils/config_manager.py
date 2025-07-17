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
        except configparser.Error as e:
            config['DEBUGGING'] = {'ENABLE_DEBUG_LOGGING': 'true'}
    else:
        config['DEBUGGING'] = {'ENABLE_DEBUG_LOGGING': 'true'}
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                config.write(f)
        except IOError as e:
            print(f"ERROR: Error al crear el archivo de configuración '{CONFIG_FILE}': {e}.")
            
    return config

app_config = load_config()
ENABLE_DEBUG_LOGGING = app_config.getboolean('DEBUGGING', 'ENABLE_DEBUG_LOGGING', fallback=True)

def setup_logging():
    if ENABLE_DEBUG_LOGGING:
        effective_log_level = logging.DEBUG
    else:
        effective_log_level = logging.CRITICAL

    root_logger = logging.getLogger()

    if root_logger.handlers:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            if hasattr(handler, 'close'):
                handler.close()

    root_logger.setLevel(effective_log_level)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler('debug.log', encoding='utf-8')
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