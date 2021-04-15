import json

from flask import Blueprint, send_file, current_app, abort

from orka_vector_api import db
from orka_vector_api.helper import get_job_by_id, get_job_id_by_dataid

data = Blueprint('data', __name__, url_prefix='/data')


@data.route('/<uuid:data_id>', methods=['GET'])
def get_data(data_id):
    # TODO get absolute path to folder where gpkgs are stored
    # TODO provide downloaded gpkg
    data_id_str = str(data_id)
    filename = data_id_str + '.gpkg'
    gpkg_abs_path = ''

    conn = db.pool.getconn()

    job_id = get_job_id_by_dataid(data_id_str, conn, current_app)
    if job_id is None:
        abort(404)

    job = get_job_by_id(job_id, conn, current_app)

    db.pool.putconn(conn)
    # TODO check if file exists, if yes, then provide it, otherwise 404

    # return send_file(gpkg_abs_path, attachment_filename=filename)
    return json.dumps({'success': True})
