# suan-trazabilidad

### Install poetry

```shell
curl -sSL https://install.python-poetry.org | python3 -

poetry new suantrazabilidad
```

Or if project pre-exists, inside the project folder then:

```shell
poetry init
```

## Add dependencies

```shell
poetry add <dependency>
```

### Use alembic to setup the database

```shell
poetry add alembic

alembic init alembic

alembic revision --autogenerate -m "Creation of tables"

alembic upgrade head

alembic downgrade -1 # downgrade to previous version
alembic downgrade head # drop tables

```

### Use docker

Create docker file

Run following commands to create or update the image

    docker build -t suantrazabilidad .
    docker run -d --name suantrazabilidadapi -p 80:80 suantrazabilidad

Other useful docker commands

    docker rm {image}
    docker image ls
