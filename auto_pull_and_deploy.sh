#!/bin/bash

# Define log file
LOG_FILE="/docker/jellyfin-automations/auto_pull_and_deploy.log"

# Add timestamp
echo "=== $(date) ===" >> "$LOG_FILE"

# Change to the repo directory
cd /docker/jellyfin-automations || { echo "Failed to change directory" >> "$LOG_FILE"; exit 1; }

# Perform git pull with full path
GIT_OUTPUT=$(/usr/bin/git pull 2>&1)
echo "$GIT_OUTPUT" >> "$LOG_FILE"

if [[ "$GIT_OUTPUT" == *"Already up to date."* ]]; then
  echo "No changes detected" >> "$LOG_FILE"
else
  echo "Changes detected. Rebuilding container..." >> "$LOG_FILE"
  /usr/bin/docker compose up -d --build >> "$LOG_FILE" 2>&1
fi
