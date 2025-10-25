#!/bin/bash
set -euo pipefail

# Production Environment Deployment Script
# Deploys the application to production environment with auto-updates via Watchtower
#
# Prerequisites:
#   - SOPS and age installed
#   - age secret key at ~/.config/sops/age/keys.txt
#   - GHCR.io credentials configured
#   - Watchtower running (use setup-watchtower.sh)
#
# Usage:
#   ./scripts/deploy-prod.sh

echo "=== Production Environment Deployment ==="
echo ""
echo "⚠️  WARNING: This will deploy to PRODUCTION environment"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# Check prerequisites
command -v sops >/dev/null 2>&1 || { echo "❌ sops not installed. Install: https://github.com/getsops/sops"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ docker not installed"; exit 1; }

# Check age key
if [ ! -f ~/.config/sops/age/keys.txt ]; then
    echo "❌ age secret key not found at ~/.config/sops/age/keys.txt"
    echo "Generate key: age-keygen -o ~/.config/sops/age/keys.txt"
    exit 1
fi

# Check if encrypted env file exists
if [ ! -f .env.prod.enc ]; then
    echo "❌ .env.prod.enc not found"
    echo "Create encrypted env file:"
    echo "  1. cp .env.example .env.prod"
    echo "  2. Edit .env.prod with your production settings"
    echo "  3. sops -e .env.prod > .env.prod.enc"
    exit 1
fi

# Decrypt environment variables
echo "📝 Decrypting environment variables..."
sops -d .env.prod.enc > .env
echo "✅ Environment variables decrypted"

# Source .env to get GITHUB_REPOSITORY
source .env

# Check GITHUB credentials
if [ -z "${GITHUB_USER:-}" ] || [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "❌ GITHUB_USER or GITHUB_TOKEN not set in .env"
    echo "These are required for production deployment"
    exit 1
fi

# Login to GHCR.io
echo "🔐 Logging in to GHCR.io..."
echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin
echo "✅ GHCR.io login successful"

# Set compose project name
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-fastapi-template}"
echo "📦 Project name: $COMPOSE_PROJECT_NAME"

# Check POSTGRES_HOST to determine if local DB is needed
PROFILE_ARGS=""
POSTGRES_HOST=$(grep "^POSTGRES_HOST=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")

if [ "$POSTGRES_HOST" = "db" ] || [ "$POSTGRES_HOST" = "localhost" ]; then
    echo "📦 ローカルDB使用を検出 (POSTGRES_HOST=$POSTGRES_HOST)"
    PROFILE_ARGS="--profile local-db"
else
    echo "🌐 外部DBaaS使用を検出 (POSTGRES_HOST=$POSTGRES_HOST)"
    echo "ℹ️  db-migratorとdb-dumperは外部DBに接続します"
fi

# Pull latest images
echo ""
echo "📥 Pulling latest images..."
docker compose -f compose.prod.yml $PROFILE_ARGS pull

# Final confirmation
echo ""
echo "Ready to deploy with tag: latest"
read -p "Proceed with deployment? (yes/no): " FINAL_CONFIRM

if [ "$FINAL_CONFIRM" != "yes" ]; then
    echo "Aborted."
    rm -f .env
    exit 0
fi

# Start services
echo ""
echo "🚀 Starting services..."
docker compose -f compose.prod.yml $PROFILE_ARGS up -d

# Wait for health check
echo ""
echo "🏥 Waiting for health check..."
MAX_WAIT=60
ELAPSED=0
INTERVAL=5

while [ $ELAPSED -lt $MAX_WAIT ]; do
    if docker compose -f compose.prod.yml $PROFILE_ARGS ps | grep -q "healthy"; then
        echo "✅ Services are healthy!"
        break
    fi

    echo "⏳ Waiting... (${ELAPSED}s/${MAX_WAIT}s)"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "⚠️  Health check timeout"
    echo "Check logs: docker compose -f compose.prod.yml $PROFILE_ARGS logs"
    echo ""
    read -p "Rollback deployment? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Rolling back..."
        docker compose -f compose.prod.yml $PROFILE_ARGS down
        rm -f .env
        exit 1
    fi
fi

# Display status
echo ""
echo "=== Deployment Status ==="
docker compose -f compose.prod.yml $PROFILE_ARGS ps

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
echo "✅ Production deployment complete!"
echo ""
echo "Next steps:"
echo "  - View logs: docker compose -f compose.prod.yml $PROFILE_ARGS logs -f"
echo "  - Check Watchtower: docker logs watchtower -f"
echo "  - Monitor health: docker compose -f compose.prod.yml $PROFILE_ARGS ps"
echo ""
echo "⚠️  IMPORTANT: Monitor the application for the next few minutes"
