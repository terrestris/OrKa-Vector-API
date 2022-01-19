__version__ = '0.1.0'

import os

from flasgger import Swagger
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from orka_vector_api import logging_config
from orka_vector_api.logging_config import setup_file_logger
from orka_vector_api.orka_db import OrkaDB
from orka_vector_api.swagger_config import get_swagger_config

db = OrkaDB()
swagger = Swagger(template=get_swagger_config())


def create_app(test_config=None):
    app_kwargs = {
        'instance_relative_config': True
    }
    if os.environ.get('FLASK_ENV', '') != 'development':
        app_kwargs['instance_path'] = f'/var/{__name__}'

    # create and configure the app
    app = Flask(__name__, **app_kwargs)
    app.config.from_mapping(
        SECRET_KEY='dev'
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    file_logger = setup_file_logger(logfile=app.config['ORKA_LOG_FILE'])
    app.logger.addHandler(file_logger)
    app.logger.setLevel(app.config['ORKA_LOG_LEVEL'])

    db.init_app(app)
    swagger.init_app(app)

    from orka_vector_api.views.status import status
    from orka_vector_api.views.jobs import jobs
    from orka_vector_api.views.data import data

    app.register_blueprint(status)
    app.register_blueprint(jobs)
    app.register_blueprint(data)

    if app.config['ENV'] == 'development':
        return app

    return ProxyFix(app, x_for=1, x_prefix=1)
