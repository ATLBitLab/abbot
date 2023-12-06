#!/usr/bin/env bash

if which brew > /dev/null; then
    echo "Homebrew is already installed. Continuing"
else
    read -p "No Homebrew. You need Homebrew to continue. Install Homebrew? [y/N]" INSTALL_HOMEBREW
    if [[ $INSTALL_HOMEBREW =~ ^(y|Y)$ ]]; then
        echo "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        echo "Homebrew installation skipped."
        exit 1
    fi
fi

# Install MongoDB
echo "Installing MongoDB..."
brew tap mongodb/brew
brew install mongodb-community

# Start MongoDB
echo "Starting MongoDB..."
brew services start mongodb/brew/mongodb-community
