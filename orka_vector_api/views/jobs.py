from flask import Blueprint

from orka_vector_api.models import Job

jobs = Blueprint('jobs', __name__, url_prefix='/jobs')

@jobs.route('/')
def root():
    db_jobs = Job.query.all()
    return {
        'jobs': db_jobs
    }
