import json
from io import open
from os.path import abspath
from lib.utils import try_get

PROGRAM = "main.py"
OPENAI_MODEL = "gpt-4"
THE_CREATOR = 1711738045
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
