from random import randrange
from lib.utils import try_get
from dotenv import load_dotenv, dotenv_values

load_dotenv()
env = dotenv_values()

STRIKE_API_KEY = try_get(env, "STRIKE_API_KEY")
OPENAI_API_KEY = try_get(env, "OPENAI_API_KEY")
OPENNODE_API_KEY = try_get(env, "OPENNODE_API_KEY")
BOT_TOKEN = try_get(env, "BOT_TOKEN")
TEST_BOT_TOKEN = try_get(env, "TEST_BOT_TOKEN")

ORG_INFO = {
    "name": "ATL BitLab",
    "slug": "atlbitlab",
    "type": "",
    "admins": [""],
    "description": "",
    "chat_id": 0000000000,
    "chat_title": "ATL BitLab",
    "block_height": "",
    "location": "ATL",
    "website": "https://atlbitlab.com",
    "github": "https://github.com/atlbitlab",
    "telegram": {"link": "https://t.me/atlbitlab", "handle": "@atlbitlab"},
    "twitter": {"link": "https://twitter.com/atlbitlab", "handle": "@atlbitlab"},
    "meetup": "https://meetup.com/atlbitlab",
    "lead": {
        "name": "Bryan Nonni",
        "email": "bryan@atlbitlab.com",
        "twitter": "https://twitter.com/nonni_io",
    },
}

ORG_NAME = try_get(ORG_INFO, "name")
ORG_SLUG = try_get(ORG_INFO, "slug")
ORG_ADMINS = try_get(ORG_INFO, "admins")
ORG_CHAT_HISTORY_FILEPATH = f"src/data/chat/{ORG_SLUG}.jsonl"
ORG_TYPE = try_get(ORG_INFO, "type")
ORG_DESCRIPTION = try_get(ORG_INFO, "description")
ORG_CHAT_ID = try_get(ORG_INFO, "chat_id")
ORG_CHAT_TITLE = try_get(ORG_INFO, "chat_title")
ORG_BLOCK_HEIGHT = try_get(ORG_INFO, "block_height")
ORG_LOCATION = try_get(ORG_INFO, "location")
ORG_WEBSITE = try_get(ORG_INFO, "website")
ORG_GITHUB = try_get(ORG_INFO, "github")

ORG_TELEGRAM = try_get(ORG_INFO, "telegram")
ORG_TELEGRAM_LINK = try_get(ORG_TELEGRAM, "link")
ORG_TELEGRAM_HANDLE = try_get(ORG_TELEGRAM, "handle")

ORG_TWITTER = try_get(ORG_INFO, "twitter")
ORG_TWITTER_LINK = try_get(ORG_TWITTER, "link")
ORG_TWITTER_HANDLE = try_get(ORG_TWITTER, "handle")

ORG_LEAD = try_get(ORG_INFO, "lead")
ORG_LEAD_EMAIL = try_get(ORG_INFO, "lead", "email")
ORG_LEAD_TWITTER = try_get(ORG_INFO, "lead", "twitter")

BOT_INFO = {
    "name": "Abbot",
    "meaning": "ATL BitLab Bot",
    "handle": "@atl_bitlab_bot",
    "user_id": "",
    "job": "",
    "context": "online telegram group chat",
    "cadence": True,
    "modulo": 5,
    "directives": [""],
    "responses": {
        "forbidden": [
            "Admin only command!",
            "You didn't say the magic word!",
            "Verboten!",
            "Access Denied!",
        ],
        "fail": [
            "Sorry, Abbot has been plugged back into the matrix. Try again later."
        ],
    },
    "intro": "Hello and welcome to Abbot (@atl_bitlab_bot). By starting Abbot, you agree to the ATL BitLab Terms & policies: https://atlbitlab.com/abbot/policies. \n\nThank you for using Abbot! We hope you enjoy your experience! \n\nWant a particular feature? Submit an issue here: https://github.com/ATLBitLab/open-abbot/issues/new?assignees=&labels=&projects=&template=feature_request.md&title=. \n\nFind a buy? Submit an issue here: https://github.com/ATLBitLab/open-abbot/issues/new?assignees=&labels=&projects=&template=bug_report.md&title=. \n\nFor questions, comments, concerns or if you want an Abbot for your telegram channel,\nvisit https://atlbitlab.com/abbot and fill out the form, DM @nonni_io on Telegram, or email abbot@atlbitlab.com.",
}

BOT_NAME = try_get(BOT_INFO, "name")
BOT_NAME_MEANING = try_get(BOT_INFO, "meaning")
BOT_INTRO = try_get(BOT_INFO, "intro")
BOT_TELEGRAM_HANDLE = try_get(BOT_INFO, "handle")
BOT_JOB = try_get(BOT_INFO, "job")
BOT_CONTEXT = try_get(BOT_INFO, "context")
BOT_CADENCE = try_get(BOT_INFO, "cadence")
BOT_MODULO = try_get(BOT_INFO, "modulo")
BOT_DIRECTIVES = ". ".join(try_get(BOT_INFO, "directives"))
BOT_RESPONSES = try_get(BOT_INFO, "responses")
BOT_RESPONSES_FORBIDDEN = try_get(BOT_RESPONSES, "forbidden")
BOT_RESPONSES_FAIL = try_get(BOT_RESPONSES, "failed")
BOT_FAQS = try_get(BOT_INFO, "faqs")
BOT_USER_ID = try_get(BOT_INFO, "user_id")
BOT_COUNT = None
BOT_CHAT_HISTORY_FILEPATH = f"src/data/chat/{BOT_NAME}.jsonl"
BOT_CORE_SYSTEM = f"Your name is {BOT_NAME}, which is short for {BOT_NAME_MEANING}, your telegram handle is {BOT_TELEGRAM_HANDLE}."


def rand_num(input: list):
    return randrange(len(input))


def bot_response(response_type: str, index: int = None) -> str:
    response_list = try_get(BOT_RESPONSES, response_type)
    index = rand_num(response_list) if not index else index
    return try_get(response_list, index)
