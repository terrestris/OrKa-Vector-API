import os
import subprocess
from threading import Event, Thread

import yaml
from psycopg2.sql import SQL, Identifier, Literal
from flask import url_for
from requests import put


def _get_geopackage_cmd(filename, layername, sql, host=None, port=None, database=None, user=None, password=None):
    cmd = f'ogr2ogr -f "GPKG" {filename} ' \
          f'PG:"host={host} user={user} port={port} dbname={database} password={password}" ' \
          f'-sql "{sql}" ' \
          f'-nln "{layername}" ' \
          f'-append'

    return cmd


def create_geopackage(data_id, layer_sqls, e, db_props=None, gpkg_path=''):
    filename = os.path.abspath(os.path.join(gpkg_path, data_id + '.gpkg'))
    print(f'creating geopackage for {data_id}, {db_props}, {gpkg_path}')

    for layername, layer_sql in layer_sqls:
        if e.isSet():
            break
        cmd = _get_geopackage_cmd(filename, layername, layer_sql, **db_props)
        # app.logger.info(cmd)
        proc = subprocess.run(cmd, shell=True, capture_output=True)
        # app.logger.info(f'Exporting {layername} exited with code {proc.returncode}')
        # if proc.stderr:
        #     app.logger.error(f'[stderr]\n{proc.stderr.decode()}')
        if proc.returncode != 0:
            return False
    return True


def get_geopackage_sql(bbox, conn, layername='', schema='', geom_column='geometry', columns=None, transform_to=None):
    if columns is None:
        columns = ['id']

    # always add id column
    if 'id' not in columns:
        columns.append('id')

    geom_sql = Identifier(geom_column)
    target_epsg = None
    if transform_to is not None:
        # we only need the numeric part of the epsg code
        target_epsg = int(transform_to.split(':')[1])
        geom_sql = SQL('ST_Transform({col}, {target_epsg})').format(col=geom_sql, target_epsg=Literal(target_epsg))

    layer_epsg_sql = SQL('Find_SRID({schema}, {table}, {geom_column})').format(
        schema=Literal(schema), table=Literal(layername), geom_column=Literal(geom_column))

    # we use && (overlaps) instead of @> (contains), as we want to include all geometries that
    # in some way lie within the bbox
    # see https://www.postgresql.org/docs/9.1/functions-array.html
    sql = SQL('SELECT {columns}, {geom_sql} as {geom_column} '
              'FROM {schema}.{table} AS t '
              'WHERE t.{geom_column} '
              '&& ST_Transform(ST_MakeEnvelope({bbox}, {source_epsg}), {layer_epsg});').format(
        columns=SQL(',').join([Identifier(k) for k in columns]),
        geom_sql=geom_sql,
        geom_column=Identifier(geom_column),
        schema=Identifier(schema),
        table=Identifier(layername),
        bbox=SQL(', ').join([Literal(b) for b in bbox]),
        layer_epsg=layer_epsg_sql,
        source_epsg=Literal(4326),
    )

    return sql.as_string(conn)


def get_layers_from_file(app):
    with open(os.path.join(app.instance_path, app.config['ORKA_LAYERS_YML'])) as file:
        layers = yaml.load(file, Loader=yaml.FullLoader)
        return layers


def create_gpkg_threaded(app, base_url, job_id, *args):
    db_props = {
        'host': app.config['PG_HOST'],
        'port': app.config['PG_PORT'],
        'database': app.config['PG_DATABASE'],
        'user': app.config['PG_USER'],
        'password': app.config['PG_PASSWORD']
    }
    gpkg_path = app.config['ORKA_GPKG_PATH']
    timeout = app.config['ORKA_THREAD_TIMEOUT']

    if not base_url.endswith('/'):
        base_url += '/'
    response_url = f'{base_url}{job_id}'
    thread = Thread(target=_create_gpkg_threaded, args=(response_url, *args),
                    kwargs={'timeout': timeout, 'db_props': db_props, 'gpkg_path': gpkg_path})
    thread.start()


def _create_gpkg_threaded(response_url, *args, timeout=None, **kwargs):
    event = Event()
    thread = Thread(target=create_geopackage, args=(*args, event), kwargs=kwargs)
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
        return put(response_url, json={'status': 'TIMEOUT'})
    else:
        return put(response_url, json={'status': 'CREATED'})
