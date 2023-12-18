from typing import List


CONFIG_JSON_FILEPATH: str = "src/data/config.json"
OPENAI_MODEL: str = "gpt-4-1106-preview"
THE_ARCHITECT_ID: int = 1711738045
THE_ARCHITECT_USERNAME: str = "nonni_io"
THE_ARCHITECT_HANDLE: str = f"@{THE_ARCHITECT_USERNAME}"
ABBOT_SQUAWKS: int = -1002139786317
SATOSHIS_PER_BTC: int = 100000000
HELP_MENU = """You can interact with me by sending these commands:

*About Me*
/help \- return detailed command list and how to use them
/rules \- return rules list for how to interact with Abbot

*Manage Me*
/start \- start Abbot in group
/stop \- stops Abbot in group

*Manage Paying Me*
/balance \- return group balance in USD and SATs
/fund \- return an invoice ⚡️ to topup your balance
/cancel \- cancel the most recently requested invoice\n"""

RULES: str = """To get me to respond to your messages, you must have a positive SAT balance \& take one of these actions

🤖 Tag my handle \@atl\_bitlab\_bot in your group message
🤖 Reply directly to my group message
🤖 Slide into my DMs to chat directly
⚡️ I work for SATs\! New groups get 50\,000 *_FREE_* sats
⚡️ To keep your SATs above 0, use /fund to get an invoice

Want more details about me? Checkout my website: https\:\/\/abbot\.atlbitlab\.com\/
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
