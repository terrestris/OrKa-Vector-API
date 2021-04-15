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
