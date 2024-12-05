FROM python:3.13.1-slim

# set workdir
WORKDIR /app

RUN apt update && \
    apt upgrade -y && \
    apt install -y libpq-dev gcc make curl && \
    pip install --upgrade pip poetry

# install requirements
COPY ./server/poetry.lock ./server/pyproject.toml ./server/Makefile /app/
RUN poetry config virtualenvs.create false
RUN make poetry:install

# add poetry files for symlinks
COPY ./pyproject.toml ./poetry.lock /