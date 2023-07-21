#!/usr/bin/env bash
source .venv/bin/activate
pip install -r requirements.txt
sudo cp atlbitlab-bot.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable atlbitlab-bot
sudo systemctl start atlbitlab-bot
sudo systemctl status atlbitlab-bot
sudo systemctl start atlbitlab-bot
sudo journalctl -u atlbitlab-bot | tail
echo "Done!"
exit 0