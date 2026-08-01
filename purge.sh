#!/bin/bash
set -e

# Load .env
if [ -f .env ]; then
    source .env
else
    echo "❌ .env file not found"
    exit 1
fi

# Get project name from current directory
PROJECT_NAME=$(basename "$PWD")
SERVICE_NAME="${PROJECT_NAME}.service"
PROJECT_DIR="/opt/${PROJECT_NAME}"

# Remote target from .env
TARGET="${TARGET_USER}@${TARGET_IP}"
SSH_CMD="ssh -p ${TARGET_PORT} ${TARGET}"

echo "🧹 Purging project: ${PROJECT_NAME} from ${TARGET}"

# Stop and disable service
${SSH_CMD} "sudo systemctl stop ${SERVICE_NAME} 2>/dev/null || true"
${SSH_CMD} "sudo systemctl disable ${SERVICE_NAME} 2>/dev/null || true"

# Delete service file
${SSH_CMD} "sudo rm -f /etc/systemd/system/${SERVICE_NAME}"

# Reload systemd
${SSH_CMD} "sudo systemctl daemon-reload"

# Delete project directory
${SSH_CMD} "sudo rm -rf ${PROJECT_DIR}"

echo "✅ Purge complete. Nothing remains on ${TARGET}."