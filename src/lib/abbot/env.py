from lib.utils import try_get
from dotenv import dotenv_values, load_dotenv
from typing import Optional

load_dotenv()
env: dict = dotenv_values()

BOT_TELEGRAM_TOKEN: str = try_get(env, "BOT_TELEGRAM_TOKEN")
TEST_BOT_TELEGRAM_HANDLE: Optional[str] = try_get(env, "TEST_BOT_TELEGRAM_TOKEN")

BOT_NOSTR_SK: str = try_get(env, "BOT_NOSTR_SK")

PAYMENT_PROCESSOR_KIND: str = try_get(env, "PAYMENT_PROCESSOR_KIND")
PAYMENT_PROCESSOR_TOKEN: str = try_get(env, "PAYMENT_PROCESSOR_TOKEN")

LNBITS_BASE_URL: Optional[str] = try_get(env, "LNBITS_BASE_URL")

OPENAI_API_KEY: Optional[str] = try_get(env, "OPENAI_API_KEY")
VECTOR_DATABASE_KIND: Optional[str] = try_get(env, "VECTOR_DATABASE_KIND")
VECTOR_DATABASE_API_KEY: Optional[str] = try_get(env, "VECTOR_DATABASE_API_KEY")

DATABASE_KIND: Optional[str] = try_get(env, "DATABASE_KIND")
DATABASE_NAME: Optional[str] = try_get(env, "DATABASE_NAME")
DATABASE_USERNAME: Optional[str] = try_get(env, "DATABASE_USERNAME")
DATABASE_PASSWORD: Optional[str] = try_get(env, "DATABASE_PASSWORD")
DATABASE_HOST: Optional[str] = try_get(env, "DATABASE_HOST")
DATABASE_CONNECTION_STRING: Optional[str] = try_get(env, "DATABASE_CONNECTION_STRING")

assert BOT_NOSTR_SK, "BOT_NOSTR_SK required"
assert BOT_TELEGRAM_TOKEN or TEST_BOT_TELEGRAM_HANDLE, "BOT_TELEGRAM_TOKEN or TEST_BOT_TELEGRAM_HANDLE required"

assert OPENAI_API_KEY, "OPENAI_API_KEY required"
if VECTOR_DATABASE_KIND:
    assert VECTOR_DATABASE_API_KEY, "VECTOR_DATABASE_API_KEY required"

assert PAYMENT_PROCESSOR_KIND and PAYMENT_PROCESSOR_TOKEN, "PAYMENT_PROCESSOR_TOKEN required"
if PAYMENT_PROCESSOR_KIND == "lnbits":
    assert LNBITS_BASE_URL, "LNBITS_BASE_URL required"

if not DATABASE_CONNECTION_STRING:
    assert DATABASE_USERNAME, "DATABASE_USERNAME required"
    assert DATABASE_PASSWORD, "DATABASE_PASSWORD required"
    assert DATABASE_HOST, "DATABASE_HOST required"

if DATABASE_KIND:
    assert DATABASE_KIND == "mongo", "DATABASE_KIND must be mongo"
