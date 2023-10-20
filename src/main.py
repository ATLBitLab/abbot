from sys import argv
from telegram.ext.filters import BaseFilter
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
)
from lib.logger import debug_logger
from lib.utils import try_get
from lib.abbot.config import AbbotConfig, AbbotEnv, setup_abbot_config
from lib.abbot.handlers import (
    leash,
    start,
    stop,
    rules,
    help,
    unleash,
    admin_nap,
    admin_kill,
    admin_plugin,
    admin_status,
    admin_unplug,
    handle_message,
)

if __name__ == "__main__":
    ARGS = argv[1:]
    DEV_MODE = "-d" in ARGS or "--dev" in ARGS

    abbot_env_config: dict = bot_env_config.get_bot_env()
    BOT_NAME: str = try_get(abbot_env_config, "BOT_NAME")
    BOT_TG_HANDLE: str = try_get(abbot_env_config, "BOT_TG_HANDLE")
    BOT_TG_TOKEN: str = try_get(abbot_env_config, "BOT_TG_TOKEN")

    debug_logger.log(f"Initializing {abbot_env_config} @{BOT_TG_HANDLE}")
    APPLICATION = ApplicationBuilder().token(BOT_TG_TOKEN).build()
    debug_logger.log(f"{BOT_NAME} @{BOT_TG_HANDLE} Initialized")

    _unplug_handler = CommandHandler("unplug", admin_unplug)
    _plugin_handler = CommandHandler("plugin", admin_plugin)
    _kill_handler = CommandHandler("kill", admin_kill)
    _nap_handler = CommandHandler("nap", admin_nap)
    _status_handler = CommandHandler("status", admin_status)
    APPLICATION.add_handler(_unplug_handler)
    APPLICATION.add_handler(_plugin_handler)
    APPLICATION.add_handler(_kill_handler)
    APPLICATION.add_handler(_nap_handler)
    APPLICATION.add_handler(_status_handler)

    help_handler = CommandHandler("help", help)
    rules_handler = CommandHandler("rules", rules)
    start_handler = CommandHandler("start", start)
    stop_handler = CommandHandler("stop", stop)
    unleash_handler = CommandHandler("unleash", unleash)
    leash_handler = CommandHandler("leash", leash)
    APPLICATION.add_handler(help_handler)
    APPLICATION.add_handler(rules_handler)
    APPLICATION.add_handler(start_handler)
    APPLICATION.add_handler(stop_handler)
    APPLICATION.add_handler(unleash_handler)
    APPLICATION.add_handler(leash_handler)

    message_handler = MessageHandler(BaseFilter(), handle_message)
    APPLICATION.add_handler(message_handler)

    debug_logger.log(f"{BOT_NAME} @{BOT_TG_HANDLE} Polling")
    APPLICATION.run_polling()
