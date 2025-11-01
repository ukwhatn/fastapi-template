#!/bin/bash
set -euo pipefail

# Initial Server Setup Script for GitHub Actions + SSH Deploy
#
# Prerequisites:
#   - SOPS and age installed
#   - age secret key at ~/.config/sops/age/keys.txt
#   - Docker & Docker Compose installed
#
# Usage:
#   ./scripts/setup-server.sh stg
#   ./scripts/setup-server.sh prod

echo "=== FastAPI Template Server Setup ==="
echo ""

# 引数チェック
if [ $# -eq 0 ]; then
    echo "Error: Environment argument required (stg or prod)"
    echo "Usage: ./scripts/setup-server.sh {stg|prod}"
    exit 1
fi

ENV=$1
REPO_NAME="fastapi-template"
REPO_URL="https://github.com/ukwhatn/fastapi-template.git"

if [ "$ENV" != "stg" ] && [ "$ENV" != "prod" ]; then
    echo "Error: Environment must be 'stg' or 'prod'"
    exit 1
fi

echo "Environment: $ENV"
echo ""

# 前提条件チェック
command -v sops >/dev/null 2>&1 || { echo "❌ sops not installed"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ docker not installed"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "❌ git not installed"; exit 1; }

# age鍵チェック
if [ ! -f ~/.config/sops/age/keys.txt ]; then
    echo "❌ age secret key not found at ~/.config/sops/age/keys.txt"
    echo "Generate key: age-keygen -o ~/.config/sops/age/keys.txt"
    exit 1
fi

# リポジトリが既に存在するかチェック
if [ -d "$REPO_NAME" ]; then
    echo "⚠️  Directory $REPO_NAME already exists"
    read -p "Remove and re-clone? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$REPO_NAME"
    else
        echo "Aborted."
        exit 0
    fi
fi

# sparse checkoutでクローン
echo "📥 Cloning repository with sparse checkout..."
git clone --filter=blob:none --sparse "$REPO_URL"
cd "$REPO_NAME"

# 必要なファイルのみチェックアウト
echo "📝 Setting up sparse checkout..."
git sparse-checkout set \
    "compose.$ENV.yml" \
    ".env.$ENV.enc" \
    ".sops.yaml" \
    "Makefile" \
    "newrelic.ini"

echo "✅ Sparse checkout complete"
echo ""

# 復号化
echo "🔓 Decrypting .env.$ENV.enc..."
sops -d ".env.$ENV.enc" > .env
echo "✅ Environment variables decrypted"
echo ""

# .envを読み込み
source .env

# GITHUB認証情報チェック
if [ -z "${GITHUB_USER:-}" ] || [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "❌ GITHUB_USER or GITHUB_TOKEN not set in .env"
    echo "These are required for GHCR.io authentication"
    exit 1
fi

# GHCRログイン
echo "🔐 Logging in to GHCR.io..."
echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin
echo "✅ GHCR.io login successful"
echo ""

# 初回起動
echo "🚀 Starting services for the first time..."
ENV=$ENV make compose:pull
ENV=$ENV make compose:up

echo ""
echo "✅ Server setup complete!"
echo ""
echo "Next steps:"
echo "  - Check service status: ENV=$ENV make compose:ps"
echo "  - View logs: ENV=$ENV make compose:logs"
echo "  - GitHub Actions will automatically deploy on push to ${ENV == 'stg' ? 'develop' : 'main'}"
echo ""
echo "⚠️  IMPORTANT: Keep .env file secure and never commit it to git!"
