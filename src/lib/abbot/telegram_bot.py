# core
import json
import time
import uuid
import tiktoken
import traceback

from datetime import datetime
from typing import Any, Dict, List, Optional


# packages
from telegram.constants import MessageEntityType, ParseMode
from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update, Message, Chat, User
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.ext.filters import (
    ChatType,
    StatusUpdate,
    Regex,
    Entity,
    Mention,
    UpdateFilter,
    UpdateType,
    Document,
    REPLY,
    VIDEO,
    PHOTO,
)

"""
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

ChatType = filters.ChatType
StatusUpdate = filters.StatusUpdate
Regex = filters.Regex
Entity = filters.Entity
Mention = filters.Mention
UpdateFilter = filters.UpdateFilter
UpdateType = filters.UpdateType
Reply = filters.REPLY
"""

from constants import (
    HELP_MENU,
    INTRODUCTION,
    MATRIX_IMG_FILEPATH,
    OPENAI_MODEL,
    RULES,
    SATOSHIS_PER_BTC,
    THE_ARCHITECT_HANDLE,
)
from ..abbot.config import (
    BOT_GROUP_CONFIG_DEFAULT,
    BOT_GROUP_CONFIG_STARTED,
    BOT_LIGHTNING_ADDRESS,
    BOT_SYSTEM_OBJECT_GROUPS,
    BOT_NAME,
    BOT_TELEGRAM_HANDLE,
    BOT_TELEGRAM_SUPPORT_CONTACT,
    BOT_TELEGRAM_USERNAME,
    BOT_SYSTEM_OBJECT_DMS,
    ORG_INPUT_TOKEN_COST,
    ORG_OUTPUT_TOKEN_COST,
    ORG_PER_TOKEN_COST_DIV,
    ORG_TOKEN_COST_MULT,
)

MARKDOWN_V2 = ParseMode.MARKDOWN_V2
MENTION = MessageEntityType.MENTION

CHAT_TYPE_GROUPS = ChatType.GROUPS
CHAT_TYPE_GROUP = ChatType.GROUP
CHAT_TYPE_PRIVATE = ChatType.PRIVATE
CHAT_CREATED = StatusUpdate.CHAT_CREATED
NEW_CHAT_MEMBERS = StatusUpdate.NEW_CHAT_MEMBERS
LEFT_CHAT_MEMEBERS = StatusUpdate.LEFT_CHAT_MEMBER
REGEX_BOT_TELEGRAM_HANDLE = Regex(BOT_TELEGRAM_HANDLE)
FILTER_MENTION_ABBOT = Mention(BOT_TELEGRAM_HANDLE)
ENTITY_MENTION = Entity(MENTION)
ENTITY_REPLY = Entity(REPLY)
REGEX_MARKDOWN_REPLY = Regex("markdown") & REPLY
MESSAGE_EDITED = UpdateType.EDITED_MESSAGE
MEDIA = VIDEO | PHOTO | Document.ALL

# local
from ..logger import debug_bot, error_bot
from ..utils import error, qr_code, try_get, successful
from ..db.mongo import TelegramDM, TelegramGroup, mongo_abbot
from ..abbot.core import Abbot
from ..abbot.utils import (
    bot_squawk,
    bot_squawk_error,
    calculate_tokens,
    parse_group_chat_data,
    parse_dm_chat_data,
    parse_message,
    parse_message_data,
    parse_message_data_keys,
    parse_user_data,
    parse_update_data,
    to_int,
    get_chat_admins,
)
from ..payments import Coinbase, CoinbasePrice, init_payment_processor, init_price_provider
from ..abbot.exceptions.exception import AbbotException
from ..abbot.telegram.filter_abbot_reply import FilterAbbotReply

payment_processor = init_payment_processor()
price_provider: Coinbase = init_price_provider()

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)

FILE_NAME = __name__
NL = "\n"
DNL = "\n\n"
USD_EG = "For usd: /fund 10 usd"
SATS_EG = "For sats: /fund 5000 sats"

ERR_NO_GROUP = "No group or group config"
ERR_NO_GROUP_CONF = "No group config"
ERR_NO_GROUP_OR_CONF = f"{ERR_NO_GROUP} or {ERR_NO_GROUP_CONF}"
ERR_INV_UNIT = "Unrecognized currency unit. Did you pass one of usd or sats?"
ERR_INV_ARGS = "Missing amount and currency unit. Did you pass an amount and a currency unit?"
ERR_INV_CREATE = f"Failed to create invoice. Please try again"
ERR_INV_CREATE_LNADDR = f"or pay to {BOT_LIGHTNING_ADDRESS} and contact @{BOT_TELEGRAM_SUPPORT_CONTACT}"
ERR_INV_CREATE = f"{ERR_INV_CREATE} {ERR_INV_CREATE_LNADDR}"
ERR_INV_CANCEL = "Failed to cancel invoice"
WARN_GROUP_NOSATS = "WARNING: Your group balance is 0 😢 Please run /fund to continue to chat"
ERR_NO_SATS = f"No sats left 😢 Please run /fund to topup{DNL}*Examples*{NL}/fund 5 usd{NL}/fund 5000 sats"
# ---------------------------------------------------------------------------------------
# --                      Telegram Handlers Helper Functions                           --
# ---------------------------------------------------------------------------------------


async def get_live_price() -> int:
    log_name: str = f"{FILE_NAME}: get_live_price"
    response: Dict[CoinbasePrice] = await price_provider.get_bitcoin_price()
    debug_bot.log(log_name, f"response={response}")
    data = try_get(response, "data")
    amount = try_get(data, "amount")
    if not data or not amount:
        error_message = try_get(response, "msg")
        error_data = try_get(response, "data")
        error_bot.log(log_name, f"response={response} error_message={error_message} error_data={error_data}")
        return error(error_message, data=error_data)
    debug_bot.log(log_name, f"data={data} \n amount={amount}")
    return int(amount)


async def usd_to_sat(usd_amount: int) -> int:
    price_dict: Dict[CoinbasePrice] = mongo_abbot.find_prices()[-1]
    btc_price_usd: int = try_get(price_dict, "amount")
    if btc_price_usd:
        if type(btc_price_usd) != int:
            btc_price_usd: int = int(btc_price_usd)
    else:
        btc_price_usd: int = await get_live_price()
    amount_calculation = int((usd_amount / int(btc_price_usd)) * SATOSHIS_PER_BTC)
    return amount_calculation if amount_calculation > 0 else 0


async def sat_to_usd(sats_amount: int) -> int:
    price_dict: Dict[CoinbasePrice] = mongo_abbot.find_prices()[-1]
    btc_price_usd: int = try_get(price_dict, "amount")
    if btc_price_usd:
        if type(btc_price_usd) != int:
            btc_price_usd: int = int(btc_price_usd)
    else:
        btc_price_usd: int = await get_live_price()
    amount_calculation = round(float((sats_amount / SATOSHIS_PER_BTC) * int(btc_price_usd)), 2)
    return amount_calculation if amount_calculation > 0 else 0


