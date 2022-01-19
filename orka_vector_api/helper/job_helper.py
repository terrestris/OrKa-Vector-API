import os

from psycopg2.extras import RealDictCursor
from psycopg2.sql import SQL, Identifier, Composed, Placeholder

from orka_vector_api.enums import Status


def create_job(conn, app, bbox, data_id, layers=None):
    schema = app.config['ORKA_DB_SCHEMA']
    if not _is_sane_schema(schema):
        raise Exception('Schema is not sane.')

    props = {
        'minx': float(bbox[0]),
        'miny': float(bbox[1]),
        'maxx': float(bbox[2]),
        'maxy': float(bbox[3]),
        'status': Status.INIT.value,
        'data_id': data_id,
        'layers': None
    }

    if layers is not None:
        props['layers'] = ','.join(layers)

    if False in [_is_sane(k, v) for k, v in props.items()]:
        raise Exception('Properties are not sane.')

    q = SQL('INSERT INTO {}.{} (minx, miny, maxx, maxy, status, data_id, layers) '
            'VALUES (%(minx)s, %(miny)s, %(maxx)s, %(maxy)s, %(status)s, %(data_id)s, %(layers)s) '
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

    if False in [_is_sane(k, v) for k, v in kwargs.items() if k != 'id']:
        raise Exception("Attributes are not sane.")

    vals = [Composed([Identifier(k), SQL('='), Placeholder(k)]) for k in kwargs.keys() if k != 'id']
    q = SQL('UPDATE {schema}.{table} SET {data} WHERE id = %(job_id)s;').format(
        schema=Identifier(schema),
        table=Identifier('jobs'),
        data=SQL(',').join(vals)
    )

    if 'status' in kwargs.keys():
        status = kwargs.get('status')
        if status == Status.TIMEOUT.value or status == Status.ERROR.value:
            app.logger.info(f'Setting status to {status} for job with id {job_id}')

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

    cols = ['id', 'minx', 'miny', 'maxx', 'maxy', 'data_id', 'status', 'layers']
    q = SQL('SELECT {cols} '
            'FROM {schema}.{table} '
            'WHERE id = %(job_id)s;').format(
        cols=SQL(',').join([Identifier(k) for k in cols]),
        schema=Identifier(schema),
        table=Identifier('jobs'))

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q, {'job_id': job_id})
        job = cur.fetchone()

    if job['layers'] is not None:
        job['layers'] = job['layers'].split(',')
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


def delete_geopackage(data_id, conn, app):
    gpkg_path = app.config['ORKA_GPKG_PATH']
    filename = data_id + '.gpkg'
    filepath = os.path.join(gpkg_path, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    else:
        return False


def count_running_jobs(conn, app):
    schema = app.config['ORKA_DB_SCHEMA']
    q = SQL('SELECT count(*) FROM {schema}.{table} WHERE status = %(status)s;').format(
        schema=Identifier(schema),
        table=Identifier('jobs')
    )

    with conn.cursor() as cur:
        cur.execute(q, {'status': Status.RUNNING.value})
        count = cur.fetchone()[0]
        conn.commit()

    return count


def threads_available(conn, app):
    max_threads = app.config['ORKA_MAX_THREADS']
    running_jobs = count_running_jobs(conn, app)
    # we have a watchdog for each thread, so we have to double it
    running_threads = running_jobs * 2
    free_threads = max_threads - running_threads
    return free_threads >= 2


def bbox_size_allowed(conn, app, bbox):
    minx = float(bbox[0])
    miny = float(bbox[1])
    maxx = float(bbox[2])
    maxy = float(bbox[3])

    max_area = app.config['ORKA_MAX_BBOX']
    q = 'SELECT ST_AREA(st_transform(geom, 3857))/1000000 from ST_MakeEnvelope(%(minx)s, %(miny)s, %(maxx)s, %(maxy)s, 4326) as geom;'
    with conn.cursor() as cur:
        cur.execute(q, {
            'minx': minx,
            'miny': miny,
            'maxx': maxx,
            'maxy': maxy
        })
        area = cur.fetchone()[0]
    return area <= max_area


def _is_sane(key, val):
    prop_map = {
        'minx': float,
        'miny': float,
        'maxx': float,
        'maxy': float,
        'status': str,
        'data_id': str,
        'layers': str
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
