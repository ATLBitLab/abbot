from bot_args import DEV_MODE, TEST_MODE

from lib.utils import try_get
from lib.utils import json_loader, try_get
from lib.abbot.env import BOT_TELEGRAM_TOKEN, TEST_BOT_TELEGRAM_HANDLE

SATOSHIS_PER_BTC: int = 100000000
CONFIG_JSON_FILEPATH: str = "src/data/config.json"

ORG_CONFIG = json_loader(CONFIG_JSON_FILEPATH, "org")
BOT_CONFIG = json_loader(CONFIG_JSON_FILEPATH, "bot")

# Bot Static Data
ORG_NAME = try_get(ORG_CONFIG, "name")
ORG_SLUG = try_get(ORG_CONFIG, "slug")
ORG_ADMINS = try_get(ORG_CONFIG, "admins")
ORG_TYPE = try_get(ORG_CONFIG, "type")
ORG_DESCRIPTION = try_get(ORG_CONFIG, "description")
ORG_BUSINESS_MODEL = try_get(ORG_CONFIG, "business_model")
ORG_INPUT_TOKEN_COST = try_get(ORG_BUSINESS_MODEL, "input_token_cost")
ORG_OUTPUT_TOKEN_COST = try_get(ORG_BUSINESS_MODEL, "output_token_cost")
ORG_PER_TOKEN_COST_DIV = try_get(ORG_BUSINESS_MODEL, "per_token_cost_divisor")
ORG_TOKEN_COST_MULT = try_get(ORG_BUSINESS_MODEL, "token_cost_multiplier")
ORG_CHAT_ID = try_get(ORG_CONFIG, "chat_id")
ORG_CHAT_TITLE = try_get(ORG_CONFIG, "chat_title")
ORG_BLOCK_HEIGHT = try_get(ORG_CONFIG, "block_height")
ORG_LOCATION = try_get(ORG_CONFIG, "location")
ORG_HEX_PUBKEY = try_get(ORG_CONFIG, "hex_pubkey")
ORG_WEBSITE = try_get(ORG_CONFIG, "website")
ORG_GITHUB = try_get(ORG_CONFIG, "github")
ORG_TELEGRAM = try_get(ORG_CONFIG, "telegram")
ORG_TELEGRAM_HANDLE = ORG_TELEGRAM.replace("https://t.me/", "@")
ORG_TWITTER = try_get(ORG_CONFIG, "twitter")
ORG_TWITTER_HANDLE = ORG_TELEGRAM.replace("https://twitter.com/", "@")

# Bot Static Data
BOT_NAME = try_get(BOT_CONFIG, "name")
BOT_SHORT_FOR = try_get(BOT_CONFIG, "short_for")
BOT_JOB = try_get(BOT_CONFIG, "job")
<<<<<<< Updated upstream
=======
BOT_SQUAWKS = try_get(BOT_CONFIG, "")
BOT_HELP_MENU = try_get(BOT_CONFIG, "")
BOT_INTRODUCTION = try_get(BOT_CONFIG, "")
BOT_OPENAI_MODEL = try_get(BOT_CONFIG, "")
BOT_RULES = try_get(BOT_CONFIG, "")
'''
OPENAI_MODEL: str = ""
THE_ARCHITECT_ID: int = 1711738045
THE_ARCHITECT_USERNAME: str = "nonni_io"
THE_ARCHITECT_HANDLE: str = f"@{THE_ARCHITECT_USERNAME}"

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
/cancel \- cancel the most recently requested invoice"""
RULES = """To get me to respond to your messages, you must have a positive SAT balance \& take one of these actions

🤖 Tag my handle \@atl\_bitlab\_bot in your group message
🤖 Reply directly to my group message
🤖 Slide into my DMs to chat directly
⚡️ I work for SATs\! New groups get 50\,000 *_FREE_* sats
⚡️ To keep your SATs above 0, use /fund to get an invoice

Want more details about me? Checkout my website: https\:\/\/abbot\.atlbitlab\.com\/"""
INTRODUCTION = f"""What up fam, the name\'s Abbot but you can think of me as your go\-to guide for all things Bitcoin 🟠\n\n{RULES}\nNow\, enough with the rules\! Let\'s dive into the world of Bitcoin together\! Ready\. Set\. Stack Sats\! 🚀"""
RELAYS = [
    "wss://relay1.nostrchat.io",
    "wss://relay2.nostrchat.io",
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.primal.net",
    "wss://relay.snort.social",
    "wss://nostr.atlbitlab.com",
]
'''


