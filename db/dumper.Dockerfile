FROM python:3.12.7-slim AS builder

RUN apt update && \
    apt upgrade -y && \
    apt install -y libpq-dev gcc make postgresql-common && \
    /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -i -v 17 && \
    apt install -y postgresql-client-17

FROM python:3.12.7-slim AS runner

# timezone
ENV TZ=Asia/Tokyo
# set workdir
WORKDIR /app

# install libpq
RUN apt update && \
    apt upgrade -y && \
    apt install -y libpq-dev && \
    apt clean

# copy from builder
COPY --from=builder /usr/bin/make /usr/bin/make
COPY --from=builder /usr/lib/postgresql/17/bin/pg_dump /usr/bin/pg_dump
COPY --from=builder /usr/lib/postgresql/17/bin/pg_restore /usr/bin/pg_restore
COPY --from=builder /usr/lib/libpq.so.* /usr/lib/

# install poetry
RUN pip install --upgrade pip poetry

# install requirements
COPY ./db/poetry.lock ./db/pyproject.toml ./db/Makefile ./db/dump.py /app/
RUN poetry config virtualenvs.create false
RUN make poetry:install:dumper

CMD ["python", "dump.py"]