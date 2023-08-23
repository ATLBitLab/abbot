#!/usr/bin/env bash
source .venv/bin/activate
pip install -r requirements.txt
sudo cp abbot.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable abbot
sudo systemctl start abbot
sudo systemctl status abbot
sudo systemctl start abbot
sudo journalctl -u abbot | tail
echo "Done!"
exit 0