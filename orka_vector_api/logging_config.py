import logging
from logging import Formatter
from logging.handlers import RotatingFileHandler


def setup_file_logger(logfile='orka.log', loglevel: str = None):
    file_handler = RotatingFileHandler(
        logfile,
        maxBytes=1024
    )
    file_handler.setFormatter(Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    log_level = logging.WARNING

    if loglevel is not None:
        if loglevel.upper() == 'CRITICAL':
            log_level = logging.CRITICAL
        elif loglevel.upper() == 'ERROR':
            log_level = logging.ERROR
        elif loglevel.upper() == 'WARNING':
            log_level = logging.WARNING
        elif loglevel.upper() == 'INFO':
            log_level = logging.INFO
        elif loglevel.upper() == 'DEBUG':
            log_level = logging.DEBUG
        elif loglevel.upper() == 'NOTSET':
            log_level = logging.NOTSET

    file_handler.setLevel(log_level)
    return file_handler
