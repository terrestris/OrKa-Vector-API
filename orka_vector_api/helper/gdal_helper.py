# TODO make this actually work
def create_or_append_geopackage(bbox, data_id, conn, app):
    host = app.config['PG_HOST'],
    port = app.config['PG_PORT'],
    database = app.config['PG_DATABASE'],
    user = app.config['PG_USER'],
    password = app.config['PG_PASSWORD']

    filename = data_id + '.gpkg'

    # TODO add proper filepath
    # TODO use SQL methods of psycopg to provide proper sql query here
    sql = ''
    # TODO get layername
    layername = ''
    cmd = f'ogr2ogr -f "GPKG" {filename} ' \
          f'PG:"host={host} user={user} port={port} dbname={database} password={password}" ' \
          f'-sql "{sql}" ' \
          f'-nln "{layername}" ' \
          f'-append'

    cur = conn.cursor()
    cur.execute(sql)
    result = cur.fetchall()
    for geom in result:
        print(geom)

    cur.close()
    return data_id