async def calculate_completion_cost(input_tokens: int, output_tokens: int):
    try:
        log_name: str = f"{FILE_NAME}: calculate_completion_cost"
        btcusd_doc = mongo_abbot.find_prices()[-1]
        debug_bot.log(log_name, f"btcusd_doc={btcusd_doc}")
        timestamp: int = try_get(btcusd_doc, "_id", default=0)
        debug_bot.log(log_name, f"timestamp={timestamp}")
        btcusd_price: float = try_get(btcusd_doc, "amount")
        debug_bot.log(log_name, f"btcusd_price={btcusd_price}")
        now: int = int(time.time())
        debug_bot.log(log_name, f"now={now}")
        if btcusd_doc or now - timestamp >= 900:
            debug_bot.log(log_name, f"now - timestamp={now - timestamp}")
            btcusd_price: int = await get_live_price()
        btcusd_price = float(btcusd_price)
        cost_input_tokens = (input_tokens / ORG_PER_TOKEN_COST_DIV) * (ORG_INPUT_TOKEN_COST * ORG_TOKEN_COST_MULT)
        cost_output_tokens = (output_tokens / ORG_PER_TOKEN_COST_DIV) * (ORG_OUTPUT_TOKEN_COST * ORG_TOKEN_COST_MULT)
        total_token_cost_usd = cost_input_tokens + cost_output_tokens
        total_token_cost_sats = int((total_token_cost_usd / btcusd_price) * SATOSHIS_PER_BTC)

        return dict(status="success", cost_usd=total_token_cost_usd, cost_sats=total_token_cost_sats)
    except AbbotException as abbot_exception:
        raise dict(status="error", data=abbot_exception)


def sanitize_md_v2(text):
    escape_chars = "_[]()~>#+-=|{}.!^@$%&;:?/<,"
    return "".join(
        "\\" + char if char in escape_chars else char for char in text if not (0xD800 <= ord(char) <= 0xDFFF)
    )


def get_balance_message(chat_title, sat_balance, usd_balance):
    group = f"💬 *{chat_title}* 💬"
    satoshis = f"⚖️ *Balance in Satoshis* {sat_balance} sats ⚡️"
    fiat = f"⚖️ *Balance in Fiat* {usd_balance} usd 💰"
    balance_message = f"{group}{DNL}{satoshis}{DNL}{fiat}{DNL}"
    if 0 in (sat_balance, usd_balance):
        balance_message = f"{balance_message}{ERR_NO_SATS}"
    return balance_message


def format_naked_bot_command(command):
    return f"/{command}{BOT_TELEGRAM_HANDLE}"


BOT_HELP_COMMAND = format_naked_bot_command("help")
BOT_RULES_COMMAND = format_naked_bot_command("rules")
BOT_START_COMMAND = format_naked_bot_command("start")
BOT_STOP_COMMAND = format_naked_bot_command("stop")
BOT_UNLEASH_COMMAND = format_naked_bot_command("unleash")
BOT_LEASH_COMMAND = format_naked_bot_command("leash")
BOT_BALANCE_COMMAND = format_naked_bot_command("balance")
BOT_FUND_COMMAND = format_naked_bot_command("fund")
BOT_STATUS_COMMAND = format_naked_bot_command("status")
BOT_COUNT_COMMAND = format_naked_bot_command("count")
# ---------------------------------------------------------------------------------------
# --                      Core Telegram Handler Functions                              --
# ---------------------------------------------------------------------------------------


