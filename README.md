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

### Steps to start the application for the first time

1. Use alembic to setup the database

```shell
poetry add alembic

alembic init alembic
````
> Additional commands for alembic are: 
```shell
alembic revision --autogenerate -m "Creation of tables"

alembic upgrade head

alembic downgrade -1 # downgrade to previous version
alembic downgrade head # drop tables
```

2. Start the application locally or with docker or with copilot

The aplication creates empty tables for principalform and projects but no alembic versionning is performed

3. Create kobo form tables using the api endpoint

Use /kobo/forms/upgrade endpoint to create form tables

4. Update tables with data

Use /kobo/data/upgrade/ endpoint to create data records in form tables

5. Copy the credentials.ini file, rename it as credentials.local.ini, make updates accordingly

> When running in docker change ENABLE_LOCAL_ENDPOINTS to False.


3. Update tables

- Use IntegracionKobo.xlsx file to update the table sctructure for kobo data tables or in dbmodels.py to manually change the data schema for Projects or PrincipalForm tables.

- Run again alembic

- Restart the application


### Use of docker

Create docker file

Run following commands to create or update the image

    docker build -t suantrazabilidad .
    docker run -d --name suantrazabilidadapi -p 80:80 suantrazabilidad

Other useful docker commands

    docker rm {image}
    docker image ls


### Copilot 

Install copilot

    curl -Lo copilot https://github.com/aws/copilot-cli/releases/latest/download/copilot-linux && chmod +x copilot && sudo mv copilot /usr/local/bin/copilot && copilot --help

Then we just need to start copilot CLI

    copilot init

Other useful commands

    copilot app delete

Create new environment

    copilot env init
    copilot env deploy --name prod
    copilot env ls

http://suant-Publi-15HX2LGTWJYAV-1336239482.us-east-1.elb.amazonaws.com