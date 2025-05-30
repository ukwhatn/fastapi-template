FROM python:3.13.3-slim

# timezone設定
ENV TZ=Asia/Tokyo

# 作業ディレクトリ設定
WORKDIR /app

# システム依存パッケージインストール
RUN apt update && \
    apt upgrade -y && \
    apt install -y libpq-dev gcc make curl && \
    pip install --upgrade pip

# 依存関係ファイルをコピー
COPY pyproject.toml uv.lock ./

# uvのインストールと依存関係インストール
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    export PATH="/root/.local/bin:$PATH" && \
    uv sync --group server --group db --frozen --no-dev

# 非rootユーザーを作成
RUN adduser --disabled-password --gecos "" nonroot
RUN chown -R nonroot:nonroot /app

# 非rootユーザーに切り替え
USER nonroot