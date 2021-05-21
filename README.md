# OrKa-Vector-API
The OrKa Vector REST API

# Install

Requires a postgres database with postgis extension installed.

```shell
pip install orka-vector-api
```

# Development


## Run Dev Server

```shell
FLASK_APP=orka_vector_api FLASK_ENV=development flask run
```

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
- `ORKA_LAYERS_PATH` = path to folder containing the layer sqls. This folder must be located within the instance folder
- `ORKA_THREAD_TIMEOUT` = timeout in seconds after which a running thread should be killed.
- `ORKA_MAX_THREADS` = number of allowed threads
- `ORKA_LOG_FILE` = path to log file
- `ORKA_STYLE_PATH` = path to the file that contains all styles, etc.
- `ORKA_STYLE_FILE` = name of the zip file (including `.zip`) that contains all styles, etc.
- `ORKA_MAX_BBOX` = maximum allowed size of the bbox in sqkm. 
- `ORKA_LOG_LEVEL` = log level
- `ORKA_APP_PORT` = the port under which the app is running on

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
ORKA_LAYERS_PATH = 'layers/'
ORKA_THREAD_TIMEOUT = 60
ORKA_MAX_THREADS = 4

ORKA_LOG_FILE = '/var/log/orka_vector_api/orka_vector_api.log'
ORKA_LOG_LEVEL = 'WARNING'

ORKA_STYLE_PATH = 'styles/'
ORKA_STYLE_FILE = 'style.zip'
ORKA_MAX_BBOX = 23211

ORKA_APP_PORT = 5000
```

# Publishing

- update version number in setup.py and orka_vector_api/__init__.py
- run following commands:

```shell
python3 -m venv venv_publish
source venv_publish/bin/activate
pip install -r requirements_publish.txt
python setup.py sdist bdist_wheel
# make sure following command prints 'passed' on all files in dist/
twine check dist/*
twine upload dist/*
```