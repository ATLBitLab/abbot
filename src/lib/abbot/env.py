from lib.utils import try_get
from dotenv import dotenv_values, load_dotenv

load_dotenv()
env: dict = dotenv_values()

BOT_NOSTR_SK = try_get(env, "BOT_NOSTR_SK")
OPENAI_API_KEY = try_get(env, "OPENAI_API_KEY")
LNBITS_BASE_URL = try_get(env, "LNBITS_BASE_URL")
PINECONE_API_KEY = try_get(env, "PINECONE_API_KEY")
PAYMENT_PROCESSOR_KIND = try_get(env, "PAYMENT_PROCESSOR_KIND")
PAYMENT_PROCESSOR_TOKEN = try_get(env, "PAYMENT_PROCESSOR_TOKEN")
BOT_TELEGRAM_TOKEN = try_get(env, "BOT_TELEGRAM_TOKEN")
TEST_BOT_TELEGRAM_HANDLE = try_get(env, "TEST_BOT_TELEGRAM_TOKEN")

assert BOT_NOSTR_SK, "BOT_NOSTR_SK required!"
assert OPENAI_API_KEY, "OPENAI_API_KEY required!"
assert LNBITS_BASE_URL, "LNBITS_BASE_URL required"
assert PINECONE_API_KEY, "PINECONE_API_KEY required!"
assert BOT_TELEGRAM_TOKEN, "BOT_TELEGRAM_TOKEN required!"
assert PAYMENT_PROCESSOR_TOKEN, "PAYMENT_PROCESSOR_TOKEN required!"
