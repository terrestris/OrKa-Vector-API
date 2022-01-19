import json
import uuid
from flask import Blueprint, request, abort, current_app

from orka_vector_api import db
from orka_vector_api.enums import Status
from orka_vector_api.exceptions.orka import OrkaException
from orka_vector_api.helper import create_job, update_job, get_job_by_id, delete_job_by_id, \
    delete_geopackage, create_gpkg_threaded, threads_available, bbox_size_allowed

jobs = Blueprint('jobs', __name__, url_prefix='/jobs')


@jobs.route('/', methods=['POST'])
def add_job():
    """Add new job.
    Add a new job and trigger the creation of a geopackage containing only
    the geometries that intersect the provided bounding box.
    ---
    parameters:
      - name: body
        in: body
        description: The bounding box
        schema:
          $ref: '#/definitions/PostBody'
        required: true
    responses:
      400:
        description: BBOX invalid, or BBOX area too big, or server busy.
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
          example:
            success: False
            message: "Invalid BBOX"
      201:
        description: The success response.
        schema:
          $ref: '#/definitions/PostResponse'
    definitions:
      PostResponse:
        type: object
        properties:
          success:
            type: boolean
            description: True, if the job was successfully created. False otherwise.
          job_id:
            type: integer
            description: The id of the created job.
        example:
          success: True
          job_id: 1
      PostBody:
        type: object
        properties:
          bbox:
            type: array
            description: The Bounding Box in EPSG 4326 with [xMin, yMin, xMax, yMax].
            items:
              type: number
          layers:
            type: array
            description: List of layers that should be included in the download. Will include all layers, if omitted.
            items:
              type: string
            required: false
        example:
          bbox:
            - 12.770159825707431
            - 53.38672734467538
            - 12.81314093379179
            - 53.40407138102892
    """
    post_body = request.json

    # bbox is always in 4326
    bbox = post_body.get('bbox')
    if bbox is None or not len(bbox) == 4:
        current_app.logger.info('Could not add job. Invalid BBOX.')
        return json.dumps({'success': False, 'message': Status.BBOX_INVALID.value}), 400, {'ContentType': 'application/json'}

    layers = post_body.get('layers')
    if layers is not None and len(layers) == 0:
        current_app.logger.info('Could not add job. Empty list of layers.')
        return json.dumps({'success': False, 'message': Status.LAYERS_INVALID.value}), 400, {'ContentType': 'application/json'}

    conn = db.pool.getconn()
    try:
        data_id = str(uuid.uuid4())

        if not bbox_size_allowed(conn, current_app, bbox):
            current_app.logger.info('Could not add job. BBOX size not allowed.')
            raise OrkaException(Status.BBOX_TOO_BIG.value)

        if not threads_available(conn, current_app):
            current_app.logger.info('Could not add job. No free threads available.')
            raise OrkaException(Status.NO_THREADS_AVAILABLE.value)

        job_id = create_job(conn, current_app, bbox, data_id, layers=layers)
        current_app.logger.debug(f'Added job with id {job_id}')
        update_job(job_id, conn, current_app, status=Status.RUNNING.value)

        current_app.logger.debug(f'Creating gpkg for job {job_id}')
        create_gpkg_threaded(current_app, job_id, data_id, bbox, layers=layers)
        response = json.dumps({'success': True, 'job_id': job_id}), 201, {'ContentType': 'application/json'}
    except OrkaException as e:
        response = json.dumps({'success': False, 'message': str(e)}), 400, {'ContentType': 'application/json'}
    except Exception as e:
        current_app.logger.info(f'Error adding job. {e}')
        response = json.dumps({'success': False}), 400, {'ContentType': 'application/json'}
    finally:
        db.pool.putconn(conn)

    return response


