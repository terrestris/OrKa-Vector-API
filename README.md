# OrKa-Vector-API
The OrKa Vector REST API

# Commands

## run dev server

start application
```shell
FLASK_APP=orka_vector_api FLASK_ENV=development flask run
```

## run prod server from another venv (waitress)

```shell
waitress-serve --call 'orka_vector_api:create_app'
```

# build

see https://flask.palletsprojects.com/en/1.1.x/tutorial/deploy/

# Configs

## config.py

A `config.py` must be added to the [instance folder](https://flask.palletsprojects.com/en/1.1.x/config/#instance-folders)
that allows following additional configs:

- `PG_USER` - username of the user that has access to the vector layers
- `PG_PASSWORD` = password of the user
- `PG_HOST` = database host
- `PG_PORT` = database port
- `PG_DATABASE` = database name
- `ORKA_DB_USER` = application database username
- `ORKA_DB_PASSWORD` = application database password
- `ORKA_DB_HOST` = application database host
- `ORKA_DB_PORT` = application database port
- `ORKA_DB_DATABASE` = application database name
- `ORKA_DB_SCHEMA` = application database schema
- `ORKA_DB_MIN_CONNECTION` = application database min connections
- `ORKA_DB_MAX_CONNECTION` = application database max connections
- `ORKA_GPKG_PATH` = path to where the created gpkg files should be placed
- `ORKA_LAYERS_YML` = path to yaml file that contains the layer specs. This file must be located within the instance folder 
- `ORKA_THREAD_TIMEOUT` = timeout in seconds after which a running thread should be killed.
- `ORKA_MAX_THREADS` = number of allowed threads

Example config.py:

```python
PG_USER = 'user'
PG_PASSWORD = 'password'
PG_HOST = 'localhost'
PG_PORT = 5432
PG_DATABASE = 'postgres'

ORKA_DB_USER = 'user2'
ORKA_DB_PASSWORD = 'password2'
ORKA_DB_HOST = 'localhost'
ORKA_DB_PORT = 5555
ORKA_DB_DATABASE = 'postgres'
ORKA_DB_SCHEMA = 'public'
ORKA_DB_MIN_CONNECTION = 1
ORKA_DB_MAX_CONNECTION = 1

ORKA_GPKG_PATH = 'data/'
ORKA_LAYERS_YML = 'layers.yml'
ORKA_THREAD_TIMEOUT = 60
ORKA_MAX_THREADS = 4
```

## layers.yml

Additionally a yaml file must be added that contains the specification for the
data to retrieve from the database. The name of the file must be specified in `config.py`.

The yaml file must provide following structure:

```yaml
- layername: '' # name of the table/layer
  schema: '' # schema of the table'
  geom_column: '' # name of the column that contains the geometries'. This will always be included in the dataset.
  columns: # list of additional columns that should be included in the gpkg
    - '' # name of column
```

Example layers.yml:

```yaml
- layername: 'osm_aeroways'
  schema: 'public'
  geom_column: 'geometry'
  columns:
    - 'type'
- layername: 'osm_waterareas'
  schema: 'public'
  geom_column: 'geometry'
  columns:
    - 'type'
    - 'name'
```
