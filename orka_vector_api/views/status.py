from flask import Blueprint

status = Blueprint('status', __name__, url_prefix='/status')


@status.route('/')
def get_status():
    return {
        'status': 'active'
    }
