import os.path

from flask import Blueprint, current_app, abort, send_from_directory

from orka_vector_api import db
from orka_vector_api.exceptions.orka import OrkaException
from orka_vector_api.helper import get_job_id_by_dataid

data = Blueprint('data', __name__, url_prefix='/data')


@data.route('/<uuid:data_id>', methods=['GET'])
def get_data(data_id):
    """Get a single geopackage.
    Get the geopackage with given uuid as filename.
    ---
    parameters:
      - name: data_id
        description: The id of the geopackage to download. The id is provided via the corresponding job.
        in: path
        type: string
        format: uuid
        required: true
    responses:
      200:
        description: The geopackage file.
    produces:
      - application/geopackage+sqlite3
    """
    data_id_str = str(data_id)
    gpkg_path = current_app.config['ORKA_GPKG_PATH']
    filename = data_id_str + '.gpkg'

    conn = db.pool.getconn()
    try:
        # only return a file if it is related to an existing job
        job_id = get_job_id_by_dataid(data_id_str, conn, current_app)
        if job_id is None:
            raise OrkaException('Corresponding job not found.')
        current_app.logger.debug(f'Provided download for {filename} of job {job_id}.')
        response = send_from_directory(os.path.abspath(gpkg_path), filename, mimetype='application/geopackage+sqlite3')
    except OrkaException as e:
        current_app.logger.info(f'Could not provide download for {filename}. No corresponding job found.')
        response = '', 404
    except Exception as e:
        current_app.logger.info(f'Error downloading gpkg. {e}')
        response = '', 404
    finally:
        db.pool.putconn(conn)

    return response


@data.route('/styles', methods=['GET'])
def get_styles_zip():
    """Get the style files, symbols, etc.
    Get all style files as a single .zip file.
    ---
    responses:
      200:
        description: The .zip file containing all styles, etc.
    produces:
      - application/zip
    """
    style_path = current_app.config['ORKA_STYLE_PATH']
    file_name = current_app.config['ORKA_STYLE_FILE']

    current_app.logger.debug(f'Provided download for style file {file_name}.')
    return send_from_directory(os.path.abspath(style_path), file_name, mimetype='application/zip')


@data.route('/groups', methods=['GET'])
def get_layer_groups():
    """Get the configuration of layer groups.
    ---
    responses:
      200:
        description: The layer group configuration json file.
    produces:
      - application/json
    """
    style_path = current_app.config['ORKA_STYLE_PATH']
    file_name = current_app.config['ORKA_LAYER_GROUPS_FILE']

    current_app.logger.debug(f'Provided download for layer groups config file {file_name}.')
    return send_from_directory(os.path.abspath(style_path), file_name, mimetype='application/json')
