FROM python:3.13.2-slim

# 作業ディレクトリ設定
WORKDIR /app

# システム依存パッケージインストール
RUN apt update && \
    apt upgrade -y && \
    apt install -y libpq-dev gcc make && \
    pip install --upgrade pip poetry

# Poetryの設定
RUN poetry config virtualenvs.create false

# 依存関係ファイルをコピー
COPY pyproject.toml poetry.lock ./

# 依存関係インストール
RUN poetry install --with db

# 移行ファイルをコピー
COPY migrations ./migrations
COPY alembic.ini ./

# 実行コマンド
CMD ["/bin/bash", "-c", "alembic upgrade head"]