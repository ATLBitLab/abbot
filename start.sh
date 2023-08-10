#!/usr/bin/bash

BASE_DIR="$HOME/telegram-gpt-bot"
source "$BASE_DIR/.env/bin/activate"
cd "$BASE_DIR/src"
python3 cli.py
