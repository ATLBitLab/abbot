#!/usr/bin/bash

BASE_DIR="$HOME/abbot"
source "$BASE_DIR/.env/bin/activate"
cd "$BASE_DIR/src"
python3 main.py
