from cli_args import DEV_MODE, TEST_MODE

from lib.utils import try_get
from lib.utils import json_loader, try_get
from constants import CONFIG_JSON_FILEPATH
from lib.abbot.env import BOT_TELEGRAM_TOKEN, TEST_BOT_TELEGRAM_HANDLE

ORG_CONFIG = json_loader(CONFIG_JSON_FILEPATH, "org")
ORG_NAME = try_get(ORG_CONFIG, "name")
ORG_SLUG = try_get(ORG_CONFIG, "slug")
ORG_ADMINS = try_get(ORG_CONFIG, "admins")
ORG_TYPE = try_get(ORG_CONFIG, "type")
ORG_DESCRIPTION = try_get(ORG_CONFIG, "description")
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

BOT_CONFIG = json_loader(CONFIG_JSON_FILEPATH, "bot")
BOT_NAME_MEANING = try_get(BOT_CONFIG, "meaning")
BOT_INTRO = try_get(BOT_CONFIG, "intro")
BOT_JOB = try_get(BOT_CONFIG, "job")
BOT_CONTEXT = try_get(BOT_CONFIG, "context")
BOT_DIRECTIVES = try_get(BOT_CONFIG, "directives")
BOT_RESPONSES = try_get(BOT_CONFIG, "responses")
BOT_RESPONSES_FORBIDDEN = try_get(BOT_RESPONSES, "forbidden")
BOT_RESPONSES_FAIL = try_get(BOT_RESPONSES, "failed")
BOT_FAQS = try_get(BOT_CONFIG, "faqs")
BOT_USER_ID = try_get(BOT_CONFIG, "user_id")

BOT_NAME = try_get(BOT_CONFIG, "name")
BOT_TELEGRAM_HANDLE = try_get(BOT_CONFIG, "handle")
BOT_CHAT_HISTORY_FILEPATH = f"src/data/chat/content/{BOT_NAME}.jsonl"
BOT_CHAT_CONFIG_FILEPATH = f"src/data/chat/content/{BOT_NAME}.jsonl"
BOT_INTRO = f"Your name is {BOT_NAME}, which is short for {BOT_NAME_MEANING}, your telegram handle is {BOT_TELEGRAM_HANDLE}. You answer to Abbot. You are part of {ORG_NAME} - {ORG_DESCRIPTION} and you are an expert in all things {ORG_LOCATION}, {ORG_NAME}, Bitcoin and Lightning Network. {BOT_DIRECTIVES}."
BOT_SYSTEM = try_get(BOT_CONFIG, "system")
BOT_CORE_SYSTEM = f"{BOT_INTRO}. {BOT_SYSTEM}"

BOT_NAME = f"t{BOT_NAME}" if TEST_MODE or DEV_MODE else BOT_NAME
BOT_TELEGRAM_HANDLE = f"test_{BOT_TELEGRAM_HANDLE}" if TEST_MODE or DEV_MODE else BOT_TELEGRAM_HANDLE
BOT_TELEGRAM_TOKEN = TEST_BOT_TELEGRAM_HANDLE if TEST_MODE or DEV_MODE else BOT_TELEGRAM_TOKEN
