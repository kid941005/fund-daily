#!/bin/bash
# Backup script for Fund Daily CI/CD
# Creates a timestamped backup before Docker build

set -e

BACKUP_DIR="${BACKUP_DIR:-/tmp/fund-daily-backup}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/fund-daily-${TIMESTAMP}"

echo "=== Fund Daily Backup Script ==="
echo "Timestamp: ${TIMESTAMP}"
echo "Backup path: ${BACKUP_PATH}"

# Create backup directory
mkdir -p "${BACKUP_PATH}"

# Backup critical files
if [ -d "/home/kid/fund-daily" ]; then
    echo "Backing up configuration files..."
    # Backup config, but exclude node_modules, __pycache__, .git, etc.
    rsync -a --exclude='node_modules' --exclude='__pycache__' --exclude='.git' --exclude='*.pyc' --exclude='dist' --exclude='.venv' /home/kid/fund-daily/ "${BACKUP_PATH}/fund-daily/" 2>/dev/null || true
    echo "Backup completed: ${BACKUP_PATH}"
else
    echo "Warning: /home/kid/fund-daily not found, skipping backup"
fi

echo "=== Backup Script Completed ==="
