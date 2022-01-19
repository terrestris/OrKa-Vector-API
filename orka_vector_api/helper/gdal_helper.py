import logging
import os
import subprocess
from os import listdir
from os.path import isfile, join, splitext
from threading import Event, Thread

from requests import put

from orka_vector_api import setup_file_logger
from orka_vector_api.enums import Status


def _get_gpkg_cmd(filename, layername, sql, host=None, port=None, database=None, user=None, password=None):
    cmd = f'ogr2ogr -f "GPKG" {filename} ' \
          f'PG:"host={host} user={user} port={port} dbname={database} password={password}" ' \
          f'-sql "{sql}" ' \
          f'-nln "{layername}" ' \
          f'-t_srs EPSG:25833 ' \
          f'-append'

    return cmd


def _create_gpkg(data_id, bbox, layers, timeout_e=None, error_e=None, db_props=None, gpkg_path='', layers_path='',
                 logfile='orka.log', loglevel='INFO'):
    log_handler = setup_file_logger(logfile=logfile)
    logger = logging.getLogger()
    logger.addHandler(log_handler)
    logger.setLevel(loglevel)
    file_name = os.path.abspath(os.path.join(gpkg_path, data_id + '.gpkg'))
    layer_sqls = _get_layer_sqls(layers_path, layer_names=layers)
    for layer_name, layer_sql in layer_sqls.items():
        if timeout_e is not None and timeout_e.isSet():
            break
        gpkg_sql = _get_gpkg_sql(layer_sql, bbox)
        gpkg_sql_escaped = _escape_sql(gpkg_sql)
        logger.debug(gpkg_sql_escaped)
        cmd = _get_gpkg_cmd(file_name, layer_name, gpkg_sql_escaped, **db_props)
        try:
            subprocess.run(cmd, shell=True, check=True, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            logger.info(f'Error creating gpkg: {e.stderr.decode()}')
            if error_e is not None:
                error_e.set()
            break


def _escape_sql(sql):
    return sql.translate(str.maketrans({'"': r'\"'}))


def _get_layer_sqls(layers_path, layer_names=None):
    layers = {}
    for f_name in listdir(layers_path):
        f_path = join(layers_path, f_name)
        f_root, f_ext = splitext(f_name)
        if not isfile(f_path):
            continue
        if not f_ext == '.sql':
            continue
        if layer_names is not None and f_root not in layer_names:
            continue

        with open(f_path) as f:
            layers[f_root] = ' '.join(f.read().splitlines())

    return layers


def _get_gpkg_sql(layer_sql, bbox):
    bbox_str = ', '.join([str(b) for b in bbox])
    # we use && (overlaps) instead of @> (contains), as we want to include all geometries that
    # in some way lie within the bbox
    # see https://www.postgresql.org/docs/9.1/functions-array.htm
    return (f'SELECT * FROM ({layer_sql}) AS l '
            f'WHERE l.geometry '
            f'&& ST_Transform(ST_MakeEnvelope({bbox_str}, 4326), ST_SRID(l.geometry))')


def create_gpkg_threaded(app, job_id, *args, layers=None):
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
    logfile = app.config['ORKA_LOG_FILE']
    loglevel = app.config['ORKA_LOG_LEVEL']
    app_port = app.config['ORKA_APP_PORT']

    response_url = f'http://localhost:{app_port}/jobs/{job_id}'

    layers_abs_path = os.path.abspath(layers_path)

    thread = Thread(target=_create_gpkg_threaded,
                    args=(response_url, *args, layers),
                    kwargs={
                        'timeout': timeout,
                        'db_props': db_props,
                        'gpkg_path': gpkg_path,
                        'layers_path': layers_abs_path,
                        'logfile': logfile,
                        'loglevel': loglevel
                    })
    thread.start()


def _create_gpkg_threaded(response_url, *args, timeout=None, logfile='orka.log', loglevel='INFO', **kwargs):
    try:
        timeout_e = Event()
        error_e = Event()
        thread = Thread(target=_create_gpkg, args=args,
                        kwargs={'timeout_e': timeout_e, 'error_e': error_e, 'logfile': logfile, 'loglevel': loglevel,
                                **kwargs})
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
    except Exception as e:
        log_handler = setup_file_logger(logfile=logfile)
        logger = logging.getLogger()
        logger.addHandler(log_handler)
        logger.setLevel(loglevel)
        logger.info(f'Unexpected Error: {e}')
        return put(response_url, json={'status': Status.ERROR.value})
