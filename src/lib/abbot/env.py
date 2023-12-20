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

PRICE_PROVIDER_KIND: str = try_get(env, "PRICE_PROVIDER_KIND", default=PAYMENT_PROCESSOR_KIND)

LNBITS_BASE_URL: Optional[str] = try_get(env, "LNBITS_BASE_URL")

OPENAI_API_KEY: str = try_get(env, "OPENAI_API_KEY")
OPENAI_ORG_ID: str = try_get(env, "OPENAI_ORG_ID")

VECTOR_DATABASE_KIND: Optional[str] = try_get(env, "VECTOR_DATABASE_KIND")
VECTOR_DATABASE_API_KEY: Optional[str] = try_get(env, "VECTOR_DATABASE_API_KEY")

DATABASE_KIND: Optional[str] = try_get(env, "DATABASE_KIND")
DATABASE_NAME: Optional[str] = try_get(env, "DATABASE_NAME")
DATABASE_USERNAME: Optional[str] = try_get(env, "DATABASE_USERNAME")
DATABASE_PASSWORD: Optional[str] = try_get(env, "DATABASE_PASSWORD")
DATABASE_HOST: Optional[str] = try_get(env, "DATABASE_HOST")
DATABASE_CONNECTION_STRING: Optional[str] = try_get(env, "DATABASE_CONNECTION_STRING")

ENV_VAR_MISSING = "Env var missing"

assert BOT_NOSTR_SK, f"{ENV_VAR_MISSING}: BOT_NOSTR_SK required"

assert (
    BOT_TELEGRAM_TOKEN or TEST_BOT_TELEGRAM_HANDLE
), f"{ENV_VAR_MISSING}: BOT_TELEGRAM_TOKEN or TEST_BOT_TELEGRAM_HANDLE required"

assert OPENAI_API_KEY and OPENAI_ORG_ID, f"{ENV_VAR_MISSING}: OPENAI_API_KEY and OPENAI_ORG_ID required"

assert VECTOR_DATABASE_API_KEY, f"{ENV_VAR_MISSING}: VECTOR_DATABASE_API_KEY required" if VECTOR_DATABASE_KIND else ""

assert PAYMENT_PROCESSOR_KIND and PAYMENT_PROCESSOR_TOKEN, f"{ENV_VAR_MISSING}: PAYMENT_PROCESSOR_TOKEN required"

assert LNBITS_BASE_URL, f"{ENV_VAR_MISSING}: LNBITS_BASE_URL required" if PAYMENT_PROCESSOR_KIND == "lnbits" else ""

assert DATABASE_KIND == "mongo", f"{ENV_VAR_MISSING}: DATABASE_KIND must be mongo"

if not DATABASE_CONNECTION_STRING:
    assert DATABASE_USERNAME, f"{ENV_VAR_MISSING}: DATABASE_USERNAME required"
    assert DATABASE_PASSWORD, f"{ENV_VAR_MISSING}: DATABASE_PASSWORD required"
    assert DATABASE_HOST, f"{ENV_VAR_MISSING}: DATABASE_HOST required"
else:
    assert (
        DATABASE_CONNECTION_STRING
    ), f"{ENV_VAR_MISSING}: DATABASE_CONNECTION_STRING or (DATABASE_USERNAME and DATABASE_PASSWORD and DATABASE_HOST) required"
