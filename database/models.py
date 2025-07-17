#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from sqlmodel import Field, SQLModel, create_engine, Session, select
from typing import Optional
from contextlib import contextmanager

import logging
from utils.config_manager import ENABLE_DEBUG_LOGGING

logger = logging.getLogger(__name__)

class Stream(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    link: str
    categorias: str
    tipo: str

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, '..', 'streams.db')
sqlite_url = f"sqlite:///{DB_PATH}"

engine = create_engine(
    sqlite_url,
    echo=False,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)

def create_db_and_tables():
    logger.info("Creando tablas...")
    SQLModel.metadata.create_all(engine)
    logger.info("Tablas creadas correctamente")

@contextmanager
def get_session():
    session = Session(engine)
    try:
        logger.debug("Iniciando sesión de BD...")
        yield session
        session.commit()
        logger.debug("Cambios confirmados en BD.")
    except Exception as e:
        session.rollback()
        logger.error(f"Error en BD: {e}", exc_info=True)
        raise
    finally:
        session.close()
        logger.debug("Sesión de BD cerrada.")
