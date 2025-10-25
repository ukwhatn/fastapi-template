#!/bin/bash
set -euo pipefail

# Dev Environment Deployment Script
# Deploys the application to dev environment with auto-updates via Watchtower
#
# Prerequisites:
#   - SOPS and age installed
#   - age secret key at ~/.config/sops/age/keys.txt
#   - GHCR.io credentials configured
#   - Watchtower running (use setup-watchtower.sh)
#
# Usage:
#   ./scripts/deploy-dev.sh

echo "=== Dev Environment Deployment ==="
echo ""

# Check prerequisites
command -v sops >/dev/null 2>&1 || { echo "❌ sops not installed. Install: https://github.com/getsops/sops"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ docker not installed"; exit 1; }

# Check age key
if [ ! -f ~/.config/sops/age/keys.txt ]; then
    echo "⚠️  age secret key not found at ~/.config/sops/age/keys.txt"
    echo "Generate key: age-keygen -o ~/.config/sops/age/keys.txt"
    exit 1
fi

# Check if encrypted env file exists
if [ ! -f .env.dev.enc ]; then
    echo "⚠️  .env.dev.enc not found"
    echo "Create encrypted env file:"
    echo "  1. cp .env.example .env.dev"
    echo "  2. Edit .env.dev with your dev settings"
    echo "  3. sops -e .env.dev > .env.dev.enc"
    exit 1
fi

# Decrypt environment variables
echo "📝 Decrypting environment variables..."
sops -d .env.dev.enc > .env
echo "✅ Environment variables decrypted"

# Source .env to get GITHUB_REPOSITORY
source .env

# Check GITHUB credentials
if [ -z "${GITHUB_USER:-}" ] || [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "⚠️  GITHUB_USER or GITHUB_TOKEN not set in .env"
    echo "Set these variables to enable GHCR.io authentication"
    read -p "Continue without authentication? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    # Login to GHCR.io
    echo "🔐 Logging in to GHCR.io..."
    echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin
    echo "✅ GHCR.io login successful"
fi

# Set compose project name
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-fastapi-template}"
echo "📦 Project name: $COMPOSE_PROJECT_NAME"

# Check POSTGRES_HOST and display database type
POSTGRES_HOST=$(grep "^POSTGRES_HOST=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")

if [ "$POSTGRES_HOST" = "db" ] || [ "$POSTGRES_HOST" = "localhost" ]; then
    echo "📦 ローカルDB使用を検出 (POSTGRES_HOST=$POSTGRES_HOST)"
else
    echo "🌐 外部DBaaS使用を検出 (POSTGRES_HOST=$POSTGRES_HOST)"
    echo "ℹ️  db-migratorとdb-dumperは外部DBに接続します"
fi

# Pull latest images
echo ""
echo "📥 Pulling latest images..."
ENV=dev make compose:pull

# Start services
echo ""
echo "🚀 Starting services..."
ENV=dev make compose:up

# Wait for health check
echo ""
echo "🏥 Waiting for health check..."
MAX_WAIT=60
ELAPSED=0
INTERVAL=5

while [ $ELAPSED -lt $MAX_WAIT ]; do
    if ENV=dev make compose:ps | grep -q "healthy"; then
        echo "✅ Services are healthy!"
        break
    fi

    echo "⏳ Waiting... (${ELAPSED}s/${MAX_WAIT}s)"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "⚠️  Health check timeout"
    echo "Check logs: ENV=dev make compose:logs"
fi

# Display status
echo ""
echo "=== Deployment Status ==="
ENV=dev make compose:ps

# Check if Watchtower is running
echo ""
if docker ps --format '{{.Names}}' | grep -q '^watchtower$'; then
    echo "✅ Watchtower is running (auto-updates enabled)"
else
    echo "⚠️  Watchtower is not running"
    echo "Run: ./scripts/setup-watchtower.sh"
fi

# Cleanup
echo ""
echo "🧹 Cleaning up..."
rm -f .env
echo "✅ Temporary .env removed"

echo ""
echo "✅ Dev deployment complete!"
echo ""
echo "Next steps:"
echo "  - View logs: make dev:logs"
echo "  - Check Watchtower: docker logs watchtower -f"
echo "  - Stop services: make dev:down"
