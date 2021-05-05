import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from orka_vector_api.orka_db import OrkaDB

db = OrkaDB()


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
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

    db.init_app(app)

    from orka_vector_api.views.status import status
    from orka_vector_api.views.jobs import jobs
    from orka_vector_api.views.data import data

    app.register_blueprint(status)
    app.register_blueprint(jobs)
    app.register_blueprint(data)

    if app.config['ENV'] == 'development':
        return app

    return ProxyFix(app, x_for=1, x_prefix=1)
