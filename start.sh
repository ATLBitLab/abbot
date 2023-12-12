#!/usr/bin/bash
source "$HOME/environments/.abbot_venv/bin/activate"
BASE_DIR="$HOME/abbot"
cd "$BASE_DIR"
pip install -r requirements.txt
python3 src/main.py --telegram --log
