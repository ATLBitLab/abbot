from lib.utils import try_get
from dotenv import dotenv_values, load_dotenv
from typing import LiteralString, Any

load_dotenv()
env: dict = dotenv_values()

BOT_NOSTR_SK: LiteralString = try_get(env, "BOT_NOSTR_SK")
BOT_NOSTR_PK: LiteralString = try_get(env, "BOT_NOSTR_PK")
BOT_NOSTR_NPUB: LiteralString = try_get(env, "BOT_NOSTR_NPUB")
OPENAI_API_KEY: LiteralString = try_get(env, "OPENAI_API_KEY")
LNBITS_BASE_URL: LiteralString = try_get(env, "LNBITS_BASE_URL")
PINECONE_API_KEY: LiteralString = try_get(env, "PINECONE_API_KEY")
PAYMENT_PROCESSOR_KIND: LiteralString = try_get(env, "PAYMENT_PROCESSOR_KIND")
PAYMENT_PROCESSOR_TOKEN: LiteralString = try_get(env, "PAYMENT_PROCESSOR_TOKEN")
BOT_TELEGRAM_TOKEN: LiteralString = try_get(env, "BOT_TELEGRAM_TOKEN")
TEST_BOT_TELEGRAM_HANDLE: LiteralString = try_get(env, "TEST_BOT_TELEGRAM_TOKEN")
DATABASE_KIND: LiteralString = try_get(env, "DATABASE_KIND")
DATABASE_NAME: LiteralString = try_get(env, "DATABASE_NAME")
DATABASE_USERNAME: LiteralString = try_get(env, "DATABASE_USERNAME")
DATABASE_PASSWORD: LiteralString = try_get(env, "DATABASE_PASSWORD")
DATABASE_HOST: LiteralString = try_get(env, "DATABASE_HOST")
DATABASE_CONNECTION_STRING: LiteralString = try_get(env, "DATABASE_CONNECTION_STRING")

assert BOT_NOSTR_SK, "BOT_NOSTR_SK required!"
assert BOT_NOSTR_PK, "BOT_NOSTR_PK required!"
assert BOT_TELEGRAM_TOKEN or TEST_BOT_TELEGRAM_HANDLE, "BOT_TELEGRAM_TOKEN or TEST_BOT_TELEGRAM_HANDLE required!"

assert OPENAI_API_KEY, "OPENAI_API_KEY required!"
assert PINECONE_API_KEY, "PINECONE_API_KEY required!"

assert PAYMENT_PROCESSOR_TOKEN, "PAYMENT_PROCESSOR_TOKEN required!"
assert LNBITS_BASE_URL, "LNBITS_BASE_URL required"

assert DATABASE_KIND, "DATABASE_KIND required!"
assert DATABASE_NAME, "DATABASE_NAME required!"
assert DATABASE_USERNAME, "DATABASE_USERNAME required!"
assert DATABASE_PASSWORD, "DATABASE_PASSWORD required!"
assert DATABASE_HOST, "DATABASE_HOST required!"
