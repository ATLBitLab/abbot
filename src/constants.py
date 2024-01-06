from typing import List
from os.path import abspath

from lib.abbot.config import BOT_TELEGRAM_HANDLE_MD

CONFIG_JSON_FILEPATH: str = "src/data/config.json"
OPENAI_MODEL: str = "gpt-4-1106-preview"
THE_ARCHITECT_ID: int = 1711738045
THE_ARCHITECT_USERNAME: str = "nonni_io"
THE_ARCHITECT_HANDLE: str = f"@{THE_ARCHITECT_USERNAME}"
ABBOT_SQUAWKS: int = -1002139786317
SATOSHIS_PER_BTC: int = 100000000
HELP_MENU = f"""You can interact with me by sending these commands\:

*About Me*
/help{BOT_TELEGRAM_HANDLE_MD} \- returns detailed command list and how to use them
/rules{BOT_TELEGRAM_HANDLE_MD} \- returns rules list for how to interact with Abbot

*Manage Me*
/start{BOT_TELEGRAM_HANDLE_MD} \- starts Abbot in a group chat
/stop{BOT_TELEGRAM_HANDLE_MD} \- stops Abbot in group chat

*Pay Me*
/balance{BOT_TELEGRAM_HANDLE_MD} \- request group chat balance in USD & SATs
/fund{BOT_TELEGRAM_HANDLE_MD} \- request invoice to topup group chat balance ⚡️\n"""

RULES: str = """To get me to respond to your messages, you must have a positive SAT balance \& take one of these actions

🤖 Tag my handle \@atl\_bitlab\_bot in your group message
🤖 Reply directly to my group message
🤖 Slide into my DMs to chat directly
⚡️ Will work for SATs\! New groups get 50k *_FREE_* sats
⚡️ To check your balance\, run /balance at any time
⚡️ Keep your SATs above 0 using /fund

Checkout my website for more details visit my [website](https\:\/\/abbot\.atlbitlab\.com\/)
"""

INTRODUCTION: str = f"""What up fam, the name\'s Abbot but you can think of me as your go\-to guide for all things Bitcoin 🟠\n\n{RULES}\nNow\, enough with the rules\! Let\'s dive into the world of Bitcoin together\! Ready\. Set\. Stack Sats\! 🚀"""
SECONDARY_INTRODUCTION: str = """👋 Whats up, my fellow bitcoiners!? My name is Abbot! I'm part of the ATL BitLab fam - your go-to spot for all things Bitcoin and Lightning in Atlanta - and I'm here to party nakamoto-style! Consider me your bitcoin concierge. Hmu anytime by tagging me (@atl_bitlab_bot) in your post or replying to my messages. Now, let's stack some sats and chat about bitcoin! 😎💻"""
RELAYS: List[str] = [
    "wss://relay1.nostrchat.io",
    "wss://relay2.nostrchat.io",
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.primal.net",
    "wss://relay.snort.social",
    "wss://nostr.atlbitlab.com",
]
RAW_MESSAGE_JL_FILE = abspath("src/data/raw_messages.jsonl")
MATRIX_IMG_FILEPATH = abspath("src/assets/unplugging_matrix.jpg")
KOOLAID_GIF_FILEPATH = abspath("src/assets/koolaid.gif")
ESCAPE_MARKDOWN_V2_CHARS = "_*[]()~`>#+-=|{}.!"
