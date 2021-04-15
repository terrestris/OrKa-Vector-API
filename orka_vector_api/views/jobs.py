import json
import uuid
from flask import Blueprint, request, abort, current_app

from orka_vector_api import db
from orka_vector_api.helper import create_or_append_geopackage, create_job, update_job, get_job_by_id, delete_job_by_id

jobs = Blueprint('jobs', __name__, url_prefix='/jobs')


@jobs.route('/', methods=['POST'])
def add_job():
    if request.content_type == 'application/json':
        post_body = request.json

        # TODO check bbox area size
        bbox = post_body.get('bbox')
        if bbox is None:
            abort(400)

        conn = db.pool.getconn()
        data_id = str(uuid.uuid4())
        job_id = create_job(conn, current_app, bbox, data_id)
        # update_job(job_id, conn, current_app, status='RUNNING')
        # TODO find a way to trigger this method but returning a response beforehand (worker)
        # gpkg = create_or_append_geopackage(bbox, conn, current_app)
        db.pool.putconn(conn)
        return json.dumps({'success': True, 'job_id': job_id}), 201, {'ContentType': 'application/json'}
    else:
        abort(400)


@jobs.route('/<int:job_id>', methods=['GET'])
def get_job(job_id):
    conn = db.pool.getconn()
    job = get_job_by_id(job_id, conn, current_app)
    db.pool.putconn(conn)
    return job


@jobs.route('/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    conn = db.pool.getconn()
    # TODO remove gpgk file
    deleted = delete_job_by_id(job_id, conn, current_app)
    db.pool.putconn(conn)
    if not deleted:
        return json.dumps({'success': False}), 400, {'ContentType': 'application/json'}

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
