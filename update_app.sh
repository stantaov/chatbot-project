#!/bin/bash

set -e  # Exit on any error

date
echo "Updating Python application on VM..."

REPO_URL="github.com/stantaov/chatbot-project.git"
BRANCH="main"
GITHUB_TOKEN=$TOKEN  # Passed securely via protectedSettings
HOME_DIR=$(eval echo ~$USER)
APP_DIR="$HOME_DIR/chatbot-project"

# Update code
if [ -d "$APP_DIR" ]; then
    sudo -u azureuser bash -c "cd $APP_DIR && git fetch origin && git reset --hard origin/$BRANCH"
else
    sudo -u azureuser git clone -b "$BRANCH" "https://${GITHUB_TOKEN}@${REPO_URL}" "$APP_DIR"
fi

# Install dependencies
sudo -u azureuser $HOME_DIR/miniconda3/envs/project/bin/pip install --upgrade pip
sudo -u azureuser $HOME_DIR/miniconda3/envs/project/bin/pip install -r "${APP_DIR}/requirements.txt"

# Restart services and check status
sudo systemctl restart frontend
sudo systemctl is-active --quiet frontend || echo "Frontend failed to start"

echo "Python application update completed!"
