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

## Or start from requirements.txt file
```shell
poetry add --dev $(cat requirements.txt)
poetry install
```

### Steps to start the application for the first time

- Locally

1. Clone the repo
2. Install dependencies with Poetry
4. Copy credentials.ini and rename it credentials.local.ini. Update the env values. 
    - Update the env values
3. Start the application using main.py file
    - Once the application is run, it creates the first tables project and Principalform and update records from the excel file attached in utils/data.
4. Use /kobo/forms/upgrade and /kobo/data/upgrade endpoints to create form tables with data from kobo for all existing forms in kobo or /data/upgrade/{form_id}/ for only form_id
    - This form tables are alembic based versionning

### Steps to changes made on forms

1. Reflect the change in the excel file found in utils/data.
2. Start the application using main.py file
3. Use previous kobo upgrades endpoints to make the updates.

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

When the new environment is created, no service is attached. To deploy service run:

    copilot deploy

And select the environment.



### Alembic useful commands

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

### Celery

1. Install celery with broker and backend dependencies (sqs or redis or rabbitmq) and then start both services


### Describing AppRunner services

```shell
aws apprunner list-services

aws apprunner describe-service --service-arn <service-arn>


<!-- 2. Install watchdog to autoupload celery in development whenever there's a change in one of the project files

```shell
poetry add celery[sqs]
#or
poetry add celery[redis]
watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- celery -A suantrazabilidad.celery worker --loglevel info

```

Wathcdemo is only meant to be run in dev mode. 


Run  -->