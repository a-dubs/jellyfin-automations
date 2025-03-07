# bash script that automatically pulls from a git repository
# and builds and starts new docker container if there are changes

#!/bin/bash set -e
git_pull_result=$(git pull)
if [[ $git_pull_result == *"Already up to date."* ]]; then
  echo "No changes"
else
  echo "Changes detected. Rebuiding container"
  docker compose up -d --build
fi