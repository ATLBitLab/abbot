#!/usr/bin/env bash

setup_env () {
    echo "Source .env"
    # source .env/bin/activate
    echo "Install requirements.txt"
    # pip install -r requirements.txt
    echo "Copy abbot.server to system"
    # sudo cp abbot.service /etc/systemd/system
}

daemon_start () {
    echo "Reload system daemon"
    # sudo systemctl daemon-reload
    echo "Enable abbot"
    # sudo systemctl enable abbot
    echo "Start abbot"
    # sudo systemctl start abbot
}

daemon_status () {
    echo "Check abbot status"
    # sudo systemctl status abbot
    echo "Print system logs"
    # sudo journalctl -u abbot | tail
}

setup_env && \
daemon_start && \
daemon_status && \
echo "Abbot is live!" && \
exit 0