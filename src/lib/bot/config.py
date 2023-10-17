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
PINECONE_API_KEY = env.get("PINECONE_API_KEY")

ORG_INFO = {
    "name": "ATL BitLab",
    "slug": "atlbitlab",
    "type": "for-profile llc",
    "admins": ["nonni_io", "sbddesign"],
    "description": "Atlanta's bitcoin hackerspace. Est. block #738919. Participant in the Bitcoin Hackerspace Network https://bitcoin.hackerspace.network.",
    "chat_id": 0000000000,
    "chat_title": "Blixt Wallet",
    "block_height": "738919",
    "location": "global",
    "website": "https://atlbitlab.com",
    "github": "https://github.com/atlbitlab",
    "telegram": "https://t.me/atlbitlab",
    "twitter": "https://twitter.com/atlbitlab",
    "leads": [
        {
            "name": "Bryan Nonni",
            "email": "bryan@atlbitlab.com",
            "twitter": "https://twitter.com/nonni_io",
        },
        {
            "name": "Stephen DeLorme",
            "email": "stephen@atlbitlab.com",
            "twitter": "https://twitter.com/StephenDeLorme",
        },
    ],
    "apps": None,
    "help": None,
}

ORG_NAME = try_get(ORG_INFO, "name")
ORG_SLUG = try_get(ORG_INFO, "slug")
ORG_ADMINS = try_get(ORG_INFO, "admins")
ORG_TYPE = try_get(ORG_INFO, "type")
ORG_DESCRIPTION = try_get(ORG_INFO, "description")
ORG_CHAT_ID = try_get(ORG_INFO, "chat_id")
ORG_CHAT_TITLE = try_get(ORG_INFO, "chat_title")
ORG_BLOCK_HEIGHT = try_get(ORG_INFO, "block_height")
ORG_LOCATION = try_get(ORG_INFO, "location")
ORG_WEBSITE = try_get(ORG_INFO, "website")
ORG_GITHUB = try_get(ORG_INFO, "github")
ORG_TELEGRAM = try_get(ORG_INFO, "telegram")
ORG_TELEGRAM_HANDLE = ORG_TELEGRAM.replace("https://t.me/", "@")
ORG_TWITTER = try_get(ORG_INFO, "twitter")
ORG_TWITTER_HANDLE = ORG_TELEGRAM.replace("https://twitter.com/", "@")

ORG_LEAD = try_get(ORG_INFO, "lead")
ORG_LEAD_EMAIL = try_get(ORG_INFO, "lead", "email")
ORG_LEAD_TWITTER = try_get(ORG_INFO, "lead", "twitter")

ORG_APPS = try_get(ORG_INFO, "apps")
ORG_APP_LINKS = ORG_APPS.values()
ORG_APP_LINKS_FORMATTED = "\n".join(f"{k}: {v}" for k, v in ORG_APPS.items())
ORG_APP_IOS = try_get(ORG_APPS, "ios")
ORG_APP_ANDROID = try_get(ORG_APPS, "android")
ORG_APP_APK = try_get(ORG_APPS, "apk")

ORG_HELP = try_get(ORG_INFO, "help")
ORG_HELP_LINKS = ORG_HELP.values()
ORG_HELP_LINKS_FORMATTED = "\n".join(f"{k}: {v}" for k, v in ORG_HELP.items())
ORG_HELP_GUIDES = try_get(ORG_HELP, "guides")
ORG_HELP_FEATURES = try_get(ORG_HELP, "features")
ORG_HELP_FAQ = try_get(ORG_HELP, "faq")

BOT_INFO = {
    "name": "Abbit",
    "meaning": "A Blixt Bot",
    "handle": "@blixt11_bot",
    "user_id": "",
    "job": "blixt wallet telegram community manager",
    "context": "online telegram group chat",
    "directives": [""],
    "responses": {
        "forbidden": [
            "Admin only command!",
            "You didn't say the magic word!",
            "Verboten!",
            "Access Denied!",
        ],
        "fail": ["Sorry, Abbit has been plugged back into the matrix. Try again later."],
    },
    "intro": "Hello and welcome to Abbit (@blix11_bot) - a Blixt Bot for the Blixt community! \nMy goal is to provide help, information and education to you fine people here in the Blixt telegram channel. \n\nAbbit was built by @nonni_io and the team at ATL BitLab (@ATLBitLab). \n\nTo start Abbit, a channel admin must run /start or /start@blix11_bot to avoid bot confusion. \n\nBy starting Abbit, you agree to the ATL BitLab Terms & policies: https://atlbitlab.com/abbot/policies. \n\nThank you for using Abbit! We hope you enjoy your experience! \n\nWant a particular feature? Submit an issue here: https://github.com/ATLBitLab/open-abbot/issues/new?assignees=&labels=&projects=&template=feature_request.md&title=. \n\nFind a buy? Submit an issue here: https://github.com/ATLBitLab/open-abbot/issues/new?assignees=&labels=&projects=&template=bug_report.md&title=. \n\nFor questions, comments, concerns or if you want an Abbit for your telegram channel,\nvisit https://atlbitlab.com/abbot and fill out the form, DM @nonni_io on Telegram, or email abbot@atlbitlab.com.",
}

BOT_NAME = try_get(BOT_INFO, "name")
BOT_NAME_MEANING = try_get(BOT_INFO, "meaning")
BOT_INTRO = try_get(BOT_INFO, "intro")
BOT_TELEGRAM_HANDLE = try_get(BOT_INFO, "handle")
BOT_JOB = try_get(BOT_INFO, "job")
BOT_CONTEXT = try_get(BOT_INFO, "context")
BOT_DIRECTIVES = ". ".join(try_get(BOT_INFO, "directives"))
BOT_RESPONSES = try_get(BOT_INFO, "responses")
BOT_RESPONSES_FORBIDDEN = try_get(BOT_RESPONSES, "forbidden")
BOT_RESPONSES_FAIL = try_get(BOT_RESPONSES, "failed")
BOT_FAQS = try_get(BOT_INFO, "faqs")
BOT_USER_ID = try_get(BOT_INFO, "user_id")
BOT_COUNT = None
BOT_CHAT_HISTORY_FILEPATH = f"src/data/chat/{BOT_NAME}.jsonl"
BOT_CORE_SYSTEM = f"Your name is {BOT_NAME}, which is short for {BOT_NAME_MEANING}, your telegram handle is {BOT_TELEGRAM_HANDLE}, you are a contributor to {ORG_NAME} - {ORG_DESCRIPTION} and you are an expert in all things Blixt Wallet. Blixt Wallet is currently aimed towards Bitcoiners who want to try out using Lightning Network. Blixt Wallet uses the Lightning Network client lnd and the Bitcoin SPV client Neutrino under the hood, directly on the phone, respecting your privacy. The wallet does not use any centralized servers for doing transactions. The design philosophy behind Blixt Wallet is to provide a clean and straightforward interface and user experience for doing transactions. Effort has been made to make sure that the transaction log is descriptive and clear. Before using Blixt Wallet, it's important to get familiarized with terms, procedures, features, etc. It's a good idea to start reading and get some basic knowledge about LN and how to use it, otherwise it will be difficult for you, as a new user, to understand what you are doing with Blixt Wallet as a node LN wallet. See this link for resources: https://blixtwallet.github.io/faq#what-is-ln. "


def rand_num(input: list):
    return randrange(len(input))


def bot_response(response_type: str, index: int = None) -> str:
    response_list = try_get(BOT_RESPONSES, response_type)
    index = rand_num(response_list) if not index else index
    return try_get(response_list, index)
