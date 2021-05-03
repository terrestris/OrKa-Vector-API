import os
import subprocess

import yaml
from psycopg2.sql import SQL, Identifier, Literal


def _get_geopackage_cmd(filename, layername, sql, host=None, port=None, database=None, user=None, password=None):
    cmd = f'ogr2ogr -f "GPKG" {filename} ' \
          f'PG:"host={host} user={user} port={port} dbname={database} password={password}" ' \
          f'-sql "{sql}" ' \
          f'-nln "{layername}" ' \
          f'-append'

    return cmd


def create_geopackage(data_id, app, layer_sqls):
    gpkg_path = app.config['ORKA_GPKG_PATH']
    filename = os.path.abspath(os.path.join(gpkg_path, data_id + '.gpkg'))
    db_props = {
        'host': app.config['PG_HOST'],
        'port': app.config['PG_PORT'],
        'database': app.config['PG_DATABASE'],
        'user': app.config['PG_USER'],
        'password': app.config['PG_PASSWORD']
    }

    for layername, layer_sql in layer_sqls:
        cmd = _get_geopackage_cmd(filename, layername, layer_sql, **db_props)
        app.logger.info(cmd)
        proc = subprocess.run(cmd, shell=True, capture_output=True)
        app.logger.info(f'Exporting {layername} exited with code {proc.returncode}')
        if proc.stderr:
            app.logger.error(f'[stderr]\n{proc.stderr.decode()}')
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
