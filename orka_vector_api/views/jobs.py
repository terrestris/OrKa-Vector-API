import json
import uuid
from flask import Blueprint, request, abort, current_app

from orka_vector_api import db
from orka_vector_api.enums import Status
from orka_vector_api.helper import create_job, update_job, get_job_by_id, delete_job_by_id, \
    delete_geopackage, create_gpkg_threaded, threads_available, bbox_size_allowed

jobs = Blueprint('jobs', __name__, url_prefix='/jobs')


@jobs.route('/', methods=['POST'])
def add_job():
    if request.content_type == 'application/json':
        post_body = request.json

        # bbox is always in 4326
        bbox = post_body.get('bbox')
        if bbox is None or not len(bbox) == 4:
            current_app.logger.info('Could not add job. Invalid BBOX.')
            abort(400)

        transform_to = post_body.get('transform_to')

        conn = db.pool.getconn()
        data_id = str(uuid.uuid4())

        if not bbox_size_allowed(conn, current_app, bbox):
            current_app.logger.info('Could not add job. BBOX size not allowed.')
            abort(400)

        if not threads_available(conn, current_app):
            current_app.logger.info('Could not add job. No free threads available.')
            return json.dumps({'success': False}), 400, {'ContentType': 'application/json'}

        job_id = create_job(conn, current_app, bbox, data_id, transform_to=transform_to)
        current_app.logger.debug(f'Added job with id {job_id}')
        update_job(job_id, conn, current_app, status=Status.RUNNING.value)

        current_app.logger.debug(f'Creating gpkg for job {job_id}')
        create_gpkg_threaded(current_app, request.base_url, job_id, data_id, bbox)

        db.pool.putconn(conn)
        return json.dumps({'success': True, 'job_id': job_id}), 201, {'ContentType': 'application/json'}
    else:
        abort(400)


@jobs.route('/<int:job_id>', methods=['GET'])
def get_job(job_id):
    conn = db.pool.getconn()
    job = get_job_by_id(job_id, conn, current_app)
    db.pool.putconn(conn)
    if job.get('status') != Status.CREATED.value:
        job.pop('data_id')

    return job


@jobs.route('/<int:job_id>', methods=['PUT'])
def put_job(job_id):
    post_body = request.json
    conn = db.pool.getconn()
    update_job(job_id, conn, current_app, **post_body)
    db.pool.putconn(conn)
    return json.dumps({'success': True}), 201, {'ContentType': 'application/json'}


@jobs.route('/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    conn = db.pool.getconn()
    job = get_job_by_id(job_id, conn, current_app)
    if job is None:
        current_app.logger.info(f'Could not delete job {job_id}. Job not found.')
        abort(400)

    deleted_gpkg = delete_geopackage(job.get('data_id'), conn, current_app)
    if not deleted_gpkg:
        current_app.logger.info(f'Could not delete gpkg for job {job_id}')

    deleted = delete_job_by_id(job_id, conn, current_app)
    db.pool.putconn(conn)
    if not deleted:
        current_app.logger.info(f'Could not delete job with id {job_id}')
        return json.dumps({'success': False}), 400, {'ContentType': 'application/json'}

    current_app.logger.debug(f'Deleted job with id {job_id}')

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
