import json
import uuid
from flask import Blueprint, request, abort, current_app

from orka_vector_api import db
from orka_vector_api.helper import create_job, update_job, get_job_by_id, delete_job_by_id, \
    get_layers_from_file, get_geopackage_sql, delete_geopackage, create_gpkg_threaded, threads_available

jobs = Blueprint('jobs', __name__, url_prefix='/jobs')


@jobs.route('/', methods=['POST'])
def add_job():
    if request.content_type == 'application/json':
        post_body = request.json

        # TODO check bbox area size
        # bbox is always in 4326
        bbox = post_body.get('bbox')
        if bbox is None or not len(bbox) == 4:
            abort(400)

        transform_to = post_body.get('transform_to')

        conn = db.pool.getconn()
        data_id = str(uuid.uuid4())

        if not threads_available(conn, current_app):
            return json.dumps({'success': False}), 400, {'ContentType': 'application/json'}

        job_id = create_job(conn, current_app, bbox, data_id, transform_to=transform_to)
        current_app.logger.info(f'Added job with id {job_id}')
        update_job(job_id, conn, current_app, status='RUNNING')
        layers = get_layers_from_file(current_app)
        layer_sqls = [(layer['layername'], get_geopackage_sql(bbox, conn, **layer, transform_to=transform_to)) for layer in layers]

        create_gpkg_threaded(current_app, request.base_url, job_id, data_id, layer_sqls)

        db.pool.putconn(conn)
        return json.dumps({'success': True, 'job_id': job_id}), 201, {'ContentType': 'application/json'}
    else:
        abort(400)


@jobs.route('/<int:job_id>', methods=['GET'])
def get_job(job_id):
    conn = db.pool.getconn()
    job = get_job_by_id(job_id, conn, current_app)
    db.pool.putconn(conn)
    # TODO create enum for job status
    if job.get('status') != 'CREATED':
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
        abort(400)

    delete_geopackage(job.get('data_id'), conn, current_app)
    deleted = delete_job_by_id(job_id, conn, current_app)
    db.pool.putconn(conn)
    if not deleted:
        current_app.logger.info(f'Could not delete job with id {job_id}')
        return json.dumps({'success': False}), 400, {'ContentType': 'application/json'}

    current_app.logger.info(f'Deleted job with id {job_id}')

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
