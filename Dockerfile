FROM python:3.10.0-slim-buster

ENV POETRY_VERSION=1.2.1
ENV PYTHONUNBUFFERED 1

RUN pip install "poetry==$POETRY_VERSION"

WORKDIR /code

COPY ./poetry.lock ./pyproject.toml /code/
COPY ./short_url /code/short_url

RUN poetry config virtualenvs.create false && poetry install --no-dev --no-interaction --no-ansi

EXPOSE 8000
