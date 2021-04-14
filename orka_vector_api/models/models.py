from flask import current_app

from orka_vector_api.db import db

__all__ = ['Job']


class Job(db.Model):
    __table_args__ = {'schema': 'orka-vector-api'}
    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
