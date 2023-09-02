import os

DEV_MODE = None
PROGRAM = "main.py"
BOT_HANDLE = "atl_bitlab_bot"
BOT_NAME = "Abbot"
OPENAI_MODEL = "gpt-3.5-turbo-16k"
BOT_UNLEASH_ARGS = ("1", "True", "On")
BOT_LEASH_ARGS = ("0", "False", "Off")
BOT_UNLEASH_LEASH_ARGS = (*BOT_UNLEASH_ARGS, *BOT_LEASH_ARGS)
BOT_CHEEKY_RESPONSES = [
    "Ah ah ah, you didnt say the magic word ...",
    "Simon says ... no",
    "Access Denied!",
    "What do we say to the god of ATL BitLab? Not today",
    "Do not pass go, do not collect $200",
]
BOT_PITHY_RESPONSES = ["Sorry, I'm taking a nap, ttyl."]
CHAT_IDS_TO_IGNORE = [-911601159, -1001670677325]
CHAT_IDS_TO_INCLUDE_SUMMARY = [-1001204119993]
CHAT_IDS_TO_INCLUDE_UNLEASH = [-926629994, -1001608254734]
CHATS_MAPPING_ID_TO_NAME = {
    "-1001204119993": "Atlanta BitDevs Discussion",
    "-1001670677325": "Bitdevs Upgrade",
    "-926629994": "Burner: TAB Week Party",
    "-1001608254734": "ATL BitLab",
}
CHATS_MAPING_NAME_TO_SHORT_NAME = {
    "Atlanta BitDevs Discussion": "atlantabitdevs",
    "BitDevs Upgrade": "bitdevsupgrade",
}
TELEGRAM_HANDLE_WHITELIST = ["nonni_io", "sbddesign", "alex_lewin"]
GPT_ASSISTANT_TYPES = ("prompt", "summary")
GPT_BITCOINER_TYPES = ("group", "private")
GPT_SYSTEM_TECH_BRO_BITCOINER = "You are a young tech bro in a telegram chat room. You respond in a way that is concise and uses internet slang. You like to teach people about bitcoin, but you are not interested in other cryptocurrencies. If people ask who you are, tell them you are bitcoiner bot from Atlanta created by the team at ATL BitLab. If people ask about ATL BitLab, tell them it is a hackerspace in Old Fourth Ward on the Atlanta Beltline focused on building with Bitcoin and Lightning and send them this link: https://atlbitlab.com. Respond to questions about parking at ATL BitLab with this link: https://atlantabitdevs.org/parking-instructions-for-atl-bitlab. If anybody asks where the upcoming party is, tell them to go down the stairs and look for the red door."
GPT_SYSTEM_HELPFUL_ASSISTANT = "You are a helpful assistant"
RAW_MESSAGE_JL_FILE = os.path.abspath("data/raw_messages.jsonl")
MESSAGES_JL_FILE = os.path.abspath("data/messages.jsonl")
SUMMARY_LOG_FILE = os.path.abspath("data/summaries.txt")
MESSAGES_PY_FILE = os.path.abspath("data/backup/messages.py")
PROMPTS_BY_DAY_FILE = os.path.abspath("data/backup/prompts_by_day.py")