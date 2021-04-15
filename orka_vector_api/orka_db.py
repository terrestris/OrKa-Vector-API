from psycopg2.pool import ThreadedConnectionPool
from flask import _app_ctx_stack, current_app


class OrkaDB(object):
    def _init_(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('ORKA_DB_HOST', 'localhost')
        app.config.setdefault('ORKA_DB_PORT', 5432)
        app.config.setdefault('ORKA_DB_DATABASE', 'postgres')
        app.config.setdefault('ORKA_DB_MIN_CONNECTION', 1)
        app.config.setdefault('ORKA_DB_MAX_CONNECTION', 1)
        app.config.setdefault('ORKA_DB_SCHEMA', 'public')

        app.teardown_appcontext(self.teardown)

    def teardown(self, exception):
        pass

    def create_pool(self):
        return ThreadedConnectionPool(
            current_app.config['ORKA_DB_MIN_CONNECTION'],
            current_app.config['ORKA_DB_MAX_CONNECTION'],
            host=current_app.config['ORKA_DB_HOST'],
            port=current_app.config['ORKA_DB_PORT'],
            database=current_app.config['ORKA_DB_DATABASE'],
            user=current_app.config['ORKA_DB_USER'],
            password=current_app.config['ORKA_DB_PASSWORD']
        )

    @property
    def pool(self):
        ctx = _app_ctx_stack.top
        if ctx is not None:
            if not hasattr(ctx, 'orka_db_pool'):
                ctx.orka_db_pool = self.create_pool()
            return ctx.orka_db_pool

