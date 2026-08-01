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

echo "📦 Installing project: ${PROJECT_NAME} to ${TARGET}"

# Create project directory
${SSH_CMD} "sudo mkdir -p ${PROJECT_DIR}"

# Copy app files (everything from app/ except venv)
${SSH_CMD} "sudo rm -rf ${PROJECT_DIR}/*"
rsync -avz --exclude venv -e "ssh -p ${TARGET_PORT}" app/ ${TARGET}:${PROJECT_DIR}/

# Create venv and install deps on remote
${SSH_CMD} "cd ${PROJECT_DIR} && python3 -m venv venv"
${SSH_CMD} "cd ${PROJECT_DIR} && venv/bin/pip install -r requirements.txt"

# Copy service file
scp -P ${TARGET_PORT} unit/${SERVICE_NAME} ${TARGET}:/tmp/
${SSH_CMD} "sudo mv /tmp/${SERVICE_NAME} /etc/systemd/system/${SERVICE_NAME}"
${SSH_CMD} "sudo chmod 644 /etc/systemd/system/${SERVICE_NAME}"

# Reload systemd, enable and start
${SSH_CMD} "sudo systemctl daemon-reload"
${SSH_CMD} "sudo systemctl enable ${SERVICE_NAME}"
${SSH_CMD} "sudo systemctl start ${SERVICE_NAME}"

echo "✅ Install complete. Status:"
${SSH_CMD} "sudo systemctl status ${SERVICE_NAME} --no-pager"