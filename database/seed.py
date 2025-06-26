#!/usr/bin/env python
# -*- coding: utf-8 -*-

from database.models import Stream, get_session, create_db_and_tables
from sqlmodel import select
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DEFAULT_STREAMS = [
]

def seed_data():
    try:
        with get_session() as session:
            existing = session.exec(select(Stream)).first()
            if existing:
                logger.info("La base de datos ya contiene datos, omitiendo seed")
                return
                
            logger.info("Insertando datos iniciales...")
            for stream in DEFAULT_STREAMS:
                session.add(stream)
            session.commit()
            logger.info(f"Insertados {len(DEFAULT_STREAMS)} streams iniciales")
            
    except Exception as e:
        logger.error(f"Error en seed_data: {e}")
        raise