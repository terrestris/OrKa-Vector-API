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
          f'-append'

    return cmd


def _create_gpkg(data_id, bbox, e, db_props=None, gpkg_path='', layers_path=''):
    file_name = os.path.abspath(os.path.join(gpkg_path, data_id + '.gpkg'))
    layer_sqls = _get_layer_sqls(layers_path)
    for layer_name, layer_sql in layer_sqls.items():
        if e.isSet():
            break
        gpkg_sql = _get_gpkg_sql(layer_sql, bbox)
        gpkg_sql_escaped = _escape_sql(gpkg_sql)
        print(gpkg_sql_escaped)
        cmd = _get_gpkg_cmd(file_name, layer_name, gpkg_sql_escaped, **db_props)
        proc = subprocess.run(cmd, shell=True, capture_output=True)
        if proc.stderr:
            raise Exception(proc.stderr.decode())
        if proc.returncode != 0:
            raise Exception('Creating Geopackage exited with non-zero code')


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
    with_sql = f'WITH l AS ({layer_sql})'
    select_sql = 'SELECT * FROM l'
    srid_sql = 'SELECT ST_SRID(l.geometry) AS srid FROM l LIMIT 1'
    where_sql = f'l.geometry && ST_Transform(ST_MakeEnvelope({bbox_str}, 4326), ({srid_sql}))'
    return f'{with_sql} {select_sql} WHERE {where_sql};'


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
    event = Event()
    thread = Thread(target=_create_gpkg, args=(*args, event), kwargs=kwargs)
    thread.start()

    killed = False
    if timeout is not None:
        thread.join(timeout)
        if thread.is_alive():
            killed = True
        event.set()
    thread.join()
    # TODO check if thread threw exception
    if killed:
        # TODO check if this works with proxy
        return put(response_url, json={'status': Status.TIMEOUT.value})
    else:
        return put(response_url, json={'status': Status.CREATED.value})