@jobs.route('/<int:job_id>', methods=['GET'])
def get_job(job_id):
    """Get the job.
    ---
    parameters:
      - name: job_id
        in: path
        description: The id of the job.
        type: integer
        required: true
    responses:
      200:
        description: The requested job.
        schema:
          $ref: '#/definitions/Job'
      404:
        description: Job not found.
    definitions:
      Job:
        description: The Job object.
        type: object
        properties:
          id:
            type: integer
            description: The id of the job
          minx:
            type: number
            description: The minX value of the provided Bounding Box.
          miny:
            type: number
            description: The minY value of the provided Bounding Box.
          maxx:
            type: number
            description: The maxX value of the provided Bounding Box.
          maxy:
            type: number
            description: The maxY value of the provided Bounding Box.
          status:
            $ref: '#/definitions/JobStatus'
          layers:
            type: array
            items:
              type: str
            description: The list of layers that are contained in the data package. If null, all layers are included.
      JobStatus:
        description: The status of a Job.
        type: string
        enum:
          - INIT
          - RUNNING
          - CREATED
          - ERROR
          - TIMEOUT
          - BBOX_TOO_BIG
          - BBOX_INVALID
          - NO_THREADS_AVAILABLE
    """
    conn = db.pool.getconn()
    try:
        job = get_job_by_id(job_id, conn, current_app)
        if job is None:
            current_app.logger.info(f'Could not get job {job_id}. Job not found.')
            raise OrkaException("Job not found.")
        if job['status'] != Status.CREATED.value:
            job.pop('data_id')
        response = job
    except OrkaException as e:
        response = '', 404
    except Exception as e:
        current_app.logger.info(f'Error getting job. {e}')
        response = '', 500
    finally:
        db.pool.putconn(conn)
    return response


@jobs.route('/<int:job_id>', methods=['PUT'])
def put_job(job_id):
    """Update a job.
    ---
    parameters:
      - name: job_id
        in: path
        description: The id of the job.
        type: integer
        required: true
      - name: body
        in: body
        description: The changed job.
        required: true
        schema:
          $ref: '#/definitions/Job'
    responses:
      201:
        description: Successfully updated.
        schema:
          $ref: '#/definitions/PutResponse'
      404:
        description: Job not found.
    definitions:
      PutResponse:
        type: object
        properties:
          success:
            type: boolean
            description: The success state of the request.
    """
    post_body = request.json
    conn = db.pool.getconn()
    try:
        job = get_job_by_id(job_id, conn, current_app)
        if job is None:
            current_app.logger.info(f'Could not update job {job_id}. Job not found.')
            raise OrkaException("Job not found.")
        update_job(job_id, conn, current_app, **post_body)
        response = json.dumps({'success': True}), 201, {'ContentType': 'application/json'}
    except OrkaException:
        response = json.dumps({'success': False}), 404, {'ContentType': 'application/json'}
    except Exception as e:
        current_app.logger.info(f'Error updating job. {e}')
        response = json.dumps({'success': False}), 500, {'ContentType': 'application/json'}
    finally:
        db.pool.putconn(conn)

    return response


@jobs.route('/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    """Delete a job.
    Deletes a job and the corresponding geopackage file.
    ---
    parameters:
      - name: job_id
        in: path
        description: The id of the job.
        type: integer
        required: true
    responses:
      200:
        description: Successfully deleted.
        schema:
          $ref: '#/definitions/DeleteResponse'
      404:
        description: Job not found.
        schema:
          $ref: '#/definitions/DeleteResponse'
      400:
        description: Job could not be deleted.
        schema:
          $ref: '#/definitions/DeleteResponse'
    definitions:
      DeleteResponse:
        type: object
        properties:
          success:
            type: boolean
            description: True, if deleted successfully. False otherwise.
    """
    conn = db.pool.getconn()
    try:
        job = get_job_by_id(job_id, conn, current_app)
        if job is None:
            current_app.logger.info(f'Could not delete job {job_id}. Job not found.')
            raise OrkaException("Job not found")

        deleted_gpkg = delete_geopackage(job.get('data_id'), conn, current_app)
        if not deleted_gpkg:
            current_app.logger.info(f'Could not delete gpkg for job {job_id}')

        deleted = delete_job_by_id(job_id, conn, current_app)
        if not deleted:
            current_app.logger.info(f'Could not delete job with id {job_id}')
            raise OrkaException('Could not delete job.')

        current_app.logger.debug(f'Deleted job with id {job_id}')
        response = json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
    except OrkaException as e:
        response = json.dumps({'success': False, 'message': str(e)}), 400, {'ContentType': 'application/json'}
    except Exception as e:
        current_app.logger.info(f'Error deleting job {e}')
        response = json.dumps({'success': False}), 500, {'ContentType': 'application/json'}
    finally:
        db.pool.putconn(conn)

    return response
