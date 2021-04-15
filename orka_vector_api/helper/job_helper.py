from psycopg2.extras import RealDictCursor
from psycopg2.sql import SQL, Identifier, Composed, Placeholder


def create_job(conn, app, bbox, data_id, transform_to=None):
    schema = app.config['ORKA_DB_SCHEMA']
    if not _is_sane_schema(schema):
        raise Exception('Schema is not sane.')

    props = {
        'minx': float(bbox[0]),
        'miny': float(bbox[1]),
        'maxx': float(bbox[2]),
        'maxy': float(bbox[3]),
        'transform_to': transform_to,
        'status': 'INIT',
        'data_id': data_id
    }

    if False in [_is_sane(k, v) for k, v in props.items()]:
        raise Exception('Properties are not sane.')

    q = SQL('INSERT INTO {}.{} (minx, miny, maxx, maxy, transform_to, status, data_id) '
            'VALUES (%(minx)s, %(miny)s, %(maxx)s, %(maxy)s, %(transform_to)s, %(status)s, %(data_id)s) '
            'RETURNING id;').format(Identifier(schema), Identifier('jobs'))

    with conn.cursor() as cur:
        cur.execute(q, {'schema': schema, **props})
        job_id, = cur.fetchone()
        conn.commit()

    return job_id


def update_job(job_id, conn, app, **kwargs):
    schema = app.config['ORKA_DB_SCHEMA']
    if not _is_sane_schema(schema):
        raise Exception('Schema is not sane.')

    if False in [_is_sane(k, v) for k, v in kwargs.items()]:
        raise Exception("Attributes are not sane.")

    vals = [Composed([Identifier(k), SQL('='), Placeholder(k)]) for k in kwargs.keys()]
    q = SQL('UPDATE {schema}.{table} SET {data} WHERE id = %(job_id)s;').format(
        schema=Identifier(schema),
        table=Identifier('jobs'),
        data=SQL(',').join(vals)
    )

    with conn.cursor() as cur:
        cur.execute(q, {
            **kwargs,
            'job_id': job_id
        })
        conn.commit()


def get_job_by_id(job_id, conn, app):
    schema = app.config['ORKA_DB_SCHEMA']
    if not _is_sane_schema(schema):
        raise Exception('Schema is not sane.')

    cols = ['id', 'minx', 'miny', 'maxx', 'maxy', 'data_id', 'transform_to', 'status']
    q = SQL('SELECT {cols} '
            'FROM {schema}.{table} '
            'WHERE id = %(job_id)s;').format(
        cols=SQL(',').join([Identifier(k) for k in cols]),
        schema=Identifier(schema),
        table=Identifier('jobs'))

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q, {'job_id': job_id})
        job = cur.fetchone()

    # TODO create enum for job status
    if not job.get('status') == 'READY':
        job.pop('data_id')

    return job


def get_job_id_by_dataid(data_id, conn, app):
    schema = app.config['ORKA_DB_SCHEMA']
    if not _is_sane_schema(schema):
        raise Exception('Schema is not sane.')

    q = SQL('SELECT id FROM {schema}.{table} WHERE data_id = %(data_id)s LIMIT 1;').format(
        schema=Identifier(schema),
        table=Identifier('jobs'))

    with conn.cursor() as cur:
        cur.execute(q, {'data_id': data_id})
        result = cur.fetchone()
        if result is None:
            job_id = None
        else:
            job_id = result[0]

    return job_id


def delete_job_by_id(job_id, conn, app):
    schema = app.config['ORKA_DB_SCHEMA']
    if not _is_sane_schema(schema):
        raise Exception('Schema is not sane.')

    q = SQL('DELETE FROM {schema}.{table} WHERE id = %(job_id)s;').format(
        schema=Identifier(schema),
        table=Identifier('jobs')
    )

    with conn.cursor() as cur:
        cur.execute(q, {'job_id': job_id})
        deleted_rows = cur.rowcount
        conn.commit()

    return deleted_rows == 1


def _is_sane(key, val):
    prop_map = {
        'minx': float,
        'miny': float,
        'maxx': float,
        'maxy': float,
        'transform_to': str,
        'status': str,
        'data_id': str
    }

    if not isinstance(key, str):
        return False
    if key not in prop_map:
        return False

    if val is None:
        return True
    if not isinstance(val, prop_map.get(key)):
        return False
    if prop_map.get(key) == str:
        if len(val) == 0:
            return False
        if '--' in val:
            return False

    return True


def _is_sane_schema(schema):
    if not isinstance(schema, str):
        return False
    if len(schema) == 0:
        return False
    if '--' in schema:
        return False
    if len(schema.split(' ')) != 1:
        return False

    return True
