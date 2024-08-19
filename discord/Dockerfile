FROM python:3.12.5-slim

WORKDIR /app

RUN apt update && \
    apt upgrade -y && \
    apt install -y build-essential git nano \
    tzdata libpq-dev gcc make && \
    pip install --upgrade pip poetry

# install requirements
COPY ./discord/poetry.lock ./discord/pyproject.toml ./discord/Makefile /app/
RUN poetry config virtualenvs.create false
RUN make poetry:install

# add poetry files for symlinks
COPY ./pyproject.toml ./poetry.lock /

CMD ["/app/bot.sh"]