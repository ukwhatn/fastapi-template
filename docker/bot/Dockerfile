FROM python:3.12.1-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    nano \
    tzdata \
    libpq-dev \
    gcc

COPY ./bot/requirements.txt /temp/requirements.txt
COPY ./server/db/requirements.txt /temp/db-requirements.txt

RUN pip install --upgrade pip && \
    pip install --no-cache-dir --upgrade -r /temp/requirements.txt && \
    pip install --no-cache-dir --upgrade -r /temp/db-requirements.txt

CMD ["/app/bot.sh"]