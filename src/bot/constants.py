import io
from os.path import abspath

I = 0
OPENAI_MODEL = "gpt-4"
THE_CREATOR = 1711738045
OPT_INOUT_FILEPATH = abspath("src/data/terms/optin_optout.json")
OPT_INOUT_FILE = io.open(OPT_INOUT_FILEPATH, "r+")
HELP_MENU = """""Welcome to Abbot!
Available Commands
1. /start
    Description: Start Abbot in your channel. Channel admin only.
2. /stop
    Description: Stop Abbot in your channel. Channel admin only.
3. /help
    Description: Show help menu"""
