from logging import Formatter
from logging.handlers import RotatingFileHandler


def setup_file_logger(logfile='orka.log'):
    file_handler = RotatingFileHandler(
        logfile,
        maxBytes=1024
    )
    file_handler.setFormatter(Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    return file_handler