async def handle_group_adds_abbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: handle_group_adds_abbot"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        message_data: Dict = parse_message_data_keys(message, keys=["group_chat_created", "new_chat_members"])
        group_chat_created = message_data.get("group_chat_created", None)
        new_chat_members = message_data.get("new_chat_members", None)
        chat: Chat = try_get(update_data, "chat")
        chat_id, chat_title, chat_type = parse_group_chat_data(chat)
        admins = await get_chat_admins(chat_id, context)
        debug_bot.log(log_name, f"admins={admins}")
        if not group_chat_created and new_chat_members:
            if BOT_TELEGRAM_HANDLE not in [username for username in new_chat_members]:
                return debug_bot.log(log_name, "Abbot not added to group")
        chat_id_filter = {"id": chat_id}
        default_history = [BOT_SYSTEM_OBJECT_GROUPS]
        token_count: int = calculate_tokens(default_history)
        group_update = {
            "$set": {
                "id": chat_id,
                "title": chat_title,
                "type": chat_type,
                "admins": admins,
                "created_at": datetime.now().isoformat(),
                "balance": 5000,
                "messages": [],
                "history": default_history,
                "config": BOT_GROUP_CONFIG_DEFAULT,
                "tokens": token_count,
            }
        }
        group: TelegramGroup = mongo_abbot.group_does_exist(chat_id_filter)
        if group:
            group_update = {"$set": {"title": chat_title, "id": chat_id, "type": chat_type, "admins": admins}}
        group: TelegramGroup = mongo_abbot.find_one_group_and_update(chat_id_filter, group_update)
        squawk_msg = f"{THE_ARCHITECT_HANDLE} New group added Abbot!\n\ntitle={chat_title}\nchat_id={chat_id}"
        await bot_squawk(log_name, squawk_msg, context)
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def handle_group_message_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: handle_group_message_edit"
        debug_bot.log(log_name, f"update={update}")
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def handle_markdown_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: handle_markdown_request"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        debug_bot.log(log_name, f"message={message}")
        message_text, message_date = parse_message_data(message)
        debug_bot.log(log_name, f"message_text={message_text} message_date={message_date}")
        reply_to_message: Optional[Message] = try_get(message, "reply_to_message")
        debug_bot.log(log_name, f"reply_to_message={reply_to_message.__str__()}")
        reply_to_message_text = try_get(reply_to_message, "text")
        debug_bot.log(log_name, f"reply_to_message_text={reply_to_message_text}")
        chat: Chat = try_get(update_data, "chat")
        debug_bot.log(log_name, f"chat={chat}")
        chat_id, chat_title, chat_type = parse_group_chat_data(chat)
        debug_bot.log(log_name, f"chat_id={chat_id} chat_title={chat_title} chat_type={chat_type}")
        user: User = try_get(update_data, "user")
        debug_bot.log(log_name, f"user={user}")
        reply_to_message_from_user: Optional[User] = try_get(reply_to_message, "from_user")
        replied_to_bot = try_get(reply_to_message_from_user, "is_bot")
        debug_bot.log(log_name, f"replied_to_bot={replied_to_bot}")
        replied_to_abbot = try_get(reply_to_message_from_user, "username") == BOT_TELEGRAM_USERNAME
        debug_bot.log(log_name, f"replied_to_abbot={replied_to_abbot}")
        if replied_to_bot and replied_to_abbot and reply_to_message_text != None:
            sanitized_text = sanitize_md_v2(reply_to_message_text)
            await message.reply_markdown_v2(sanitized_text)
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: help"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        sanitized_text = sanitize_md_v2(HELP_MENU)
        await message.reply_markdown_v2(sanitized_text, disable_web_page_preview=True)
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: rules"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        await message.reply_markdown_v2(RULES, disable_web_page_preview=True)
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: start"
        response: Dict = parse_message(update)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_message response={response}")
        debug_bot.log(log_name, f"response={response}")
        message: Message = try_get(response, "data")
        if not message:
            squawk_msg = f"No message object: update={update} response={response} message={message}"
            return await bot_squawk_error(log_name, squawk_msg, context)
        debug_bot.log(log_name, f"message={message}")
        message_text, _ = parse_message_data(message)
        chat: Chat = try_get(message, "chat")
        chat_id, chat_title, chat_type = parse_group_chat_data(chat)
        user: User = try_get(message, "from_user")
        user_id, username, first_name = parse_user_data(user)
        is_handle = True
        if not username:
            username = first_name
            is_handle = False
        if not username:
            username = user_id
            is_handle = False
        intro_history_dict = {"role": "assistant", "content": INTRODUCTION}
        new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}
        if not username:
            new_history_dict = {"role": "user", "content": f"someone said: {message_text}"}
        elif not is_handle:
            new_history_dict = {"role": "user", "content": f"{username} said: {message_text}"}
        if chat_type not in ("group", "supergroup", "channel"):
            return await message.reply_text(f"{BOT_START_COMMAND} is disabled in DMs. Feel free to chat at will!")
        chat_id_filter = {"id": chat_id}
        new_message_dict = message.to_dict()
        group: TelegramGroup = mongo_abbot.find_one_group(chat_id_filter)
        if not group:
            debug_bot.log(log_name, f"no group found chat_id={chat_id} chat_title={chat_title}")
            await bot_squawk(log_name, f"no group found chat_id={chat_id} chat_title={chat_title}", context)
            group: TelegramGroup = mongo_abbot.find_one_group_and_update(
                chat_id_filter,
                {
                    "$set": {
                        "created_at": datetime.now().isoformat(),
                        "title": chat_title,
                        "id": chat_id,
                        "type": chat_type,
                        "balance": 5000,
                        "messages": [new_message_dict],
                        "history": [BOT_SYSTEM_OBJECT_GROUPS, intro_history_dict, new_history_dict],
                        "config": BOT_GROUP_CONFIG_STARTED,
                    }
                },
            )

        group_history: List = try_get(group, "history")
        group_history = [*group_history, new_history_dict]

        group_config: Dict = try_get(group, "config")
        debug_bot.log(log_name, f"group_config={group_config}")

        started: Dict = try_get(group_config, "started")
        debug_bot.log(log_name, f"started={started}")

        introduced: Dict = try_get(group_config, "introduced")
        debug_bot.log(log_name, f"introduced={introduced}")

        group_balance: int = try_get(group, "balance")
        debug_bot.log(log_name, f"group_balance={group_balance}")
        balance_is_zero = group_balance == 0
        if balance_is_zero:
            balance_message: str = sanitize_md_v2(get_balance_message(chat_title, group_balance, 0))
            # reuse buttons to ask if they want an invoice
            # or send an invoice
            return await message.reply_markdown_v2(balance_message)

        if started:
            debug_bot.log(log_name, f"started={started}")
            already_started = f"Hey\! I'm already started and ready to rock and roll 🪨🤘🎸"
            already_started = f"{already_started}\n\nFeel free to run /rules or /help for more information"
            debug_bot.log(log_name, f"already_started={already_started}")
            await bot_squawk(log_name, already_started, context)
            return await message.reply_markdown_v2(already_started, disable_web_page_preview=True)
        elif not introduced:
            group: TelegramGroup = mongo_abbot.find_one_group_and_update(
                chat_id_filter,
                {
                    "$set": {
                        "title": chat_title,
                        "id": chat_id,
                        "balance": group_balance,
                        "config.started": True,
                        "config.introduced": True,
                    },
                    "$push": {
                        "messages": new_message_dict,
                        "history": new_history_dict,
                    },
                },
            )
            await message.reply_photo(MATRIX_IMG_FILEPATH, f"Please wait while {BOT_NAME} is unplugged from the Matrix")
            time.sleep(3)
            return await message.reply_markdown_v2(INTRODUCTION, disable_web_page_preview=True)

        abbot = Abbot(chat_id, "group", group_history)
        answer, input_tokens, output_tokens, _ = abbot.chat_completion(chat_title)

        response: Dict = await calculate_completion_cost(input_tokens, output_tokens)
        if not successful(response):
            err_msg = f"{log_name}: calculate_completion_cost: not successful"
            bal_msg = f"group_balance={group_balance}"
            res_msg = f"response={response}"
            chat_msg = f"chat_id={chat_id}\nchat_title={chat_title}"
            squawk_msg = f"{err_msg}: {bal_msg} {res_msg} {chat_msg}"
            await bot_squawk(log_name, squawk_msg, context)

        cost_sats: int = try_get(response, "cost_sats", default=500)
        group_balance -= cost_sats
        balance_is_below_zero = group_balance < 0
        if balance_is_below_zero:
            group_balance = 0
            squawk_msg = f"Group balance: {group_balance}\n\chat_id={chat_id}\chat_title={chat_title}"
            answer = f"{answer}\n\n{WARN_GROUP_NOSATS}"
            debug_bot.log(log_name, squawk_msg)
            await bot_squawk(log_name, squawk_msg, context)

        debug_bot.log(log_name, f"group_balance={group_balance}")
        group_history = abbot.get_history()

        group: TelegramGroup = mongo_abbot.find_one_group_and_update(
            chat_id_filter,
            {
                "$set": {
                    "title": chat_title,
                    "id": chat_id,
                    "balance": group_balance,
                    "tokens": abbot.history_tokens,
                    "config.started": True,
                },
                "$push": {
                    "messages": new_message_dict,
                    "history": new_history_dict,
                },
            },
        )
        if "`" in answer or "**" in answer:
            return await message.reply_markdown_v2(sanitize_md_v2(answer), disable_web_page_preview=True)
        return await message.reply_text(answer, disable_web_page_preview=True)
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: stop"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")

        message: Message = try_get(update_data, "message")
        message_text, _ = parse_message_data(message)
        new_message_dict = message.to_dict()
        debug_bot.log(log_name, f"message={message}")

        chat: Chat = try_get(update_data, "chat")
        chat_id, chat_title, chat_type = parse_group_chat_data(chat)
        debug_bot.log(log_name, f"chat={chat}")
        chat_id_filter = {"id": chat_id}

        user: User = try_get(update_data, "user")
        user_id, username, first_name = parse_user_data(user)
        username: str = username or first_name or user_id or "someone"
        new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}
        debug_bot.log(log_name, f"user={user}")

        group_exists: bool = mongo_abbot.group_does_exist(chat_id_filter)
        if not group_exists:
            squawk = f"Group does not exist"
            reply_msg = f"There is no group 🥄👀 Try running /start or contact {THE_ARCHITECT_HANDLE} for help."
            await message.reply_text(reply_msg)
            abbot_squawk = f"{squawk}\n\nchat_id={chat_id}, chat_title={chat_title}"
            await bot_squawk(log_name, abbot_squawk, context)
        debug_bot.log(log_name, f"group_exists={group_exists}")

        group: TelegramGroup = mongo_abbot.find_one_group_and_update(
            chat_id_filter,
            {
                "$set": {
                    "title": chat_title,
                    "id": chat_id,
                    "config.started": False,
                },
                "$push": {
                    "messages": new_message_dict,
                    "history": new_history_dict,
                },
            },
        )
        still_running: bool = try_get(group, "config", "started")
        if still_running:
            reply_text_err = f"Failed to stop {BOT_NAME}. Please try again or contact {THE_ARCHITECT_HANDLE} for help"
            abbot_squawk = f"{log_name}: {reply_text_err} => chat_id={chat_id}, chat_title={chat_title}"
            error_bot.log(log_name, abbot_squawk)
            await message.reply_text(reply_text_err)
            return await bot_squawk(log_name, abbot_squawk, context)

        await bot_squawk(log_name, f"{BOT_NAME} stopped\n\nchat_id={chat_id}, chat_title={chat_title}", context)
        await message.reply_text(f"Thanks for using {BOT_NAME}! Come back soon!")
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: balance"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")

        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")

        message: Message = try_get(update_data, "message")
        chat: Chat = try_get(update_data, "chat")
        chat_id, chat_title, chat_type = parse_group_chat_data(chat)
        if chat_type == "private":
            return await message.reply_text("/balance is disabled in DMs. Feel free to chat at will!")

        chat_id_filter = {"id": chat_id}
        group: TelegramGroup = mongo_abbot.find_one_group(chat_id_filter)

        group_balance = try_get(group, "balance", default=0)
        if group_balance and type(group_balance) == float:
            group: TelegramGroup = mongo_abbot.find_one_dm_and_update(
                chat_id_filter, {"$set": {"balance": int(group_balance)}}
            )
            group_balance = try_get(group, "balance", default=0)
        usd_balance = await sat_to_usd(group_balance)
        balance_message: str = sanitize_md_v2(get_balance_message(chat_title, group_balance, usd_balance))
        return await message.reply_markdown_v2(balance_message)
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def unleash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: unleash"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")

        message: Message = try_get(update_data, "message")
        message_text, message_date = parse_message_data(message)
        message_text: str = message_text.split()
        debug_bot.log(log_name, f"message_text={message_text} message_date={message_date}")

        chat: Chat = try_get(update_data, "chat")
        chat_id, _, chat_type = parse_group_chat_data(chat)
        if chat_type == "private":
            return await message.reply_text("/unleash is disabled in DMs. Feel free to chat at will!")

        new_count: str = try_get(message_text, 1)
        new_count: Optional[int] = to_int(new_count)
        if not new_count or new_count <= 0:
            new_count: int = 5
        chat_id_filter = {"id": chat_id}
        group: TelegramGroup = mongo_abbot.find_one_group(chat_id_filter)
        if not group:
            return await message.reply_text(f"{ERR_NO_GROUP} - Did you run /start{BOT_TELEGRAM_HANDLE}?")
        current_sats: int = try_get(group, "balance")
        if current_sats == 0:
            return await message.reply_text(ERR_NO_SATS)
        group: TelegramGroup = mongo_abbot.find_one_group_and_update(
            chat_id_filter, {"$set": {"config.unleashed": True, "config.count": new_count}}
        )
        await message.reply_text(f"Abbot has been unleashed to respond every {new_count} messages")
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def leash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: leash"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        chat: Chat = try_get(update_data, "chat")
        chat_id, _, chat_type = parse_group_chat_data(chat)
        if chat_type == "private":
            return await message.reply_text("/leash is disabled in DMs. Feel free to chat at will!")
        chat_id_filter = {"id": chat_id}
        group: TelegramGroup = mongo_abbot.find_one_group(chat_id_filter)
        if not group:
            return await message.reply_text(f"{ERR_NO_GROUP} - Did you run /start{BOT_TELEGRAM_HANDLE}?")
        group_config: Dict = mongo_abbot.get_group_config(chat_id_filter)
        unleashed: bool = try_get(group_config, "unleashed")
        if unleashed:
            group: TelegramGroup = mongo_abbot.find_one_group_and_update(
                chat_id_filter, {"$set": {"config.unleashed": False}}
            )
        await message.reply_text(f"Abbot has been leashed to not respond on message count")
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: status"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        debug_bot.log(log_name, f"message={message}")
        chat: Chat = try_get(update_data, "chat")
        debug_bot.log(log_name, f"chat={chat}")
        chat_id, chat_title, chat_type = parse_group_chat_data(chat)
        if chat_type == "private":
            return await message.reply_text("/status is disabled in DMs. Feel free to chat at will!")
        chat_id_filter = {"id": chat_id}
        group_config: Dict = mongo_abbot.get_group_config(chat_id_filter)
        if not group_config:
            abbot_squawk = f"{log_name}: {ERR_NO_GROUP_CONF}:"
            error_msg = f"id={chat_id}, title={chat_title}, group_config={group_config}"
            abbot_squawk = f"{abbot_squawk}\n\n{error_msg}"
            reply_text_err = f"Failed to get group status. Please contact {THE_ARCHITECT_HANDLE} for assistance."
            error_bot.log(log_name, abbot_squawk)
            await bot_squawk(log_name, abbot_squawk, context)
            return await message.reply_text(reply_text_err)
        debug_bot.log(log_name, f"group_config={group_config}")
        group_started: bool = try_get(group_config, "started")
        group_introduced: bool = try_get(group_config, "introduced")
        group_unleashed: bool = try_get(group_config, "unleashed")
        group_count: int = try_get(group_config, "count", default=0)

        group_msg = f"💬 *Group*: {chat_title} 💬"
        started = f"🚀 *Started*: {group_started} 🚀"
        introduced = f"🗣️ *Introduced*: {group_introduced} 🗣️"
        unleashed = f"🦮 *Unleashed*: {group_unleashed} 🦮"
        count = f"🧛‍♀️ *Count*: {group_count} 🧛‍♀️"
        full_msg = sanitize_md_v2(f"{group_msg}\n{started}\n{introduced}\n{unleashed}\n{count}")
        await message.reply_markdown_v2(full_msg)
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: count"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        debug_bot.log(log_name, f"message={message}")
        chat: Chat = try_get(update_data, "chat")
        debug_bot.log(log_name, f"chat={chat}")
        chat_id, chat_title, chat_type = parse_group_chat_data(chat)
        chat_id_filter = {"id": chat_id}
        group_history: Dict = mongo_abbot.get_group_history(chat_id_filter)
        group_config: Dict = mongo_abbot.get_group_config(chat_id_filter)
        if not group_history or not group_config:
            abbot_squawk = f"{log_name}: {ERR_NO_GROUP_CONF}:"
            error_msg = f"id={chat_id}, title={chat_title}, group_history={group_history}"
            abbot_squawk = f"{abbot_squawk}\n\n{error_msg}"
            reply_text_err = f"Failed to get group history count. Please contact {THE_ARCHITECT_HANDLE} for assistance."
            error_bot.log(log_name, abbot_squawk)
            await bot_squawk(log_name, abbot_squawk, context)
            return await message.reply_text(reply_text_err)
        unleashed_count: int = try_get(group_config, "count", default=0)
        history_count: int = len(group_history)
        counts_msg = f"🧛‍♀️ *Unleashed Count*: {unleashed_count}\n💬 *History Count*: {history_count}"
        remaining = unleashed_count - (history_count % unleashed_count)
        full_msg = sanitize_md_v2(f"{counts_msg}\n\n🤖 Abbot responds in {remaining}")
        await message.reply_markdown_v2(full_msg)
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def fund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: fund"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        message_text: str = try_get(message, "text")
        debug_bot.log(log_name, f"message_text={message_text}")
        chat: Chat = try_get(update_data, "chat")
        debug_bot.log(log_name, f"chat={chat}")
        chat_id, chat_title, chat_type = parse_group_chat_data(chat)
        if payment_processor.CHAT_ID_INVOICE_ID_MAP.get(chat_id, None):
            return await message.reply_text("Active invoice already issued")
        chat_type: str = chat_type.capitalize()
        if chat_type == "Private":
            return await message.reply_text("/fund is disabled in DMs. Feel free to chat at will!")
        user: User = try_get(update_data, "user")
        debug_bot.log(log_name, f"user={user}")
        user_id, username, first_name = parse_user_data(user)
        username: str = username or first_name or user_id or "someone"
        topup_for: str = chat_title
        topup_by: str = username
        args = message_text.split()
        args_len = len(args)
        debug_bot.log(log_name, f"args={args}")
        if args_len < 2:
            return await message.reply_text(f"{ERR_INV_ARGS}\n{SATS_EG}\n{USD_EG}")
        elif args_len < 3:
            return await message.reply_text(f"{ERR_INV_ARGS}\n{SATS_EG}\n{USD_EG}")
        amount: str = try_get(args, 1)
        if "." in amount:
            amount: float = float(try_get(args, 1))
        else:
            amount: int = int(try_get(args, 1))
        if amount < 1:
            one_usd_in_sats: int = await usd_to_sat(1)
            return await message.reply_text(f"Amount too low. Must be at least 1 usd or {one_usd_in_sats} sats")
        debug_bot.log(log_name, f"amount={amount}")
        currency_unit: str = try_get(args, 2, default="sats")
        currency_unit = currency_unit.lower()
        debug_bot.log(log_name, f"currency_unit={currency_unit}")
        if currency_unit == "sats":
            currency_unit = "SATS"
            emoji = "⚡️"
            symbol = ""
            invoice_amount = await sat_to_usd(amount)
            sats_balance = amount
        elif currency_unit == "usd":
            currency_unit = "USD"
            emoji = "💰"
            symbol = "$"
            invoice_amount = amount
            sats_balance = await usd_to_sat(amount)
        else:
            return await message.reply_text(f"{ERR_INV_UNIT}\n\n{SATS_EG}\n\n{USD_EG}")
        await message.reply_text("Creating your invoice, please wait ...")
        debug_bot.log(log_name, f"payment_processor={payment_processor}")
        debug_bot.log(log_name, f"amount={amount}")
        debug_bot.log(log_name, f"invoice_amount={invoice_amount}")
        group_msg = f"💬 *Group* 💬\n{topup_for}\n"
        sender_msg = f"✉️ *Requested by* ✉️\n@{topup_by}\n"
        amount_msg = f"{emoji} *Amount* {emoji}\n{symbol}{amount} {currency_unit}\n"
        cid = str(uuid.uuid1())
        description = f"{group_msg}{sender_msg}{amount_msg}"
        debug_bot.log(log_name, f"description={description}")
        response = await payment_processor.get_invoice(cid, description, invoice_amount, chat_id)
        debug_bot.log(log_name, f"response={response}")
        create_squawk = f"Failed to create strike invoice: {json.dumps(response)}"
        if not successful(response):
            await bot_squawk(log_name, create_squawk, context)
            return await message.reply_text(ERR_INV_CREATE)
        invoice_id = try_get(response, "invoice_id")
        invoice = try_get(response, "ln_invoice")
        expiration_in_sec = try_get(response, "expiration_in_sec")
        payment_processor.CHAT_ID_INVOICE_ID_MAP[chat_id] = invoice_id
        if None in (invoice_id, invoice, expiration_in_sec):
            await bot_squawk(log_name, create_squawk, context)
            return await message.reply_text(ERR_INV_CREATE)
        expires_msg = f"🕰️ *Expires in*: {expiration_in_sec} seconds\n"
        description = f"{description}\n{expires_msg}"
        await message.reply_photo(photo=qr_code(invoice), caption=sanitize_md_v2(description), parse_mode=MARKDOWN_V2)
        await message.reply_markdown_v2(f"`{invoice}`")
        cancel_squawk = f"{ERR_INV_CANCEL}: description={description}, invoice_id={invoice_id}"
        is_paid = False
        while expiration_in_sec >= 0 and not is_paid:
            debug_bot.log(log_name, f"expiration_in_sec={expiration_in_sec}")
            is_paid = await payment_processor.invoice_is_paid(invoice_id)
            debug_bot.log(log_name, f"is_paid={is_paid}")
            expiration_in_sec -= 1
            if expiration_in_sec == 0:
                debug_bot.log(log_name, f"expiration_in_sec == 0, invoice_id={invoice_id}")
                break
            time.sleep(1)
        if is_paid:
            group: TelegramGroup = mongo_abbot.find_one_group_and_update(
                {"id": chat_id}, {"$inc": {"balance": sats_balance}}
            )
            if not group:
                error_bot.log(log_name, f"not group")
                return await bot_squawk(log_name, group, context)
            balance: int = try_get(group, "balance", default=amount)
            await message.reply_text(f"Invoice Paid! ⚡️ {chat_title} balance: {balance} sats ⚡️")
        else:
            keyboard = [[InlineKeyboardButton("Yes", callback_data="1"), InlineKeyboardButton("No", callback_data="2")]]
            await bot_squawk(log_name, cancel_squawk, context)
            keyboard_markup = InlineKeyboardMarkup(keyboard)
            await message.reply_text(f"Invoice expired! Try again?", reply_markup=keyboard_markup)
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def fund_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: fund_button"
        query: Optional[CallbackQuery] = try_get(update, "callback_query")
        update_id: int = try_get(update, "update_id")
        message: Message = try_get(query, "message")
        chat: Chat = try_get(message, "chat")
        chat_id: int = try_get(chat, "id")
        await query.answer()
        if query.data == "1":
            reply_to_message: Message = try_get(message, "reply_to_message")
            update: Update = Update(update_id=update_id, message=reply_to_message)
            await fund(update, context)
        elif query.data == "2":
            ln_addr = "You can also pay my LN address abbot@atlbitlab.com"
            contact = "If you do, be sure to contact @nonni_io to ensure you get credit"
            reply_msg = f"{ln_addr} ⚡️\n{contact}"
            await query.edit_message_text(reply_msg)
            invoice_id = payment_processor.CHAT_ID_INVOICE_ID_MAP.get(chat_id, None)
            if not invoice_id:
                chat_inv_map = payment_processor.CHAT_ID_INVOICE_ID_MAP
                abbot_squawk = f"Cannot cancel invoice: no invoice_id: chat_inv_map={chat_inv_map}"
                return await bot_squawk(log_name, abbot_squawk, context)
            cancelled = await payment_processor.expire_invoice(invoice_id)
            if not cancelled:
                cancel_squawk = f"{ERR_INV_CANCEL}: chat_id={chat_id}, invoice_id={invoice_id}"
                await bot_squawk(log_name, cancel_squawk, context)
            debug_bot.log(log_name, f"invoice_id={invoice_id} cancelled={cancelled}")
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def handle_group_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: handle_group_mention"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        debug_bot.log(log_name, f"message={message}")
        message_text, message_date = parse_message_data(message)
        debug_bot.log(log_name, f"message_text={message_text} message_date={message_date}")
        chat: Chat = try_get(update_data, "chat")
        debug_bot.log(log_name, f"chat={chat}")
        chat_id, chat_title, chat_type = parse_group_chat_data(chat)
        debug_bot.log(log_name, f"chat_id={chat_id} chat_title={chat_title} chat_type={chat_type}")
        user: User = try_get(update_data, "user")
        debug_bot.log(log_name, f"user={user}")
        user_id, username, first_name = parse_user_data(user)
        debug_bot.log(log_name, f"username={username}")
        if not username:
            username = try_get(user, "first_name")
        if chat_type not in ("group", "supergroup", "channel"):
            debug_bot.log(log_name, f"chat_type={chat_type}")
        chat_id_filter = {"id": chat_id}
        stopped_err = f"{BOT_NAME} not started - Please run /start{BOT_TELEGRAM_HANDLE}"
        group: TelegramGroup = mongo_abbot.find_one_group(chat_id_filter)
        group_config: Dict = try_get(group, "config")
        group_balance: int = try_get(group, "balance")
        if not group or not group_config:
            abbot_squawk = f"{log_name}: {ERR_NO_GROUP}: id={chat_id}, title={chat_title}"
            error_msg = f"{ERR_NO_GROUP}: group={group} group_config={group_config}"
            abbot_squawk = f"{abbot_squawk}\n\n{error_msg}"
            error_bot.log(log_name, abbot_squawk)
            return await bot_squawk(log_name, abbot_squawk, context)
        debug_bot.log(log_name, f"group_config={group_config}")
        started: bool = try_get(group_config, "started")
        debug_bot.log(log_name, f"started={started}")
        if not started:
            abbot_squawk = f"{log_name}: {stopped_err}: id={chat_id}, title={chat_title}"
            error_bot.log(log_name, abbot_squawk)
            await bot_squawk(log_name, abbot_squawk, context)
            return await message.reply_text(stopped_err)
        new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}
        if not message_text:
            message_text_err = f"{log_name}: No message text: message={message} update={update}"
            return await bot_squawk(log_name, message_text_err, context)
        if not username:
            new_history_dict = {"role": "user", "content": f"someone said: {message_text}"}
        else:
            new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}
        group_history: List[Dict] = [*try_get(group, "history", default=[]), new_history_dict]
        if not group or not group_history:
            abbot_squawk = f"{log_name}: {ERR_NO_GROUP}: id={chat_id}, title={chat_title}"
            error_msg = f"{ERR_NO_GROUP}: group={group} group_config={group_config}"
            abbot_squawk = f"{abbot_squawk}\n\n{error_msg}"
            error_bot.log(log_name, abbot_squawk)
            await message.reply_text(stopped_err)
            return await bot_squawk(log_name, abbot_squawk, context)
        debug_bot.log(log_name, f"group_config={group_config}")
        if group_balance == 0:
            reply_msg = f"No sats left 😢 Run `/fund <amount> <currency>`"
            reply_msg = f"{reply_msg} to refill your sats and continue chatting\n\n"
            reply_msg = f"{reply_msg}e.g. `/fund 10000 sats`\n`/fund 10 usd`"
            abbot_squawk = f"Group balance: {group_balance}\n\ngroup_id={chat_id}\ngroup_title={chat_title}"
            await bot_squawk(log_name, abbot_squawk, context)
            return await message.reply_markdown_v2(sanitize_md_v2(reply_msg))
        abbot = Abbot(chat_id, "group", group_history)
        answer, input_tokens, output_tokens, total_tokens = abbot.chat_completion(chat_title)
        await bot_squawk(log_name, f"chat_id={chat_id} chat_title={chat_title} total_tokens={total_tokens}", context)
        response: Dict = await calculate_completion_cost(input_tokens, output_tokens)
        if not successful(response):
            sub_log_name = f"{log_name}: calculate_completion_cost"
            error_bot.log(log_name, f"response={response}")
            msg = f"{sub_log_name}: Failed to calculate remaining sats"
            msg = f"{msg}: group_balance={group_balance}\nresponse={response}\nchat=(id={chat_id}\ntitle=({chat_title})"
            error_bot.log(log_name, msg)
            await bot_squawk(log_name, msg, context)
        cost_sats: int = try_get(response, "cost_sats", default=500)
        group_balance = 0 if group_balance < 0 else group_balance - cost_sats
        if group_balance == 0:
            abbot_squawk = f"Group balance: {group_balance}\n\ngroup_id={chat_id}\ngroup_title={chat_title}"
            answer = f"{answer}\n\n{WARN_GROUP_NOSATS}"
            debug_bot.log(log_name, abbot_squawk)
            await bot_squawk(log_name, abbot_squawk, context)
        debug_bot.log(log_name, f"group_balance={group_balance}")
        assistant_history_update = {"role": "assistant", "content": answer}
        group_history = abbot.get_history()
        new_message_dict = message.to_dict()
        group: TelegramGroup = mongo_abbot.find_one_group_and_update(
            chat_id_filter,
            {
                "$set": {
                    "title": chat_title,
                    "id": chat_id,
                    "balance": group_balance,
                    "tokens": abbot.history_tokens,
                },
                "$push": {"messages": new_message_dict, "history": assistant_history_update},
            },
        )
        if "`" in answer or "**" in answer:
            return await message.reply_markdown_v2(sanitize_md_v2(answer), disable_web_page_preview=True)
        return await message.reply_text(answer, disable_web_page_preview=True)
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def handle_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: handle_group_reply: "
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")

        message: Message = try_get(update_data, "message")
        debug_bot.log(log_name, f"message={message}")

        chat: Chat = try_get(update_data, "chat")
        chat_id, chat_title, chat_type = parse_group_chat_data(chat)
        group_detail_msg: str = f"chat_id={chat_id}\nchat_title={chat_title}"
        debug_bot.log(log_name, group_detail_msg)
        debug_bot.log(log_name, f"chat={chat}")

        user: User = try_get(update_data, "user")
        debug_bot.log(log_name, f"user={user}")

        message_text, message_date = parse_message_data(message)
        if not message_text:
            message_text_err = f"{log_name}: No message text: message={message} update={update}"
            return await bot_squawk(log_name, message_text_err, context)
        debug_bot.log(log_name, f"message_text={message_text} message_date={message_date}")

        user_id, username, first_name = parse_user_data(user)
        username: str = username or first_name or user_id or "someone"
        reply_to_message: Optional[Message] = try_get(message, "reply_to_message")
        debug_bot.log(log_name, f"reply_to_message={reply_to_message.__str__()}")

        reply_to_message_text: Optional[Message] = try_get(reply_to_message, "text")
        debug_bot.log(log_name, f"reply_to_message_text={reply_to_message_text}")

        reply_to_message_from_user: Optional[User] = try_get(reply_to_message, "from_user")
        debug_bot.log(log_name, f"reply_to_message_from_user={reply_to_message_from_user}")

        replied_to_bot: Optional[bool] = try_get(reply_to_message_from_user, "is_bot")
        debug_bot.log(log_name, f"replied_to_bot={replied_to_bot}")

        reply_to_message_from_user_username: Optional[str] = try_get(reply_to_message_from_user, "username")
        debug_bot.log(log_name, f"reply_to_message_from_user_username={reply_to_message_from_user_username}")

        replied_to_abbot = reply_to_message_from_user_username in (BOT_TELEGRAM_USERNAME, BOT_TELEGRAM_HANDLE)
        debug_bot.log(log_name, f"replied_to_abbot={replied_to_abbot}")

        if not replied_to_abbot:
            return await bot_squawk(log_name, "Group reply not to Abbot: chat_id={} chat_title={}", context)

        chat_id_filter = {"id": chat_id}
        group: TelegramGroup = mongo_abbot.find_one_group(chat_id_filter)
        group_balance: Dict = try_get(group, "balance")
        group_history: List[Dict] = try_get(group, "history")
        group_config: Dict = try_get(group, "config")
        started: bool = try_get(group_config, "started")
        debug_bot.log(log_name, f"group_config={group_config} started={started}")

        reply_msg = f"{ERR_NO_GROUP} - Did you run /start{BOT_TELEGRAM_HANDLE}?"
        if not group or not group_config or not group_history:
            abbot_squawk = f"{log_name}: {ERR_NO_GROUP}: id={chat_id}, title={chat_title}"
            abbot_squawk = f"{abbot_squawk}\n\n{reply_msg}"
            error_bot.log(log_name, abbot_squawk)
            return await bot_squawk(log_name, abbot_squawk, context)

        if chat_type in ("group", "supergroup", "channel"):
            admins = await get_chat_admins(chat_id, context)
            debug_bot.log(log_name, f"admins={admins}")

        new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}
        if not username:
            new_history_dict = {"role": "user", "content": f"{username} said: {message_text}"}

        new_message_dict = message.to_dict()
        group: TelegramGroup = mongo_abbot.find_one_group_and_update(
            chat_id_filter,
            {
                "$set": {
                    "title": chat_title,
                    "id": chat_id,
                    "admins": admins,
                },
                "$push": {"messages": new_message_dict, "history": new_history_dict},
            },
        )
        group_id: str = try_get(group, "id")
        group_title: str = try_get(group, "title")
        group_created_at: str = try_get(group, "created_at")
        debug_bot.log(log_name, f"group_id={group_id} group_title={group_title} group_created_at={group_created_at}")
        if group_balance == 0:
            abbot_squawk = f"Group balance: {group_balance}\n\ngroup_id={chat_id}\ngroup_title={chat_title}"
            await bot_squawk(log_name, abbot_squawk, context)
            return await message.reply_text(ERR_NO_SATS)
        if replied_to_abbot:
            if started:
                abbot = Abbot(chat_id, "group", group_history)
                answer, input_tokens, output_tokens, _ = abbot.chat_completion(chat_title)
                response: Dict = await calculate_completion_cost(input_tokens, output_tokens)
                if not successful(response):
                    error_bot.log(log_name, f"response={response}")
                    sub_log_name = f"{log_name}: calculate_completion_cost"
                    calc_failed_msg = f"{sub_log_name}: Failed to calculate remaining sats"
                    abbot_squawk = f"{calc_failed_msg}: group_id={chat_id}\ngroup_title=({chat_title})"
                    abbot_squawk = f"{abbot_squawk}: group_balance={group_balance}\nresponse={response}\n"
                    error_bot.log(log_name, abbot_squawk)
                    await bot_squawk(log_name, abbot_squawk, context)
                debug_bot.log(log_name, f"response={response}")
                cost_sats: int = try_get(response, "cost_sats", default=500)
                group_balance = 0 if group_balance < 0 else group_balance - cost_sats
                if group_balance == 0:
                    abbot_squawk = f"Group balance: {group_balance}\n\ngroup_id={chat_id}\ngroup_title={chat_title}"
                    answer = f"{answer}\n\n{WARN_GROUP_NOSATS}"
                    debug_bot.log(log_name, abbot_squawk)
                    await bot_squawk(log_name, abbot_squawk, context)
                debug_bot.log(log_name, f"cost_sats={cost_sats}")
                debug_bot.log(log_name, f"group_balance={group_balance}")
                assistant_history_update = {"role": "assistant", "content": answer}
                group_history = abbot.get_history()
                token_count: int = calculate_tokens(group_history)
                group: TelegramGroup = mongo_abbot.find_one_group_and_update(
                    chat_id_filter,
                    {
                        "$set": {"balance": group_balance, "tokens": token_count},
                        "$push": {"history": assistant_history_update},
                    },
                )
                if "`" in answer or "**" in answer:
                    return await message.reply_markdown_v2(sanitize_md_v2(answer), disable_web_page_preview=True)
                await message.reply_text(answer, disable_web_page_preview=True)
            else:
                await message.reply_text(reply_msg)
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def handle_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: handle_dm"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        message_text, _ = parse_message_data(message)
        chat: Chat = try_get(update_data, "chat")
        chat_id, _, _ = parse_group_chat_data(chat)
        user_id, username, first_name = parse_dm_chat_data(chat)
        username: str = username or first_name or chat_id or user_id or "someone"
        chat_title: str = f"{BOT_NAME}-{username}-{chat_id}"
        # sender: User = try_get(update_data, "user")
        # sender_id, sender_username, sender_first_name = parse_user_data(sender)
        new_message_dict = message.to_dict()
        chat_id_filter = {"id": chat_id}
        dm_update = {
            "$set": {
                "created_at": datetime.now().isoformat(),
                "id": chat_id,
                "username": username,
                "type": "dm",
                "messages": [new_message_dict],
                "history": [BOT_SYSTEM_OBJECT_DMS],
            }
        }
        dm_exists: bool = mongo_abbot.find_one_dm(chat_id_filter)
        if dm_exists:
            dm_update = {
                "$set": {"id": chat_id, "username": username},
                "$push": {
                    "messages": new_message_dict,
                    "history": {"role": "user", "content": message_text},
                },
            }
        dm: TelegramDM = mongo_abbot.find_one_dm_and_update(chat_id_filter, dm_update)
        debug_bot.log(log_name, f"chat_id={chat_id}")
        dm_history: List = try_get(dm, "history")
        abbot = Abbot(chat_id, "dm", dm_history)
        answer, _, _, _ = abbot.chat_completion(chat_title)
        dm_history = abbot.get_history()
        dm: TelegramDM = mongo_abbot.find_one_dm_and_update(
            chat_id_filter,
            {"$set": {"tokens": abbot.history_tokens}, "$push": {"history": {"role": "assistant", "content": answer}}},
        )
        if "`" in answer or "**" in answer:
            return await message.reply_markdown_v2(sanitize_md_v2(answer), disable_web_page_preview=True)
        return await message.reply_text(answer, disable_web_page_preview=True)
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def handle_group_kicks_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: handle_group_kicks_bot"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        debug_bot.log(log_name, f"message={message}")
        chat: Chat = try_get(update_data, "chat")
        debug_bot.log(log_name, f"chat={chat}")
        left_chat_member: Dict = try_get(message, "left_chat_member", "from_user")
        is_bot: bool = try_get(left_chat_member, "is_bot")
        username: bool = try_get(left_chat_member, "is_bot")
        if is_bot and username == BOT_TELEGRAM_HANDLE:
            abbot_squawk = f"Bot kicked from group:\n\ntitle={chat.title}\nid={chat.id}"
            return await bot_squawk(log_name, abbot_squawk, context)
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def handle_group_default(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: handle_group_default"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        debug_bot.log(log_name, f"message={message}")
        message_text, _ = parse_message_data(message)

        chat: Chat = try_get(update_data, "chat")
        debug_bot.log(log_name, f"chat={chat}")
        chat_id, chat_title, chat_type = parse_group_chat_data(chat)
        chat_title: str = chat_title

        user: User = try_get(update_data, "user")
        debug_bot.log(log_name, f"user={user}")
        user_id, username, first_name = parse_user_data(user)
        new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}

        if not username:
            username: str = first_name or user_id or "someone"
            new_history_dict = {"role": "user", "content": f"{username} said: {message_text}"}
        debug_bot.log(log_name, f"username={username}")

        if not message_text:
            message_text_err = f"{log_name}: No message text: message={message} update={update}"
            await bot_squawk(log_name, message_text_err, context)
            new_history_dict = None

        chat_id_filter = {"id": chat_id}
        new_message_dict = message.to_dict()
        group: TelegramGroup = mongo_abbot.find_one_group(chat_id_filter)
        group_detail_msg: str = f"chat_id={chat_id}\nchat_title={chat_title}"
        if not group:
            group_update = {
                "$set": {
                    "created_at": datetime.now().isoformat(),
                    "title": chat_title,
                    "id": chat_id,
                    "type": chat_type,
                    "balance": 5000,
                    "messages": [new_message_dict],
                    "history": [BOT_SYSTEM_OBJECT_GROUPS],
                    "config": BOT_GROUP_CONFIG_DEFAULT,
                }
            }
            squawk_msg = f"New group created:\n\n{group_detail_msg}"
        else:
            if new_history_dict:
                group_update = {
                    "$set": {"title": chat_title, "id": chat_id, "type": chat_type},
                    "$push": {
                        "messages": new_message_dict,
                        "history": new_history_dict,
                    },
                }
            else:
                group_update = {
                    "$set": {"title": chat_title, "id": chat_id, "type": chat_type},
                    "$push": {"messages": new_message_dict},
                }
                squawk_msg = f"Existing group updated:\n\n{group_detail_msg}"
        await bot_squawk(log_name, squawk_msg, context)
        group: TelegramGroup = mongo_abbot.find_one_group_and_update(chat_id_filter, group_update)
        group_balance: int = try_get(group, "balance")
        group_history: List = try_get(group, "history")
        group_config: Dict = try_get(group, "config")
        unleashed: Dict = try_get(group_config, "unleashed")
        count: Dict = try_get(group_config, "count")
        if unleashed and count > 0:
            abbot = Abbot(chat_id, chat_type, group_history)
            debug_bot.log(log_name, f"abbot.history_len={abbot.history_len}")
            debug_bot.log(log_name, f"count={count}")
            if abbot.history_len % count == 0:
                if group_balance == 0:
                    # DM an admin?
                    # send message, and set unleashed = False and count = 0? or set started = False?
                    # fund_msg = "No SATs available! Please run /fund to topup (e.g. /fund 5 usd or /fund 5000 sats)."
                    debug_bot.log(log_name, f"group_balance={group_balance}")
                    return await bot_squawk(log_name, f"No SATS! {chat_title} {chat_id} {chat_type}", context)
                debug_bot.log(log_name, f"group_balance={group_balance}")
                chat_title_completion: str = chat_title.lower()
                answer, input_tokens, output_tokens, total_tokens = abbot.chat_completion(chat_title_completion)
                group: TelegramGroup = mongo_abbot.find_one_group_and_update(
                    chat_id_filter,
                    {
                        "$inc": {"tokens": total_tokens},
                        "$push": {"history": {"role": "assistant", "content": answer}},
                    },
                )
                response: Dict = await calculate_completion_cost(input_tokens, output_tokens)
                if not successful(response):
                    sub_log_name = f"{log_name}: calculate_completion_cost"
                    error_bot.log(log_name, f"response={response}")
                    abbot_squawk = f"{sub_log_name}: Failed to calculate remaining sats"
                    abbot_squawk = f"{abbot_squawk}: group_balance={group_balance}\nresponse={response}\nchat=(id={chat_id}\ntitle=({chat_title})"
                    error_bot.log(log_name, abbot_squawk)
                    await bot_squawk(log_name, abbot_squawk, context)
                cost_sats: int = try_get(response, "cost_sats", default=100)
                group_balance -= cost_sats
                balance_is_below_zero = group_balance < 0
                if balance_is_below_zero:
                    group_balance = 0
                    abbot_squawk = f"Group balance: {group_balance}\n\ngroup_id={chat_id}\ngroup_title={chat_title}"
                    answer = f"{answer}\n\n{WARN_GROUP_NOSATS}"
                    debug_bot.log(log_name, abbot_squawk)
                    await bot_squawk(log_name, abbot_squawk, context)
                debug_bot.log(log_name, f"group_balance={group_balance}")
                group: TelegramGroup = mongo_abbot.find_one_group_and_update(
                    chat_id_filter,
                    {"$dec": {"balance": group_balance}},
                )
                if "`" in answer or "**" in answer:
                    return await message.reply_markdown_v2(sanitize_md_v2(answer), disable_web_page_preview=True)
                return await message.reply_text(answer, disable_web_page_preview=True)
    except AbbotException as abbot_exception:
        await bot_squawk_error(log_name, abbot_exception, context)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    log_name: str = f"{FILE_NAME}: error_handler"
    exception = context.error
    formatted_traceback = "".join(traceback.format_exception(None, exception, exception.__traceback__))
    update_dict = update.to_dict()
    error_msg = "Exception while handling Telegram update"
    error_msg_update = f"{error_msg}\n\tupdate={json.dumps(update_dict, indent=4)}\n\tontext={context}"
    error_msg_except = f"{error_msg_update}\n\n\tException: {exception}"
    error_msg_tb = f"\n\n\tTraceback: {formatted_traceback}"
    squawk_msg = f"{log_name}: {error_msg_except}"
    log_msg = f"{log_name}: {error_msg_except} {error_msg_tb}"
    error_bot.log(log_name, log_msg)
    await bot_squawk(log_name, squawk_msg, context)


