# syntax=docker/dockerfile:1

# ========================================
# フロントエンドビルダーステージ
# ========================================
FROM node:22-slim AS frontend-builder

WORKDIR /frontend

# Corepackを有効化してpnpmを使用
RUN corepack enable

# package.json と pnpm-lock.yaml をコピー（キャッシュ最適化）
COPY frontend/package.json frontend/pnpm-lock.yaml ./

# pnpm fetchでロックファイルからパッケージを取得（キャッシュ層の最適化）
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm fetch --frozen-lockfile

# 依存関係をインストール
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile --offline

# フロントエンドのソースコードをコピー
COPY frontend/ ./

# ビルド実行
RUN pnpm run build

# ========================================
# バックエンドビルダーステージ
# ========================================
FROM ghcr.io/astral-sh/uv:0.9.5-python3.13-trixie-slim AS backend-builder

WORKDIR /app

# UV_COMPILE_BYTECODE: 起動時間を30-50%改善するためバイトコードコンパイルを有効化
# UV_LINK_MODE: マルチステージビルドでのコピー時の一貫性を保つためcopyモードを使用
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# psycopg2-binaryのビルドに必要（libpq-dev, gcc）
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        make && \
    rm -rf /var/lib/apt/lists/*

# pyproject.toml/uv.lockをbind mountで参照し、レイヤーに含めず依存関係を解決
# キャッシュマウントでuv's cache（/root/.cache/uv）を永続化し、再ビルド時に高速化
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project

COPY . /app

# --no-editableで本番環境用の非編集可能インストール（パフォーマンス最適化）
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# ========================================
# ランタイムステージ
# ========================================
FROM ghcr.io/astral-sh/uv:0.9.5-python3.13-trixie-slim AS runtime

# PYTHONUNBUFFERED: コンテナログでリアルタイム出力を確保するためバッファリング無効化
# PYTHONDONTWRITEBYTECODE: builderステージで既にバイトコード化済みのため不要な.pycの生成を抑制
# PYTHONPATH: appモジュールを正しく解決するためにプロジェクトルートを設定
ENV TZ=Asia/Tokyo \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/usr/src \
    PATH="/app/.venv/bin:$PATH"

# psycopg2の実行時依存ライブラリ（libpq5）とヘルスチェック用curl
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl && \
    rm -rf /var/lib/apt/lists/*

# 非rootユーザーで実行
RUN adduser --disabled-password --gecos "" nonroot

WORKDIR /usr/src

# バックエンドビルド成果物をコピー
COPY --from=backend-builder --chown=nonroot:nonroot /app /app

# フロントエンドビルド成果物をコピー
COPY --from=frontend-builder --chown=nonroot:nonroot /frontend/dist /usr/src/frontend/dist

# 開発時のホットリロードのため./appをマウント（compose.yml参照）
COPY --chown=nonroot:nonroot ./app /usr/src/app

USER nonroot
