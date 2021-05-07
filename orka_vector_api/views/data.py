import os.path

from flask import Blueprint, current_app, abort, send_from_directory

from orka_vector_api import db
from orka_vector_api.helper import get_job_id_by_dataid

data = Blueprint('data', __name__, url_prefix='/data')


@data.route('/<uuid:data_id>', methods=['GET'])
def get_data(data_id):
    data_id_str = str(data_id)
    gpkg_path = current_app.config['ORKA_GPKG_PATH']
    filename = data_id_str + '.gpkg'

    conn = db.pool.getconn()

    # only return a file if it is related to an existing job
    job_id = get_job_id_by_dataid(data_id_str, conn, current_app)
    if job_id is None:
        current_app.logger.info(f'Could not provide download for {filename}. No corresponding job found.')
        abort(404)

    db.pool.putconn(conn)

    current_app.logger.debug(f'Provided download for {filename} of job {job_id}.')
    return send_from_directory(os.path.abspath(gpkg_path), filename,  mimetype='application/geopackage+sqlite3')


@data.route('/styles', methods=['GET'])
def get_styles_zip():
    style_path = current_app.config['ORKA_STYLE_PATH']
    file_name = current_app.config['ORKA_STYLE_FILE']

    current_app.logger.debug(f'Provided download for style file {file_name}.')
    return send_from_directory(os.path.abspath(style_path), file_name, mimetype='application/zip')
