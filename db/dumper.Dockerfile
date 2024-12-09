FROM python:3.12.7-slim AS builder

# timezone
ENV TZ=Asia/Tokyo
# set workdir
WORKDIR /app

RUN apt update && \
    apt upgrade -y && \
    apt install -y libpq-dev gcc make postgresql-common && \
    /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -i -v 17 && \
    apt install -y postgresql-client-17 && \
    apt clean

# install poetry
RUN pip install --upgrade pip poetry

# install requirements
COPY ./db/poetry.lock ./db/pyproject.toml ./db/Makefile ./db/dump.py /app/
RUN poetry config virtualenvs.create false
RUN make poetry:install:dumper

CMD ["python", "dump.py"]