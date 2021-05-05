from enum import Enum


class Status(Enum):
    INIT = 'INIT'
    RUNNING = 'RUNNING'
    CREATED = 'CREATED'
    ERROR = 'ERROR'
    TIMEOUT = 'TIMEOUT'
