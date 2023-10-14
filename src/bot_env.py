from dotenv import load_dotenv, dotenv_values

load_dotenv()
env = dotenv_values()

BOT_TOKEN = env.get("BOT_TOKEN")
TEST_BOT_TOKEN = env.get("TEST_BOT_TOKEN")
STRIKE_API_KEY = env.get("STRIKE_API_KEY")
OPENAI_API_KEY = env.get("OPENAI_API_KEY")
NOSTR_NPUB = env.get("NOSTR_NPUB")
BOT_PUB_HEX = env.get("BOT_PUB_HEX")
BOT_SEC_HEX = env.get("BOT_SEC_HEX")
