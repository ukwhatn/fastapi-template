#!/bin/bash
set -euo pipefail

# Watchtower Setup Script
# Sets up Watchtower with label-based control and automatic self-updates
#
# Usage:
#   ./scripts/setup-watchtower.sh

echo "=== Watchtower Setup ==="
echo ""

# Check if Watchtower is already running
if docker ps -a --format '{{.Names}}' | grep -q '^watchtower$'; then
    echo "⚠️  Watchtower container already exists"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    echo "Stopping and removing existing Watchtower..."
    docker stop watchtower || true
    docker rm watchtower || true
fi

# Environment selection
echo "Select environment:"
echo "  1) dev"
echo "  2) prod"
read -p "Enter choice (1-2): " ENV_CHOICE

case $ENV_CHOICE in
    1)
        ENV_NAME="dev"
        IMAGE_TAG="develop"
        ;;
    2)
        ENV_NAME="prod"
        IMAGE_TAG="latest"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

# Notification URL (Shoutrrr format)
echo ""
echo "Enter notification URL (leave empty to skip):"
echo "  Discord: discord://token@id"
echo "  Slack: slack://token@channel"
read -p "URL: " NOTIFICATION_URL

# Poll interval (default: 600 seconds = 10 minutes)
POLL_INTERVAL="${WATCHTOWER_POLL_INTERVAL:-600}"

# Build Watchtower command
WATCHTOWER_CMD="docker run -d \
  --name watchtower \
  --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e WATCHTOWER_POLL_INTERVAL=$POLL_INTERVAL \
  -e WATCHTOWER_CLEANUP=true \
  -e WATCHTOWER_LABEL_ENABLE=true \
  -e WATCHTOWER_INCLUDE_RESTARTING=true \
  -e WATCHTOWER_ROLLING_RESTART=true"

# Add notification if provided
if [ -n "$NOTIFICATION_URL" ]; then
    WATCHTOWER_CMD="$WATCHTOWER_CMD \
  -e WATCHTOWER_NOTIFICATIONS=shoutrrr \
  -e WATCHTOWER_NOTIFICATION_URL='$NOTIFICATION_URL'"
fi

# Add self-update prevention label
WATCHTOWER_CMD="$WATCHTOWER_CMD \
  -l com.centurylinklabs.watchtower.enable=false \
  containrrr/watchtower:latest"

# Start Watchtower
echo ""
echo "Starting Watchtower..."
eval $WATCHTOWER_CMD

# Wait for container to start
sleep 2

if docker ps --format '{{.Names}}' | grep -q '^watchtower$'; then
    echo "✅ Watchtower started successfully!"
else
    echo "❌ Failed to start Watchtower"
    exit 1
fi

# Setup cron for weekly self-update
echo ""
echo "Setting up weekly self-update cron..."

CRON_SCRIPT="/etc/cron.weekly/update-watchtower"
CRON_CONTENT='#!/bin/bash
# Watchtower self-update script
# Runs weekly to update Watchtower itself

LOG_FILE="/var/log/watchtower-update.log"

{
    echo "=== Watchtower Update - $(date) ==="

    # Pull latest image
    echo "Pulling latest Watchtower image..."
    docker pull containrrr/watchtower:latest

    # Stop and remove old container
    echo "Stopping Watchtower..."
    docker stop watchtower || true
    docker rm watchtower || true

    # Restart with same configuration
    echo "Restarting Watchtower..."
    docker start watchtower 2>/dev/null || {
        echo "Failed to start (container removed), recreating..."
        # Re-run setup script
        cd '"$(pwd)"' && ./scripts/setup-watchtower.sh --non-interactive
    }

    # Cleanup old images
    docker image prune -f --filter "dangling=true"

    echo "✅ Watchtower update completed"
    echo ""
} >> "$LOG_FILE" 2>&1
'

# Create cron script
if [ -w /etc/cron.weekly ]; then
    echo "$CRON_CONTENT" | sudo tee "$CRON_SCRIPT" > /dev/null
    sudo chmod +x "$CRON_SCRIPT"
    echo "✅ Cron job created at $CRON_SCRIPT"
else
    echo "⚠️  Cannot write to /etc/cron.weekly (need sudo)"
    echo "Manual cron setup required. Save this to $CRON_SCRIPT:"
    echo "$CRON_CONTENT"
fi

# Display status
echo ""
echo "=== Watchtower Configuration ==="
echo "  Environment: $ENV_NAME"
echo "  Image tag: $IMAGE_TAG"
echo "  Poll interval: ${POLL_INTERVAL}s"
if [ -n "$NOTIFICATION_URL" ]; then
    echo "  Notifications: Enabled"
else
    echo "  Notifications: Disabled"
fi
echo ""
echo "=== Container Status ==="
docker ps --filter "name=watchtower" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Deploy your project: make dev:deploy or make prod:deploy"
echo "  2. Check Watchtower logs: docker logs watchtower -f"
echo "  3. Verify cron: sudo cat /var/log/watchtower-update.log"
