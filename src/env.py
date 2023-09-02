from dotenv import load_dotenv, dotenv_values
load_dotenv()
env = dotenv_values()

_BOT_TOKEN = env.get("BOT_TOKEN")
_TEST_BOT_TOKEN = env.get("TEST_BOT_TOKEN")
_STRIKE_API_KEY = env.get("STRIKE_API_KEY")
_OPENAI_API_KEY = env.get("OPENAI_API_KEY")