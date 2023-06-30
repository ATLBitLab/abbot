#!/usr/bin/bash

BASE_DIR="$HOME/telegram-gpt-bot"
source "$BASE_DIR/.venv/bin/activate"
cd "$BASE_DIR/src"
$BASE_DIR/.venv/bin/python cli.py
