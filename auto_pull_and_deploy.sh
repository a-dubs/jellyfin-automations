#!/bin/bash
git_pull_result=$(git pull)
if [[ $git_pull_result == *"Already up to date."* ]]; then
  echo "No changes"
else
  echo "Changes detected. Rebuiding container"
  docker compose up -d --build
fi