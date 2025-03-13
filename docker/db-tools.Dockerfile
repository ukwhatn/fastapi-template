FROM python:3.13.2-slim

# 作業ディレクトリ設定
WORKDIR /app

# 環境変数設定
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# システム依存パッケージインストールと不要なキャッシュの削除
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends libpq-dev gcc make && \
    pip install --no-cache-dir --upgrade pip poetry && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Poetryの設定
RUN poetry config virtualenvs.create false

# 依存関係ファイルをコピー
COPY pyproject.toml poetry.lock ./

# モードに基づいて依存関係をインストール
RUN poetry install --no-interaction --with db,dumper

# マイグレーションファイルとダンプスクリプトをコピー
COPY alembic.ini ./
COPY migrations ./migrations
COPY app/db/dump.py ./

# エントリポイントスクリプト
COPY docker/db-tools-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ARG MODE=migrator
ENV DB_TOOL_MODE=$MODE
# エントリポイントスクリプトを実行
ENTRYPOINT ["/entrypoint.sh"]