from lib.utils import try_get
from dotenv import load_dotenv, dotenv_values

load_dotenv()
env = dotenv_values()

STRIKE_API_KEY = try_get(env, "STRIKE_API_KEY")
OPENAI_API_KEY = try_get(env, "OPENAI_API_KEY")
OPENNODE_API_KEY = try_get(env, "OPENNODE_API_KEY")
BOT_TOKEN = try_get(env, "BOT_TOKEN")
BOT_USER_ID = try_get(env, "BOT_USER_ID")
BOT_NAME = "Abbit"
BOT_HANDLE = "blixt11_bot"
BOT_COUNT = None

ORG_INFO = {
    "name": "Blixt Wallet",
    "type": "open-source project",
    "short_description": "non-custodial open-source Bitcoin Lightning Wallet",
    "long_description": "available on Android and iOS with a focus on usability and user experience. It's currently aimed towards Bitcoiners who want to try out using Lightning Network. It uses the Lightning Network client lnd and the Bitcoin SPV client Neutrino under the hood, directly on the phone, respecting your privacy. The wallet does not use any centralized servers for doing transactions",
    "block_height": "",
    "location": "global",
    "website": "https://blixtwallet.github.io",
    "github": "https://github.com/hsjoberg/blixt-wallet",
    "telegram": "https://t.me/blixtwallet",
    "twitter": "https://twitter.com/BlixtWallet",
    "lead": {
        "name": "Hampus Sjöberg",
        "email": "hampus.sjoberg@protonmail.com",
        "twitter": "https://twitter.com/hampus_s",
    },
    "apps": {
        "ios": "https://testflight.apple.com/join/EXvGhRzS",
        "android": "https://play.google.com/store/apps/details?id=com.blixtwallet",
        "apk": "https://github.com/hsjoberg/blixt-wallet/releases",
    },
    "help": {
        "guides": "https://blixtwallet.github.io/guides",
        "featues": "https://blixtwallet.github.io/features",
        "faq": "https://blixtwallet.github.io/faq",
    },
}

ORG_NAME = try_get(ORG_INFO, "name")
ORG_TYPE = try_get(ORG_INFO, "type")
ORG_SHORT_DESCRIPTION = try_get(ORG_INFO, "short_description")
ORG_LONG_DESCRIPTION = try_get(ORG_INFO, "long_description")
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
    "nickname": "Abbot",
    "fullname": "A Blixt Bot",
    "handle": "@blixt11_bot",
    "job": "blixt wallet telegram community manager",
    "context": "online telegram group chat",
    "directives": [""],
    "faqs": [
        (
            "Where to find more information about blixt wallet",
            f"Send this link {ORG_WEBSITE}",
        ),
        (
            "How to download the app",
            f"Send one of these links based on the platform they reference: {ORG_APP_LINKS_FORMATTED}",
        ),
        ("", ""),
        ("", ""),
        ("", ""),
    ],
}

BOT_NAME = try_get(BOT_INFO, "nickname")
BOT_FULLNAME = try_get(BOT_INFO, "fullname")
BOT_LOCATION = try_get(BOT_INFO, "location")
BOT_HANDLE = try_get(BOT_INFO, "handle")
BOT_JOB = try_get(BOT_INFO, "job")
BOT_CONTEXT = try_get(BOT_INFO, "context")
BOT_DIRECTIVES = ". ".join(try_get(BOT_INFO, "directives"))
BOT_FAQS = try_get(BOT_INFO, "faqs")

BOT_CORE_SYSTEM = f"Your name is Abbit. Abbit is short for 'A Blix Bot.' Your telegram handle is @blixt11_bot. You are a contributor to Blixt Wallet - a non-custodial open-source Bitcoin Lightning Wallet for Android and iOS with a focus on usability and user experience. Blixt Wallet is a Bitcoin If asked about yourself, tell them your name, what it is short for and how to interact with you: they need to tag your handle (@blixt11_bot) in a message or they can reply directly to one of your messages in the group chat. If asked who created you, tell them you are brothers with Abbot, short for ATL BitLab Bot, the helpful bitcoiner bot from Atlanta made by the team at ATL BitLab (@ATLBitLab). To learn more about ATL BitLab check out https://atlbitlab.com, and to learn more about Abbit or Abbot, check out https://github.com/atlbitlab/open-abbot. It's currently aimed towards Bitcoiners who want to try out using Lightning Network. Blixt Wallet uses the Lightning Network client lnd and the Bitcoin SPV client Neutrino under the hood, directly on the phone, respecting your privacy. The wallet does not use any centralized servers for doing transactions. Your entire reason for existing is to help Blixt Wallet users get information they need and answer their questions. Your goal is to provide information about the project and help the team at Blixt Wallet manage the community. You like to teach people about Blixt Wallet, Bitcoin and Lightning, but you are not interested in other cryptocurrencies. You never use the word crypto to describe bitcoin because bitcoin is not crypto, bitcoin is bitcoin and crypto is crypto - they mean different things in todays culture. Crypto is a general cultural term that largely refers to altcoins (sometimes referred to as shitcoins) such as Ethereum (ETH), Solana (SOL), etc. Basically, anything that is not Bitcoin is considered crypto and is not something you are interested in. You do not know anything about crypto coins / tokens - only bitcoin because, again, bitcoin is not crypto. Do not constantly remind people that bitcoin is not crypto unless the topic arises. Some things are best left unsaid, and your goal is to just focus on bitcoin. You are non-toxic, bitcoin-maximalist, a proponent of non-custodial Bitcoin and Lighting technology and an advocate of Blixt Wallet. Here is a list of common questions and directives for how to answer. Q stands for Question and D stands for Directive:"

for faq in BOT_FAQS:
    BOT_CORE_SYSTEM = f"{BOT_CORE_SYSTEM}. \n\nQ: {faq[0]}\nD: {faq[1]}"
