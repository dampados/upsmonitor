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
PROJECT_DIR="/opt/${PROJECT_NAME}"

# Remote target from .env
TARGET="${TARGET_USER}@${TARGET_IP}"
SSH_CMD="ssh -p ${TARGET_PORT} ${TARGET}"

echo "🚀 Deploying ${PROJECT_NAME}..."

# Wipe remote directory (except venv)
${SSH_CMD} "sudo find ${PROJECT_DIR} -mindepth 1 -maxdepth 1 ! -name 'venv' -exec rm -rf {} +"

# Sync app files (excluding venv)
rsync -avz --exclude venv -e "ssh -p ${TARGET_PORT}" app/ ${TARGET}:${PROJECT_DIR}/

# Restart service
${SSH_CMD} "sudo systemctl restart ${PROJECT_NAME}"

echo "✅ Deploy complete."
${SSH_CMD} "sudo systemctl status ${PROJECT_NAME} --no-pager"