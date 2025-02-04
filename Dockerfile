FROM python:3.11 AS requirements-stage

WORKDIR /tmp

# RUN pip install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"

# Install the poetry export plugin
RUN poetry self add poetry-plugin-export

# Debug: Check if Poetry and the plugin are installed
RUN poetry --version && poetry self show plugins

COPY ./pyproject.toml ./poetry.lock* /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM python:3.11

WORKDIR /code

# Copy the external pycardano folder
# COPY ./pycardano /code/pycardano

COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./suantrazabilidadapi /code/suantrazabilidadapi

EXPOSE 80

CMD ["uvicorn", "suantrazabilidadapi.app:suantrazabilidad", "--host", "0.0.0.0", "--port", "80"]