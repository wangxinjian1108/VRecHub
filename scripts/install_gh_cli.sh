#!/usr/bin/env bash
set -euo pipefail

mkdir -p /usr/share/keyrings /etc/apt/sources.list.d

curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | tee /etc/apt/sources.list.d/github-cli.list

apt-get update
apt-get install -y gh

echo "gh $(gh --version | head -1) installed successfully."
echo "Run 'gh auth login' to authenticate."
