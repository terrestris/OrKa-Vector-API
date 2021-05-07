from logging import Formatter
from logging.handlers import RotatingFileHandler


def setup_file_logger(**kwargs):
    file_handler = RotatingFileHandler(
        kwargs.get('logfile', 'orka.log'),
        maxBytes=1024
    )
    file_handler.setFormatter(Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    return file_handler
