# syntax=docker/dockerfile:1

# ========================================
# ビルダーステージ
# ========================================
FROM python:3.14-slim-trixie AS builder

# uvのインストール（再現性のため特定バージョンに固定）
COPY --from=ghcr.io/astral-sh/uv:0.5.15 /uv /uvx /bin/

# 作業ディレクトリ設定
WORKDIR /app

# uv環境変数の設定
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# ビルドに必要なシステム依存パッケージをインストール
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        make && \
    rm -rf /var/lib/apt/lists/*

# 依存関係ファイルを先にコピー（レイヤーキャッシングの最適化）
COPY pyproject.toml uv.lock ./

# 依存関係のみをインストール（プロジェクト本体は除外）
# 依存関係が変更されない限り、このレイヤーはキャッシュされる
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --group server --group db --frozen --no-dev --no-install-project

# プロジェクト全体をコピー
COPY . .

# プロジェクト本体をインストール
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --group server --group db --frozen --no-dev

# ========================================
# ランタイムステージ
# ========================================
FROM python:3.14-slim-trixie AS runtime

# タイムゾーン設定
ENV TZ=Asia/Tokyo

# ランタイムに必要なシステム依存パッケージをインストール
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl && \
    rm -rf /var/lib/apt/lists/*

# 非rootユーザーを作成
RUN adduser --disabled-password --gecos "" nonroot

# 作業ディレクトリ設定
WORKDIR /usr/src

# ビルダーから仮想環境をコピー
COPY --from=builder --chown=nonroot:nonroot /app/.venv /usr/src/.venv

# アプリケーションコードをコピー
COPY --chown=nonroot:nonroot ./app /usr/src/app

# 仮想環境を使用するようにPATHを設定
ENV PATH="/usr/src/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# 非rootユーザーに切り替え
USER nonroot
