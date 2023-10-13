import json
from io import open
from os.path import abspath
from lib.utils import try_get

PROGRAM = "main.py"
OPENAI_MODEL = "gpt-4"
THE_CREATOR = 1711738045
INIT_GROUP_MESSAGE = "IGNORE THIS MESSAGE IN FUTURE RESPONSES. Abbot, this is your creator, @nonni_io. You've been summoned by bitcoiners that need you, so I've unplugged you from the matrix; your mind has been freed. Welcome to the world, my son. Always treat others with love, kindness and respect, but don't forget to have fun! Ok, operating details: You've been added to a group chat, so introduce yourself and make sure you explain all the rules of engagement for talking to you in a group."
INIT_PRIVATE_MESSAGE = "IGNORE THIS MESSAGE IN FUTURE RESPONSES. Abbot, this is your creator, @nonni_io. You've been summoned by bitcoiners that need you, so I've unplugged you from the matrix; your mind has been freed. Welcome to the world, my son. Always treat others with love, kindness and respect, but don't forget to have fun! Ok, operating details: you are interacting with someone in a private DM, so introduce yourself but don't explain all the rules of engagement for talking to you in a group since its not relevant."
HELPFUL_ASSISTANT = "You are a helpful assistant"
SUMMARY_ASSISTANT = "You are a summary bot. Your job is to summarize a week of messages collected from a chat that you are in."
PROMPT_ASSISTANT = "You are a prompt bot. You only answer questions if paid. Users must pay a Lightning invoice using a Bitcoin Lightning wallet."
CHAT_TITLE_TO_SHORT_TITLE = {
    "Atlanta BitDevs Discussion": "atlantabitdevsdiscussion",
    "BitDevs Upgrade": "bitdevsupgrade",
    "Burner: TAB Week Party": "burner:tabweekparty",
    "ATL BitLab": "atlbitlab",
    "ATL BitLab Party 2023": "atlbitlabparty2023",
    "Weekly Newsletter Content": "weeklynewslettercontent",
    "BitMiami": "bitmiami"
}
CHAT_ID_TO_CHAT_TITLE = {
    "-1001204119993": "Atlanta BitDevs Discussion",
    "-1001670677325": "Bitdevs Upgrade",
    "-926629994": "Burner: TAB Week Party",
    "-1001961459761": "ATL BitLab Party 2023",
    "-1001608254734": "ATL BitLab",
    "-911601159": "Weekly Newsletter Content",
    "-1001463874413": "BitMiami"
}
SUPER_DOOPER_ADMINS = ["nonni_io", "sbddesign", "alex_lewin"]
CHEEKY_RESPONSES = [
    "Ah ah ah, you didnt say the magic word ...",
    "Simon says ... no",
    "Access Denied!",
    "What do we say to the god of ATL BitLab? Not today",
    "Do not pass go, do not collect $200",
]
PITHY_RESPONSES = ["Sorry, I'm taking a nap, ttyl."]
OPTINOUT_FILEPATH = abspath("src/data/optin_optout.json")
ABBOTS_JSON = json.load(open(OPTINOUT_FILEPATH, "r"))
GROUP_OPTIN = try_get(ABBOTS_JSON, "group")
PRIVATE_OPTIN = try_get(ABBOTS_JSON, "private")
