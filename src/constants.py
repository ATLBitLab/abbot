from typing import List
from os.path import abspath

OPENAI_MODEL: str = "gpt-4-1106-preview"
THE_ARCHITECT_ID: int = 1711738045
THE_ARCHITECT_USERNAME: str = "nonni_io"
THE_ARCHITECT_HANDLE: str = f"@{THE_ARCHITECT_USERNAME}"
ABBOT_SQUAWKS: int = -1002139786317
SATOSHIS_PER_BTC: int = 100000000
NAKED_COMMANDS = ["help", "rules", "start", "stop", "unleash", "leash", "balance", "fund", "count", "status"]
HELP_MENU = f"""
Hello world 🤖

My name is Abbot. I am a bitcoin-only, AI assistant focused on bitcoin communities around the world!

My goals are simple: reduce work for bitcoin community organizers, answer bitcoin questions and entertain your community!

*About Me*
/help 📖 Read this help
/rules 📜 How to interact

*Manage Me*
/start 🏁 Start letting me chat
/stop 🛑 Stop letting me chat
/unleash 🐕 Enable cadenced responses: `/unleash 10`
/leash 🐕 Disable cadenced responses: `/leash`

*Pay Me*
/balance ⚖️ View your balance in usd and sats
/fund ⚡️ Refill your SATs: `/fund 1000 sats`

*About Us*
/status 📊 View info about started & unleashed
/count 🔢 View info about unleash cadence

Abbot is not a wallet and does not store funds
Invoices help @atlbitlab pay the bills for using Abbot

Built with ☕️🧡₿ by @atlbitlab
Est block #797812
"""

RULES: str = """To get me to respond to your messages, you must have a positive SAT balance \& take one of these actions

🤖 Tag my handle \@atl\_bitlab\_bot in your group message
🤖 Reply directly to my group message
🤖 Slide into my DMs to chat directly
🤖 Use /unleash to let me auto\-respond
⚡️ Will work for SATs\! New groups get 5k *_FREE_* sats
⚡️ To check your balance\, run /balance at any time
⚡️ Keep your SATs above 0 using /fund
⚡️ Make your group more entertaining using /unleash

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
ESCAPE_MARKDOWN_V2_CHARS = "_*()~`>+-=|{}.!"
