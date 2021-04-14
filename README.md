# OrKa-Vector-API
The OrKa Vector REST API

# Commands

## run dev server

(optional) set path to non-default config file
```shell
export CONFIG_ABS_PATH=/path/to/config/file/config.py
```

start application
```shell
FLASK_APP=orka_vector_api FLASK_ENV=development flask run
```

## run prod server (waitress)

TODO fix command/setup

```shell
export CONFIG_ABS_PATH=/path/to/config/file/config.py
waitress-serve --call 'orka_vector_api:create_app'
```


## db

```shell
FLASK_APP=orka_vector_api FLASK_ENV=development flask db init
FLASK_APP=orka_vector_api FLASK_ENV=development flask db migrate
FLASK_APP=orka_vector_api FLASK_ENV=development flask db upgrade
```