>>>>>>> Stashed changes
BOT_TELEGRAM = try_get(BOT_CONFIG, "telegram")
BOT_TELEGRAM_USERNAME = try_get(BOT_TELEGRAM, "username")
BOT_TELEGRAM_USER_ID = try_get(BOT_TELEGRAM, "user_id")
BOT_TELEGRAM_CONTEXT = try_get(BOT_TELEGRAM, "context")
BOT_TELEGRAM_SUPPORT_CONTACT = try_get(BOT_TELEGRAM, "support_contact")
BOT_LIGHTNING = try_get(BOT_CONFIG, "lightning")
BOT_LIGHTNING_ADDRESS = try_get(BOT_LIGHTNING, "address")
BOT_NOSTR = try_get(BOT_CONFIG, "nostr")
BOT_NOSTR_PK = try_get(BOT_NOSTR, "pk")
BOT_NOSTR_NPUB = try_get(BOT_NOSTR, "npub")
BOT_SYSTEM = try_get(BOT_CONFIG, "system")
BOT_SYSTEM_DM = try_get(BOT_SYSTEM, "dm")
BOT_SYSTEM_GROUP = try_get(BOT_SYSTEM, "group")
BOT_SYSTEM_CORE = try_get(BOT_SYSTEM, "core")
BOT_DIRECTIVE = try_get(BOT_SYSTEM, "directive")

# Bot Dynamic + Static Data
BOT_NAME = f"t{BOT_NAME}" if TEST_MODE or DEV_MODE else BOT_NAME
BOT_TELEGRAM_USERNAME = f"test_{BOT_TELEGRAM_USERNAME}" if TEST_MODE or DEV_MODE else BOT_TELEGRAM_USERNAME
BOT_TELEGRAM_HANDLE = f"@{BOT_TELEGRAM_USERNAME}"
BOT_TELEGRAM_TOKEN = TEST_BOT_TELEGRAM_HANDLE if TEST_MODE or DEV_MODE else BOT_TELEGRAM_TOKEN

BOT_INTRO = f"Your name is {BOT_NAME}, which is short for {BOT_SHORT_FOR}, your telegram handle is {BOT_TELEGRAM_HANDLE}. You answer to Abbot. You are part of {ORG_NAME} - {ORG_DESCRIPTION} and you are an expert in all things {ORG_LOCATION}, {ORG_NAME} and Bitcoin and Lightning Network. {BOT_DIRECTIVE}"
BOT_SYSTEM_CORE_DMS = f"{BOT_SYSTEM_DM}. {BOT_INTRO}. {BOT_SYSTEM_CORE}"
BOT_SYSTEM_CORE_GROUPS = f"{BOT_SYSTEM_GROUP}. {BOT_INTRO}. {BOT_SYSTEM_CORE}"

BOT_SYSTEM_OBJECT_GROUPS = {"role": "system", "content": BOT_SYSTEM_CORE_GROUPS}
BOT_SYSTEM_OBJECT_DMS = {"role": "system", "content": BOT_SYSTEM_CORE_DMS}
BOT_GROUP_CONFIG_DEFAULT = {"started": False, "introduced": False, "unleashed": False, "count": None}
BOT_GROUP_CONFIG_STARTED = {"started": True, "introduced": True, "unleashed": False, "count": None}