class TelegramBotBuilder:
    from lib.abbot.config import BOT_TELEGRAM_TOKEN

    def __init__(self):
        log_name: str = f"{FILE_NAME}: TelegramBotBuilder.__init__()"
        debug_bot.log(log_name, f"Telegram abbot initializing: name={BOT_NAME} handle={BOT_TELEGRAM_HANDLE}")
        telegram_bot = ApplicationBuilder().token(self.BOT_TELEGRAM_TOKEN).build()
        debug_bot.log(log_name, f"Telegram abbot initialized")

        # Add command handlers
        telegram_bot.add_handlers(
            handlers=[
                MessageHandler(CHAT_TYPE_GROUPS & (NEW_CHAT_MEMBERS | CHAT_CREATED), handle_group_adds_abbot),
                MessageHandler(CHAT_TYPE_GROUPS & LEFT_CHAT_MEMEBERS, handle_group_kicks_bot),
                MessageHandler(UpdateFilter(CHAT_TYPE_GROUPS & MESSAGE_EDITED), handle_group_message_edit),
                MessageHandler(REGEX_MARKDOWN_REPLY, handle_markdown_request),
            ]
        )

        telegram_bot.add_handlers(
            handlers=[
                CommandHandler("help", help),
                CommandHandler("rules", rules),
                CommandHandler("start", start),
                CommandHandler("stop", stop),
                CommandHandler("unleash", unleash),
                CommandHandler("leash", leash),
                CommandHandler("balance", balance),
                CommandHandler("fund", fund),
                CommandHandler("count", count),
                CommandHandler("status", status),
                CallbackQueryHandler(fund_button),
            ]
        )

        telegram_bot.add_handlers(
            handlers=[
                MessageHandler(CHAT_TYPE_PRIVATE, handle_dm),
                MessageHandler(CHAT_TYPE_GROUPS & FILTER_MENTION_ABBOT, handle_group_mention),
                MessageHandler(CHAT_TYPE_GROUPS & FilterAbbotReply(), handle_group_reply),
                # MessageHandler(CHAT_TYPE_GROUPS & MEDIA, handle_group_media),
                # TODO: https://github.com/python-telegram-bot/python-telegram-bot/wiki/Extensions---Advanced-Filters
                MessageHandler(CHAT_TYPE_GROUPS, handle_group_default),
            ]
        )
        telegram_bot.add_error_handler(error_handler)
        self.telegram_bot = telegram_bot

    def run(self):
        log_name: str = f"{FILE_NAME}: TelegramBotBuilder.run"
        debug_bot.log(log_name, f"Telegram abbot polling")
        self.telegram_bot.run_polling()
