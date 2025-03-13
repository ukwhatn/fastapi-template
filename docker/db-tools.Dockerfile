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

# 引数からモードを取得（migrator または dumper）
ARG MODE=migrator

# モードに基づいて依存関係をインストール
RUN if [ "$MODE" = "migrator" ]; then \
      poetry install --with db; \
    elif [ "$MODE" = "dumper" ]; then \
      poetry install --with db,dumper; \
    fi

# マイグレーションファイルをコピー（migrator の場合）
COPY migrations ./migrations
COPY alembic.ini ./

# ダンプスクリプトをコピー（dumper の場合）
COPY app/db/dump.py ./

# エントリポイントスクリプト
COPY docker/db-tools-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 環境変数でモードを設定
ENV DB_TOOL_MODE=$MODE

# エントリポイントスクリプトを実行
ENTRYPOINT ["/entrypoint.sh"]