import os
import subprocess
from os import listdir
from os.path import isfile, join, splitext
from threading import Event, Thread

from requests import put

from orka_vector_api.enums import Status


def _get_gpkg_cmd(filename, layername, sql, host=None, port=None, database=None, user=None, password=None):
    cmd = f'ogr2ogr -f "GPKG" {filename} ' \
          f'PG:"host={host} user={user} port={port} dbname={database} password={password}" ' \
          f'-sql "{sql}" ' \
          f'-nln "{layername}" ' \
          f'-t_srs EPSG:25833 ' \
          f'-append'

    return cmd


def _create_gpkg(data_id, bbox, timeout_e=None, error_e=None, db_props=None, gpkg_path='', layers_path=''):
    file_name = os.path.abspath(os.path.join(gpkg_path, data_id + '.gpkg'))
    layer_sqls = _get_layer_sqls(layers_path)
    for layer_name, layer_sql in layer_sqls.items():
        if timeout_e is not None and timeout_e.isSet():
            break
        gpkg_sql = _get_gpkg_sql(layer_sql, bbox)
        gpkg_sql_escaped = _escape_sql(gpkg_sql)
        print(gpkg_sql_escaped)
        cmd = _get_gpkg_cmd(file_name, layer_name, gpkg_sql_escaped, **db_props)
        proc = subprocess.run(cmd, shell=True, capture_output=True)
        # if proc.stderr:
        #     if error_e is not None:
        #         error_e.set()
        #     break
            # raise Exception(f'Error creating {file_name}: ' + proc.stderr.decode())
        if proc.returncode != 0:
            print(proc.stderr.decode())
            if error_e is not None:
                error_e.set()
            break
            # raise Exception(f'Error creating {file_name}: Program exited with non-zero code.')


def _escape_sql(sql):
    return sql.translate(str.maketrans({'"': r'\"'}))


def _get_layer_sqls(layers_path):
    layers = {}
    for fname in listdir(layers_path):
        fpath = join(layers_path, fname)
        if not isfile(fpath):
            continue
        if not fname.endswith('.sql'):
            continue

        lname, _ = splitext(fname)
        with open(fpath) as f:
            layers[lname] = ' '.join(f.read().splitlines())

    return layers


def _get_gpkg_sql(layer_sql, bbox):
    bbox_str = ', '.join([str(b) for b in bbox])
    # we use && (overlaps) instead of @> (contains), as we want to include all geometries that
    # in some way lie within the bbox
    # see https://www.postgresql.org/docs/9.1/functions-array.htm
    return (f'SELECT * FROM ({layer_sql}) AS l '
            f'WHERE l.geometry '
            f'&& ST_Transform(ST_MakeEnvelope({bbox_str}, 4326), ST_SRID(l.geometry))')


def create_gpkg_threaded(app, base_url, job_id, *args):
    db_props = {
        'host': app.config['PG_HOST'],
        'port': app.config['PG_PORT'],
        'database': app.config['PG_DATABASE'],
        'user': app.config['PG_USER'],
        'password': app.config['PG_PASSWORD']
    }
    gpkg_path = app.config['ORKA_GPKG_PATH']
    layers_path = app.config['ORKA_LAYERS_PATH']
    timeout = app.config['ORKA_THREAD_TIMEOUT']

    if not base_url.endswith('/'):
        base_url += '/'
    response_url = f'{base_url}{job_id}'

    layers_abs_path = os.path.abspath(layers_path)

    thread = Thread(target=_create_gpkg_threaded,
                    args=(response_url, *args,),
                    kwargs={
                        'timeout': timeout,
                        'db_props': db_props,
                        'gpkg_path': gpkg_path,
                        'layers_path': layers_abs_path
                    })
    thread.start()


def _create_gpkg_threaded(response_url, *args, timeout=None, **kwargs):
    timeout_e = Event()
    error_e = Event()
    thread = Thread(target=_create_gpkg, args=args, kwargs={'timeout_e': timeout_e, 'error_e': error_e, **kwargs})
    thread.start()

    killed = False
    if timeout is not None:
        thread.join(timeout)
        if thread.is_alive():
            killed = True
        timeout_e.set()
    thread.join()

    if error_e.isSet():
        return put(response_url, json={'status': Status.ERROR.value})
    if killed or error_e.isSet():
        return put(response_url, json={'status': Status.TIMEOUT.value})
    else:
        return put(response_url, json={'status': Status.CREATED.value})
