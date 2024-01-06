# core
import json
import time
import uuid
import traceback

from datetime import datetime
from typing import Any, Dict, List, Optional

# packages
from telegram import Bot, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update, Message, Chat, User
from telegram.constants import MessageEntityType, ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.ext.filters import ChatType, StatusUpdate, Regex, Entity, Mention, UpdateFilter, UpdateType, REPLY, TEXT

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
    ABBOT_SQUAWKS,
    ESCAPE_MARKDOWN_V2_CHARS,
    HELP_MENU,
    INTRODUCTION,
    MATRIX_IMG_FILEPATH,
    OPENAI_MODEL,
    RULES,
    SATOSHIS_PER_BTC,
    THE_ARCHITECT_ID,
    THE_ARCHITECT_HANDLE,
    THE_ARCHITECT_USERNAME,
)
from ..abbot.config import (
    BOT_GROUP_CONFIG_DEFAULT,
    BOT_GROUP_CONFIG_STARTED,
    BOT_GROUP_CONFIG_STARTED_UNLEASHED,
    BOT_GROUP_CONFIG_STOPPED,
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
REGEX_MARKDOWN_REPLY = Regex("markdown")
MESSAGE_OR_EDITED = UpdateType.MESSAGES

# local
from ..logger import debug_bot, error_bot
from ..utils import error, qr_code, success, try_get, successful
from ..db.mongo import TelegramDM, TelegramGroup, mongo_abbot
from ..abbot.core import Abbot
from ..abbot.utils import (
    bot_squawk,
    calculate_tokens,
    parse_group_chat_data,
    parse_dm_chat_data,
    parse_message_data,
    parse_message_data_keys,
    parse_user_data,
    parse_update_data,
)
from ..payments import Coinbase, CoinbasePrice, init_payment_processor, init_price_provider
from ..abbot.exceptions.exception import AbbotException
from ..abbot.telegram.filter_abbot_reply import FilterAbbotReply

payment_processor = init_payment_processor()
price_provider: Coinbase = init_price_provider()

import tiktoken

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)
FILE_NAME = __name__
no_group_error = "No group or group config"
no_group_config_error = "No group config"
no_group_or_config_err = f"{no_group_error} or {no_group_config_error}"

sats_example = "For sats: /fund 5000 sats"
usd_example = "For usd: /fund 10 usd"
invoice_error_args = "Missing amount and currency unit. Did you pass an amount and a currency unit?"
invoice_error_unit = "Unrecognized currency unit. Did you pass one of usd or sats?"
create_fail_msg = f"Failed to create invoice. Please try again"
create_fail_lnaddr = f"or pay to {BOT_LIGHTNING_ADDRESS} and contact @{BOT_TELEGRAM_SUPPORT_CONTACT}"
create_fail = f"{create_fail_msg} {create_fail_lnaddr}"
cancel_fail_msg = "Failed to cancel invoice"
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
    amount = int((usd_amount / int(btc_price_usd)) * SATOSHIS_PER_BTC)
    if amount <= 0:
        amount = 2500
    return amount


async def sat_to_usd(sats_amount: int) -> int:
    price_dict: Dict[CoinbasePrice] = mongo_abbot.find_prices()[-1]
    btc_price_usd: int = try_get(price_dict, "amount")
    if btc_price_usd:
        if type(btc_price_usd) != int:
            btc_price_usd: int = int(btc_price_usd)
    else:
        btc_price_usd: int = await get_live_price()
    amount = round(float((sats_amount / SATOSHIS_PER_BTC) * int(btc_price_usd)), 2)
    if amount <= 0:
        amount = 1
    return amount


async def recalc_balance_sats(in_token_count: int, out_token_count: int, current_balance: int, bot: Bot):
    try:
        log_name: str = f"{FILE_NAME}: recalc_balance_sats"
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

        cost_input_tokens = (in_token_count / ORG_PER_TOKEN_COST_DIV) * (ORG_INPUT_TOKEN_COST * ORG_TOKEN_COST_MULT)
        cost_output_tokens = (out_token_count / ORG_PER_TOKEN_COST_DIV) * (ORG_OUTPUT_TOKEN_COST * ORG_TOKEN_COST_MULT)
        total_token_cost_usd = cost_input_tokens + cost_output_tokens
        total_token_cost_sats = (total_token_cost_usd / btcusd_price) * SATOSHIS_PER_BTC
        if total_token_cost_sats > current_balance or current_balance == 0:
            return 0
        remaining_balance_sats = current_balance - total_token_cost_sats
        return success(data=int(remaining_balance_sats), cost_sats=int(total_token_cost_sats))
    except AbbotException as abbot_exception:
        raise abbot_exception


# def escape_markdown_v2(text):
#     return "".join("\\" + char if char in ESCAPE_MARKDOWN_V2_CHARS else char for char in text)


def sanitize_md_v2(text):
    # Characters to be escaped in Telegram Markdown V2
    escape_chars = "_[]()~>#+-=|{}.!^@$%&;:?/<,"

    # Remove surrogates and escape Markdown V2 characters
    return "".join(
        "\\" + char if char in escape_chars else char for char in text if not (0xD800 <= ord(char) <= 0xDFFF)
    )


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
        # message_text, message_date = parse_message_data(message)

        message_data: Dict = parse_message_data_keys(message, keys=["group_chat_created", "new_chat_members"])
        group_chat_created = message_data.get("group_chat_created", None)
        new_chat_members = message_data.get("new_chat_members", None)

        chat: Chat = try_get(update_data, "chat")
        chat_id, chat_title, chat_type = parse_group_chat_data(chat)

        group_admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]
        debug_bot.log(log_name, f"group_admins={group_admins}")

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
                "admins": group_admins,
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
            group_update = {"$set": {"title": chat_title, "id": chat_id, "type": chat_type, "admins": group_admins}}
        group: TelegramGroup = mongo_abbot.find_one_group_and_update(chat_id_filter, group_update)
        debug_bot.log(log_name, f"group={group}")
        await context.bot.send_message(
            chat_id=ABBOT_SQUAWKS, text=f"{log_name}: Abbot added to new group: title={chat_title}, id={chat_id})"
        )
    except AbbotException as abbot_exception:
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


async def handle_group_message_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO: handle message edited
    pass


async def reply_markdown(update, context):
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
        await message.reply_markdown_v2("sanitized_text")
    except AbbotException as abbot_exception:
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


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
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: help"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        await message.reply_markdown_v2(HELP_MENU, disable_web_page_preview=True)
    except AbbotException as abbot_exception:
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


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
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: start"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        message_text, _ = parse_message_data(message)
        chat: Chat = try_get(update_data, "chat")
        chat_id, chat_title, chat_type = parse_group_chat_data(chat)
        if chat_type == "private":
            return await message.reply_text("/start is disabled in DMs. Feel free to chat at will!")
        user: User = try_get(update_data, "user")
        _, username, _ = parse_user_data(user)

        if chat_type in ("group", "supergroup", "channel"):
            admins: Any = [admin.to_dict() for admin in await chat.get_administrators()] or []
            debug_bot.log(log_name, f"admins={admins}")

        chat_id_filter = {"id": chat_id}
        new_message_dict = message.to_dict()
        intro_history_dict = {"role": "assistant", "content": INTRODUCTION}
        new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}
        group_exists: bool = mongo_abbot.group_does_exist(chat_id_filter)
        debug_bot.log(log_name, f"group_exists={group_exists}")
        if not group_exists:
            group_update = {
                "$set": {
                    "created_at": datetime.now().isoformat(),
                    "title": chat_title,
                    "id": chat_id,
                    "type": chat_type,
                    "admins": admins,
                    "balance": 5000,
                    "messages": [new_message_dict],
                    "history": [BOT_SYSTEM_OBJECT_GROUPS, intro_history_dict, new_history_dict],
                    "config": BOT_GROUP_CONFIG_STARTED_UNLEASHED,
                }
            }
            group: TelegramGroup = mongo_abbot.find_one_group_and_update(chat_id_filter, group_update)
            debug_bot.log(log_name, f"group={group}")
        else:
            group_update = {
                "$set": {
                    "title": chat_title,
                    "id": chat_id,
                    "type": chat_type,
                    "admins": admins,
                    "config": BOT_GROUP_CONFIG_STARTED_UNLEASHED,
                },
                "$push": {
                    "messages": new_message_dict,
                    "history": new_history_dict,
                },
            }

        group_config: Dict = mongo_abbot.get_group_config(chat_id_filter)
        debug_bot.log(log_name, f"group_config={group_config}")
        started: Dict = try_get(group_config, "started")
        if started:
            already_started = f"Hey\! I'm already started and ready to rock and roll 🪨🤘🎸"
            already_started = f"{already_started}\n\nFeel free to run /rules or /help for more information"
            debug_bot.log(log_name, f"already_started={already_started}")
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {already_started}")
            return await message.reply_markdown_v2(already_started, disable_web_page_preview=True)
        debug_bot.log(log_name, f"started={started}")

        current_sats: TelegramGroup = mongo_abbot.get_group_balance(chat_id_filter)
        if current_sats == 0:
            group_msg = f"⚡️ Group: {chat_title} ⚡️ "
            sats_balance_msg = f"⚡️ SATs Balance: {current_sats} ⚡️"
            usd_balance = await sat_to_usd(current_sats)
            usd_balance_msg = f"💰 USD Balance: {usd_balance} 💰"
            fund_msg = "No SATs available! Please run /fund to topup (e.g. /fund 5 usd or /fund 5000 sats)."
            await message.reply_text(f"{group_msg} \n {sats_balance_msg} \n {usd_balance_msg} \n {fund_msg}")
        debug_bot.log(log_name, f"current_sats={current_sats}")

        introduced: Dict = try_get(group_config, "introduced")
        debug_bot.log(log_name, f"introduced={introduced}")
        if introduced:
            group_history: List[Dict] = try_get(group, "group_history")
            abbot = Abbot(chat_id, "group", group_history)
            answer, input_tokens, output_tokens, _ = abbot.chat_completion()

            response: Dict = await recalc_balance_sats(input_tokens, output_tokens, current_sats, context.bot)
            sats_remaining: int = try_get(response, "data")
            if not successful(response):
                sub_log_name = f"{log_name}: recalc_balance_sats"
                error_bot.log(log_name, f"response={response}")
                msg = f"{sub_log_name}: Failed to calculate remaining sats"
                error_bot.log(log_name, msg)
                error_bot.log(log_name, f"current_sats={current_sats}\nresponse={response}")
                error_bot.log(log_name, f"chat_id={chat_id}\nchat_title={chat_title}")
                await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=msg)

            if not sats_remaining and current_sats > 0:
                sats_remaining = current_sats - 250
            else:
                sats_remaining = 0
                abbot_squawk = f"Group balance: {current_sats}\n\ngroup_id={chat_id}\ngroup_title={chat_title}"
                answer = f"{answer}\n\n Note: You group is now out of SATs. Please run /fund to topup."
                debug_bot.log(log_name, abbot_squawk)
                await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
            debug_bot.log(log_name, f"sats_remaining={sats_remaining}")

            assistant_history_update = {"role": "assistant", "content": answer}
            group_history = abbot.get_history()
            token_count: int = calculate_tokens(group_history)
            group: TelegramGroup = mongo_abbot.find_one_group_and_update(
                chat_id_filter,
                {
                    "$set": {"balance": sats_remaining, "tokens": token_count},
                    "$push": {"history": assistant_history_update},
                },
            )
            debug_bot.log(log_name, f"group={group}")
            await message.reply_text(answer)

        await message.reply_photo(MATRIX_IMG_FILEPATH, f"Please wait while {BOT_NAME} is unplugged from the Matrix")
        time.sleep(3)
        await message.reply_markdown_v2(INTRODUCTION, disable_web_page_preview=True)
    except AbbotException as abbot_exception:
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


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
        debug_bot.log(log_name, f"message={message}")

        chat: Chat = try_get(update_data, "chat")
        chat_id, chat_title, chat_type = parse_group_chat_data(chat)
        debug_bot.log(log_name, f"chat={chat}")

        if chat_type in ("group", "supergroup", "channel"):
            admins: Any = [admin.to_dict() for admin in await chat.get_administrators()] or []
            debug_bot.log(log_name, f"admins={admins}")
        else:
            return await message.reply_text("/stop is disabled in DMs. Feel free to chat at will!")

        user: User = try_get(update_data, "user")
        user_id, username, first_name = parse_user_data(user)
        debug_bot.log(log_name, f"user={user}")

        chat_id_filter = {"id": chat_id}
        new_message_dict = message.to_dict()
        new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}
        group_exists: bool = mongo_abbot.group_does_exist(chat_id_filter)
        if not group_exists:
            group_dne_err = f"Group chat not onboarded"
            reply_msg = f"Did you run /start?"
            await message.reply_text(reply_msg)
            abbot_squawk = f"{group_dne_err}\n\nchat_id={chat_id}, chat_title={chat_title}"
            return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=group_dne_err)
        debug_bot.log(log_name, f"group_exists={group_exists}")

        group: TelegramGroup = mongo_abbot.find_one_group_and_update(
            chat_id_filter,
            {
                "$set": {
                    "title": chat_title,
                    "id": chat_id,
                    "admins": admins,
                    "config.started": False,
                },
                "$push": {
                    "messages": new_message_dict,
                    "history": new_history_dict,
                },
            },
        )
        debug_bot.log(log_name, f"group={group}")

        still_running: bool = try_get(group, "config", "started")
        if still_running:
            reply_text_err = f"Failed to stop {BOT_NAME}. Please try again or contact {THE_ARCHITECT_HANDLE} for help"
            abbot_squawk = f"{log_name}: {reply_text_err} => chat_id={chat_id}, chat_title={chat_title}"
            error_bot.log(log_name, abbot_squawk)
            await message.reply_text(reply_text_err)
            return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)

        await message.reply_text(f"Thanks for using {BOT_NAME}! Come back soon!")
        abbot_squawk = f"{BOT_NAME} stopped\n\nchat_id={chat_id}, chat_title={chat_title}"
        await bot_squawk(abbot_squawk, context)
    except AbbotException as abbot_exception:
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


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
        group_msg = f" 💬 *Group*\: {chat_title} 💬"
        sats_balance_msg = f"⚡️ *SAT Balance*\: {group_balance} SAT ⚡️"
        usd_balance_msg = f"💰 *USD Balance*\: {usd_balance} USD 💰"
        balance_msg = f"{group_msg}\n{sats_balance_msg}\n{usd_balance_msg}".replace(".", "\.")
        return await message.reply_markdown_v2(balance_msg)
    except AbbotException as abbot_exception:
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


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
        debug_bot.log(log_name, f"message_text={message_text} message_date={message_date}")
        message_text: str = message_text.split()

        chat: Chat = try_get(update_data, "chat")
        chat_id, _, chat_type = parse_group_chat_data(chat)
        if chat_type == "private":
            return await message.reply_text("/unleash is disabled in DMs. Feel free to chat at will!")

        arg_count: str = try_get(message_text, 1)
        if not arg_count:
            arg_count: int = 5
        if arg_count == 0:
            return await message.reply_text(
                "/unleash requires count > 0, use /leash to set to 0 & turn off unleash mode"
            )

        chat_id_filter = {"id": chat_id}
        group: TelegramGroup = mongo_abbot.find_one_group(chat_id_filter)
        if not group:
            return await message.reply_text(f"{no_group_error} - Did you run /start{BOT_TELEGRAM_HANDLE}?")
        current_sats: int = try_get(group, "balance")
        if current_sats == 0:
            return await message.reply_text(f"You group SAT balance is 0. Please run /fund to topup.")
        group_config: Dict = mongo_abbot.get_group_config(chat_id_filter)
        unleashed: bool = try_get(group_config, "unleashed")
        count: bool = try_get(group_config, "count")
        if unleashed and count != arg_count:
            group: TelegramGroup = mongo_abbot.find_one_group_and_update(
                chat_id_filter, {"$set": {"config.count": arg_count}}
            )

        await message.reply_text(f"Abbot has been unleashed to respond every {arg_count}")
    except AbbotException as abbot_exception:
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


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
            return await message.reply_text(f"{no_group_error} - Did you run /start{BOT_TELEGRAM_HANDLE}?")
    except AbbotException as abbot_exception:
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


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
            abbot_squawk = f"{log_name}: {no_group_config_error}:"
            error_msg = f"id={chat_id}, title={chat_title}, group_config={group_config}"
            abbot_squawk = f"{abbot_squawk}\n\n{error_msg}"
            reply_text_err = f"Failed to get group status. Please contact {THE_ARCHITECT_HANDLE} for assistance."
            error_bot.log(log_name, abbot_squawk)
            await bot_squawk(abbot_squawk, context)
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
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


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
        chat_type: str = chat_type.capitalize()
        if chat_type == "Private":
            return await message.reply_text("/fund is disabled in DMs. Feel free to chat at will!")

        user: User = try_get(update_data, "user")
        debug_bot.log(log_name, f"user={user}")
        user_id, username, first_name = parse_user_data(user)
        username: str = username or first_name or chat_id or user_id

        topup_for: str = chat_title
        topup_by: str = username

        args = message_text.split()
        args_len = len(args)
        debug_bot.log(log_name, f"args={args}")

        if args_len < 2:
            return await message.reply_text(f"{invoice_error_args}\n{sats_example}\n{usd_example}")
        elif args_len < 3:
            return await message.reply_text(f"{invoice_error_args}\n{sats_example}\n{usd_example}")

        amount: int | float = try_get(args, 1)
        if "." in amount:
            amount: float = float(try_get(args, 1))
        else:
            amount: int = int(try_get(args, 1))

        if amount < 0.01:
            return await message.reply_text("Amount too low. Must be at least 0.01")
        debug_bot.log(log_name, f"amount={amount}")

        currency_unit: str = try_get(args, 2, default="sats")
        currency_unit = currency_unit.lower()
        debug_bot.log(log_name, f"currency_unit={currency_unit}")

        if currency_unit == "sats":
            currency_unit = "SATS"
            emoji = "⚡️"
            symbol = "⚡️"
            invoice_amount = await sat_to_usd(amount)
            balance = amount
        elif currency_unit == "usd":
            currency_unit = "USD"
            emoji = "💰"
            symbol = "$"
            invoice_amount = amount
            balance = await usd_to_sat(amount)
        else:
            return await message.reply_text(f"{invoice_error_unit}\n\n{sats_example}\n\n{usd_example}")

        await message.reply_text("Creating your invoice, please wait ...")
        debug_bot.log(log_name, f"payment_processor={payment_processor}")
        debug_bot.log(log_name, f"amount={amount}")
        debug_bot.log(log_name, f"invoice_amount={invoice_amount}")

        group_msg = f"💬 *Group*: {topup_for}\n\n"
        sender_msg = f"✉️ *Requested by*: @{topup_by}\n\n"
        amount_msg = f"{emoji} *Amount*: {symbol}{amount} {currency_unit}\n\n"
        cid = str(uuid.uuid1())
        invoiceid_msg = f"🧾 *Invoice ID*:\n{cid}"
        description = f"{group_msg}{sender_msg}{amount_msg}{invoiceid_msg}"
        debug_bot.log(log_name, f"description={description}")

        response = await payment_processor.get_invoice(cid, description, invoice_amount, chat_id)
        debug_bot.log(log_name, f"response={response}")

        create_squawk = f"Failed to create strike invoice: {json.dumps(response)}"
        if not successful(response):
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{create_squawk}: not successful()")
            return await message.reply_text(create_fail)

        invoice_id = try_get(response, "invoice_id")
        invoice = try_get(response, "ln_invoice")
        expiration_in_sec = try_get(response, "expiration_in_sec")
        payment_processor.CHAT_ID_INVOICE_ID_MAP[chat_id] = invoice_id
        if None in (invoice_id, invoice, expiration_in_sec):
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=create_squawk)
            return await message.reply_text(create_fail)
        expires_msg = f"🕰️ Expires in: {expiration_in_sec} seconds\n"
        description = f"{description}\n{expires_msg}"
        await message.reply_photo(photo=qr_code(invoice), caption=sanitize_md_v2(description), parse_mode=MARKDOWN_V2)
        await message.reply_markdown_v2(f"`{invoice}`")

        cancel_squawk = f"{cancel_fail_msg}: description={description}, invoice_id={invoice_id}"
        is_paid = False
        while expiration_in_sec >= 0 and not is_paid:
            debug_bot.log(log_name, f"expiration_in_sec={expiration_in_sec}")
            if expiration_in_sec == 0:
                debug_bot.log(log_name, f"expiration_in_sec == 0, cancelling invoice_id={invoice_id}")
                cancelled = await payment_processor.expire_invoice(invoice_id)
                debug_bot.log(log_name, f"cancelled={cancelled}")
                if not cancelled:
                    cancel_reply = (
                        f"{cancel_fail_msg}: Try again or pay to abbot@atlbitlab.com and contact {THE_ARCHITECT_HANDLE}"
                    )
                    await context.bot.send_message(chat_id=THE_ARCHITECT_ID, text=cancel_squawk)
                    return await message.reply_text(cancel_reply)
            is_paid = await payment_processor.invoice_is_paid(invoice_id)
            debug_bot.log(log_name, f"is_paid={is_paid}")
            expiration_in_sec -= 1
            if expiration_in_sec % 10 == 0:
                await message.reply_text(f"🕰️ Invoice expires in: {expiration_in_sec} seconds\n")
            time.sleep(1)

        if is_paid:
            group: TelegramGroup = mongo_abbot.find_one_group_and_update(
                {"id": chat.id}, {"$inc": {"balance": balance}}
            )
            if not group:
                error_bot.log(log_name, f"not group")
                return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=group)
            balance: int = try_get(group, "balance", default=amount)
            await message.reply_text(f"Invoice Paid! ⚡️ {chat_title} balance: {balance} sats ⚡️")
        else:
            keyboard = [[InlineKeyboardButton("Yes", callback_data="1"), InlineKeyboardButton("No", callback_data="2")]]
            await context.bot.send_message(chat_id=THE_ARCHITECT_ID, text=cancel_squawk)
            keyboard_markup = InlineKeyboardMarkup(keyboard)
            await message.reply_text(f"Invoice expired! Try again?", reply_markup=keyboard_markup)
    except AbbotException as abbot_exception:
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


async def fund_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: fund_button"

        query: Optional[CallbackQuery] = try_get(update, "callback_query")
        update_id: int = try_get(update, "update_id")
        await query.answer()
        if query.data == "1":
            message: Message = try_get(query, "message", "reply_to_message")
            update: Update = Update(update_id=update_id, message=message)
            await fund(update, context)
        elif query.data == "2":
            np = "No problem"
            ln_addr = "You can also pay my LN address abbot@atlbitlab.com"
            contact = "If you do, be sure to contact @nonni_io to ensure you get credit"
            reply_msg = f"{np} 👍 {ln_addr} ⚡️ {contact}"
            await query.edit_message_text(reply_msg)
    except AbbotException as abbot_exception:
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


"""
async def fund_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: fund_cancel"

        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")

        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")

        message: Message = try_get(update_data, "message")
        message_text: str = message.text
        debug_bot.log(log_name, f"message_text={message_text}")
        args = message_text.split()
        debug_bot.log(log_name, f"args={args}")

        chat: Chat = try_get(update_data, "chat")
        chat_id, chat_title, chat_type = parse_group_chat_data(chat)
        if chat_type == "private":
            return await message.reply_text("/cancel is disabled in DMs. Feel free to chat at will!")

        invoice_id = try_get(args, 1) or payment_processor.CHAT_ID_INVOICE_ID_MAP.get(chat_id, None)
        if not invoice_id:
            return await message.reply_text("Invoice not found")
        debug_bot.log(log_name, f"invoice_id={invoice_id}")

        await message.reply_text("Attempting to cancel your invoice, please wait ...")
        debug_bot.log(log_name, f"payment_processor={payment_processor.to_dict()}")

        cancel_squawk = f"Failed to cancel invoice: chat_id={chat_id}, chat_title={chat_title}, invoice_id={invoice_id}"
        cancel_fail = f"Failed to cancel invoice. Try again or pay abbot@atlbitlab.com & contact {THE_ARCHITECT_HANDLE} for confirmation"
        cancelled = await payment_processor.expire_invoice(invoice_id)
        if not cancelled:
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=cancel_squawk)
            return await message.reply_text(cancel_fail)

        await message.reply_text(f"Invoice id {invoice_id} successfully cancelled for {chat_title}")
    except AbbotException as abbot_exception:
        await bot_squawk(f"{log_name}: {abbot_exception}", context)
"""


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

        if chat_type in ("group", "supergroup", "channel"):
            admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]
            debug_bot.log(log_name, f"admins={admins}")

        chat_id_filter = {"id": chat_id}
        stopped_err = f"{BOT_NAME} not started - Please run /start{BOT_TELEGRAM_HANDLE}"

        group: TelegramGroup = mongo_abbot.find_one_group(chat_id_filter)
        group_config: Dict = try_get(group, "config")
        if not group or not group_config:
            abbot_squawk = f"{log_name}: {no_group_error}: id={chat_id}, title={chat_title}"
            error_msg = f"{no_group_error}: group={group} group_config={group_config}"
            abbot_squawk = f"{abbot_squawk}\n\n{error_msg}"

            error_bot.log(log_name, abbot_squawk)
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
            return await message.reply_text(stopped_err)
        debug_bot.log(log_name, f"group={group}")
        debug_bot.log(log_name, f"group_config={group_config}")

        started: bool = try_get(group_config, "started")
        debug_bot.log(log_name, f"started={started}")
        if not started:
            abbot_squawk = f"{log_name}: {stopped_err}: id={chat_id}, title={chat_title}"
            error_bot.log(log_name, abbot_squawk)
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
            return await message.reply_text(stopped_err)

        new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}
        if not message_text:
            message_text_err = f"{log_name}: No message text: message={message} update={update}"
            return await context.bot.send_message(chat_id=THE_ARCHITECT_ID, text=message_text_err)

        if not username and not message_date:
            new_history_dict = {"role": "user", "content": f"someone said: {message_text}"}
        elif username and message_date:
            new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}
        elif not username and message_date:
            new_history_dict = {"role": "user", "content": f"someone said: {message_text}"}
        elif username and not message_date:
            new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}

        new_message_dict = message.to_dict()
        group: TelegramGroup = mongo_abbot.find_one_group_and_update(
            chat_id_filter,
            {
                "$set": {
                    "title": chat_title,
                    "id": chat_id,
                    "type": chat_type,
                    "admins": admins,
                },
                "$push": {
                    "messages": new_message_dict,
                    "history": new_history_dict,
                },
            },
        )
        group_history: List[Dict] = try_get(group, "history")
        if not group or not group_history:
            abbot_squawk = f"{log_name}: {no_group_error}: id={chat_id}, title={chat_title}"
            error_msg = f"{no_group_error}: group={group} group_config={group_config}"
            abbot_squawk = f"{abbot_squawk}\n\n{error_msg}"

            error_bot.log(log_name, abbot_squawk)
            await message.reply_text(stopped_err)
            return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
        debug_bot.log(log_name, f"group={group}")
        debug_bot.log(log_name, f"group_config={group_config}")

        current_sats: TelegramGroup = mongo_abbot.get_group_balance(chat_id_filter)
        if current_sats == 0:
            group_no_sats_msg = f"Your group is out of SATs. To continue using {BOT_NAME}, topup using /fund"
            abbot_squawk = f"Group balance: {current_sats}\n\ngroup_id={chat_id}\ngroup_title={chat_title}"
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
            return await message.reply_text(group_no_sats_msg)

        abbot = Abbot(chat_id, "group", group_history)
        answer, input_tokens, output_tokens, _ = abbot.chat_completion()

        response: Dict = await recalc_balance_sats(input_tokens, output_tokens, current_sats, context.bot)
        sats_remaining: int = try_get(response, "data")
        if not successful(response):
            sub_log_name = f"{log_name}: recalc_balance_sats"
            error_bot.log(log_name, f"response={response}")
            msg = f"{sub_log_name}: Failed to calculate remaining sats"
            msg = f"{msg}: current_sats={current_sats}\nresponse={response}\nchat=(id={chat_id}\ntitle=({chat_title})"
            error_bot.log(log_name, msg)
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=msg)

        if not sats_remaining:
            sats_remaining = current_sats - 250

        if sats_remaining == 0:
            abbot_squawk = f"Group balance: {current_sats}\n\ngroup_id={chat_id}\ngroup_title={chat_title}"
            answer = f"{answer}\n\n Note: You group is now out of SATs. Please run /fund to topup."
            debug_bot.log(log_name, abbot_squawk)
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)

        debug_bot.log(log_name, f"sats_remaining={sats_remaining}")

        assistant_history_update = {
            "role": "assistant",
            "content": answer,
        }
        group_history = abbot.get_history()
        token_count: int = calculate_tokens(group_history)
        group: TelegramGroup = mongo_abbot.find_one_group_and_update(
            chat_id_filter,
            {
                "$set": {"balance": sats_remaining, "tokens": token_count},
                "$push": {"history": assistant_history_update},
            },
        )

        debug_bot.log(log_name, f"group={group}")

        await message.reply_text(answer)
    except AbbotException as abbot_exception:
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


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
        debug_bot.log(log_name, f"chat={chat}")

        user: User = try_get(update_data, "user")
        debug_bot.log(log_name, f"user={user}")

        message_text, message_date = parse_message_data(message)
        debug_bot.log(log_name, f"message_text={message_text} message_date={message_date}")

        chat_id, chat_title, chat_type = parse_group_chat_data(chat)
        debug_bot.log(log_name, f"chat_id={chat_id} chat_title={chat_title} chat_type={chat_type}")

        if chat_type in ("group", "supergroup", "channel"):
            admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]
            debug_bot.log(log_name, f"admins={admins}")

        user_id, username, first_name = parse_user_data(user)
        if not username:
            username = try_get(user, "first_name")

        reply_to_message: Optional[Message] = try_get(message, "reply_to_message")
        debug_bot.log(log_name, f"reply_to_message={reply_to_message.__str__()}")
        # debug_bot.log(log_name, f"reply_to_message={json.dumps(reply_to_message.to_dict(), indent=2)}")
        reply_to_message_from_user: Optional[User] = try_get(reply_to_message, "from_user")
        replied_to_bot = try_get(reply_to_message_from_user, "is_bot")
        debug_bot.log(log_name, f"replied_to_bot={replied_to_bot}")

        replied_to_abbot = try_get(reply_to_message_from_user, "username") == BOT_TELEGRAM_USERNAME
        debug_bot.log(log_name, f"replied_to_abbot={replied_to_abbot}")

        if replied_to_bot and replied_to_abbot:
            chat_id_filter = {"id": chat_id}
            stopped_err = f"{BOT_NAME} not started - Please run /start{BOT_TELEGRAM_HANDLE}"

            group: TelegramGroup = mongo_abbot.find_one_group(chat_id_filter)
            group_config: Dict = try_get(group, "config")
            started: bool = try_get(group_config, "started")
            debug_bot.log(log_name, f"started={started}")
            if not group or not group_config:
                abbot_squawk = f"{log_name}: {no_group_error}: id={chat_id}, title={chat_title}"
                reply_msg = f"{no_group_error} - Did you run /start{BOT_TELEGRAM_HANDLE}?"
                abbot_squawk = f"{abbot_squawk}\n\n{reply_msg}"

                error_bot.log(log_name, abbot_squawk)
                await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
                return await message.reply_text(reply_msg)
            elif not started:
                abbot_squawk = f"{log_name}: {stopped_err}: id={chat_id}, title={chat_title}"
                error_bot.log(log_name, abbot_squawk)
                await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
                return await message.reply_text(stopped_err)

            debug_bot.log(log_name, f"group={group}")
            debug_bot.log(log_name, f"group_config={group_config}")

            new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}
            if not message_text:
                message_text_err = f"{log_name}: No message text: message={message} update={update}"
                return await context.bot.send_message(chat_id=THE_ARCHITECT_ID, text=message_text_err)

            if not username and not message_date:
                new_history_dict = {"role": "user", "content": f"someone said: {message_text}"}
            elif username and message_date:
                new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}
            elif not username and message_date:
                new_history_dict = {"role": "user", "content": f"someone said: {message_text}"}
            elif username and not message_date:
                new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}

            new_message_dict = message.to_dict()
            group: TelegramGroup = mongo_abbot.find_one_group_and_update(
                chat_id_filter,
                {
                    "$set": {
                        "title": chat_title,
                        "id": chat_id,
                        "type": chat_type,
                        "admins": admins,
                    },
                    "$push": {
                        "messages": new_message_dict,
                        "history": new_history_dict,
                    },
                },
            )
            group_history: List[Dict] = try_get(group, "history")
            if not group or not group_history:
                abbot_squawk = f"{log_name}: {no_group_error}: id={chat_id}, title={chat_title}"
                error_msg = f"{no_group_error}: group={group} group_config={group_config}"
                abbot_squawk = f"{abbot_squawk}\n\n{error_msg}"

                error_bot.log(log_name, abbot_squawk)
                # await message.reply_text(stopped_err)
                return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
            debug_bot.log(log_name, f"new group={group}")
            debug_bot.log(log_name, f"new group_config={group_config}")

            current_sats: TelegramGroup = mongo_abbot.get_group_balance(chat_id_filter)
            if current_sats == 0:
                group_no_sats_msg = f"Your group is out of SATs. To continue using {BOT_NAME}, topup using /fund"
                abbot_squawk = f"Group balance: {current_sats}\n\ngroup_id={chat_id}\ngroup_title={chat_title}"
                await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
                return await message.reply_text(group_no_sats_msg)

            abbot = Abbot(chat_id, "group", group_history)
            answer, input_tokens, output_tokens, _ = abbot.chat_completion()

            response: Dict = await recalc_balance_sats(input_tokens, output_tokens, current_sats, context.bot)
            sats_remaining: int = try_get(response, "data")
            cost_sats: int = try_get(response, "cost_sats")
            debug_bot.log(log_name, f"sats_remaining={sats_remaining}")
            debug_bot.log(log_name, f"cost_sats={cost_sats}")
            if not successful(response):
                error_bot.log(log_name, f"response={response}")
                sub_log_name = f"{log_name}: recalc_balance_sats"
                calc_failed_msg = f"{sub_log_name}: Failed to calculate remaining sats"
                abbot_squawk = f"{calc_failed_msg}: group_id={chat_id}\ngroup_title=({chat_title})"
                abbot_squawk = f"{abbot_squawk}: current_sats={current_sats}\nresponse={response}\n"
                error_bot.log(log_name, abbot_squawk)
                await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
            debug_bot.log(log_name, f"response={response}")

            if not sats_remaining:
                sats_remaining = current_sats - cost_sats

            if sats_remaining == 0:
                abbot_squawk = f"Group balance: {current_sats}\n\ngroup_id={chat_id}\ngroup_title={chat_title}"
                answer = f"{answer}\n\n Note: You group is now out of SATs. Please run /fund to topup."
                debug_bot.log(log_name, abbot_squawk)
                await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
            debug_bot.log(log_name, f"sats_remaining={sats_remaining}")
            assistant_history_update = {
                "role": "assistant",
                "content": answer,
            }
            group_history = abbot.get_history()
            token_count: int = calculate_tokens(group_history)
            group: TelegramGroup = mongo_abbot.find_one_group_and_update(
                chat_id_filter,
                {
                    "$set": {"balance": sats_remaining, "tokens": token_count},
                    "$push": {"history": assistant_history_update},
                },
            )
            debug_bot.log(log_name, f"group={group}")
            await message.reply_text(answer)
    except AbbotException as abbot_exception:
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


async def handle_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: handle_group_adds_abbot"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")

        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")

        message: Message = try_get(update_data, "message")
        message_text, _ = parse_message_data(message)

        chat: Chat = try_get(update_data, "chat")
        chat_id, _, _ = parse_group_chat_data(chat)
        _, username, first_name = parse_dm_chat_data(chat)
        username: str = username or first_name or chat_id or None
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
        debug_bot.log(log_name, f"dm={dm}")

        dm_history: List = try_get(dm, "history")
        abbot = Abbot(chat_id, "dm", dm_history)
        answer, _, _, _ = abbot.chat_completion()

        dm_history = abbot.get_history()
        dm: TelegramDM = mongo_abbot.find_one_dm_and_update(
            chat_id_filter,
            {"$set": {"tokens": abbot.history_tokens}, "$push": {"history": {"role": "assistant", "content": answer}}},
        )
        if "`" in answer:
            answer = f"`{answer}`"
            await message.reply_text(answer, parse_mode=MARKDOWN_V2, disable_web_page_preview=True)
        else:
            await message.reply_text(answer)
    except AbbotException as abbot_exception:
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


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
            return await context.bot.send_message(
                chat_id=THE_ARCHITECT_ID, text=f"Bot kicked from group:\n\ntitle={chat.title}\nid={chat.id}"
            )
    except AbbotException as abbot_exception:
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


"""
async def handle_chat_migrated():
        => check for old chat doc
        => update old id -> new id
"""
"""
def handle_missing_username(message, username):
    log_name: str = f"{FILE_NAME}: handle_group_default"
    message_text = try_get(message, "text")
    
    if not message_text:
        return error(f"{log_name}: No message text: message={message}")
    
    new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}
    if not username:
        new_history_dict = {"role": "user", "content": f"{message_text}"}
    elif username:
        new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}
    elif not username:
        new_history_dict = {"role": "user", "content": f"{message_text}"}
    elif username:
        new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}

    return new_history_dict
"""


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

        user: User = try_get(update_data, "user")
        debug_bot.log(log_name, f"user={user}")
        user_id, username, first_name = parse_user_data(user)
        username: str = username or first_name or user_id
        debug_bot.log(log_name, f"user={user}")
        group_admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]

        chat_id_filter = {"id": chat_id}
        group: TelegramGroup = mongo_abbot.find_one_group(chat_id_filter)

        new_message_dict = message.to_dict()
        new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}
        group_update = {
            "$set": {
                "created_at": datetime.now().isoformat(),
                "title": chat_title,
                "id": chat_id,
                "type": chat_type,
                "admins": group_admins,
                "balance": 5000,
                "messages": [new_message_dict],
                "history": [BOT_SYSTEM_OBJECT_GROUPS],
                "config": BOT_GROUP_CONFIG_DEFAULT,
            }
        }
        if group:
            group_history: List = try_get(group, "history")
            group_history = [*group_history, new_history_dict]
            token_count: int = calculate_tokens(group_history)
            group_update = {
                "$set": {
                    "title": chat_title,
                    "id": chat_id,
                    "type": chat_type,
                    "admins": group_admins,
                    "tokens": token_count,
                },
                "$push": {
                    "messages": new_message_dict,
                    "history": new_history_dict,
                },
            }

        group: TelegramGroup = mongo_abbot.find_one_group_and_update(chat_id_filter, group_update)
        group_id: int = try_get(group, "id")
        group_title: str = try_get(group, "title")
        msg = f"Existing group updated:\n\ngroup_id={group_id}\ngroup_title={group_title}"
        await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=msg)

        group_config: Dict = try_get(group, "config")
        unleashed: Dict = try_get(group_config, "unleashed")
        count: Dict = try_get(group_config, "count")
        if unleashed and count > 0:
            abbot = Abbot(chat_id, chat_type, group_history)
            if abbot.history_len % count == 0:
                current_sats: TelegramGroup = mongo_abbot.get_group_balance(chat_id_filter)
                if current_sats == 0:
                    return
                debug_bot.log(log_name, f"current_sats={current_sats}")

                answer, input_tokens, output_tokens, _ = abbot.chat_completion()

                response: Dict = await recalc_balance_sats(input_tokens, output_tokens, current_sats, context.bot)
                sats_remaining: int = try_get(response, "data")
                if not successful(response):
                    sub_log_name = f"{log_name}: recalc_balance_sats"
                    error_bot.log(log_name, f"response={response}")
                    msg = f"{sub_log_name}: Failed to calculate remaining sats"
                    error_bot.log(log_name, msg)
                    error_bot.log(log_name, f"current_sats={current_sats}\nresponse={response}")
                    error_bot.log(log_name, f"chat_id={chat_id}\nchat_title={chat_title}")
                    await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=msg)

                if not sats_remaining and current_sats > 0:
                    sats_remaining = current_sats - 250
                else:
                    sats_remaining = 0
                    abbot_squawk = f"Group balance: {current_sats}\n\ngroup_id={chat_id}\ngroup_title={chat_title}"
                    answer = f"{answer}\n\n Note: You group is now out of SATs. Please run /fund to topup."
                    debug_bot.log(log_name, abbot_squawk)
                    await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
                debug_bot.log(log_name, f"sats_remaining={sats_remaining}")

                token_count: int = abbot.calculate_history_tokens()
                assistant_history_update = {"role": "assistant", "content": answer}
                group: TelegramGroup = mongo_abbot.find_one_group_and_update(
                    chat_id_filter,
                    {
                        "$set": {"balance": sats_remaining, "tokens": token_count},
                        "$push": {"history": assistant_history_update},
                    },
                )
                debug_bot.log(log_name, f"group={group}")
                await message.reply_text(answer)
    except AbbotException as abbot_exception:
        await bot_squawk(f"{log_name}: {abbot_exception}", context)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    log_name: str = f"{FILE_NAME}: error_handler"
    exception = context.error
    formatted_traceback = "".join(traceback.format_exception(None, exception, exception.__traceback__))
    base_message = "Exception while handling Telegram update"
    base_message = f"{base_message}\n\tUpdate={update.to_dict()}\n\tContext={context}"
    base_message = f"{base_message}\n\n\tException: {exception}\n\n\tTraceback: {formatted_traceback}"

    update_dict = update.to_dict()
    error_bot.log(log_name, "Exception while handling update")
    error_bot.log(log_name, f"Update={json.dumps(update_dict, indent=4)}")
    error_bot.log(log_name, f"Exception: {exception}")
    error_bot.log(log_name, f"Traceback: {formatted_traceback}")

    await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {base_message}")


class TelegramBotBuilder:
    from lib.abbot.config import BOT_TELEGRAM_TOKEN

    def __init__(self):
        log_name: str = f"{FILE_NAME}: TelegramBotBuilder()"
        debug_bot.log(log_name, f"Telegram abbot initializing: name={BOT_NAME} handle={BOT_TELEGRAM_HANDLE}")
        telegram_bot = ApplicationBuilder().token(self.BOT_TELEGRAM_TOKEN).build()
        debug_bot.log(log_name, f"Telegram abbot initialized")

        # Add command handlers
        telegram_bot.add_handlers(
            handlers=[
                MessageHandler(CHAT_TYPE_GROUPS & (NEW_CHAT_MEMBERS | CHAT_CREATED), handle_group_adds_abbot),
                MessageHandler(UpdateFilter(CHAT_TYPE_GROUPS & MESSAGE_OR_EDITED), handle_group_message_edit),
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
                CommandHandler("status", status),
                CommandHandler("balance", balance),
                CommandHandler("fund", fund),
                CallbackQueryHandler(fund_button),
                # CommandHandler("cancel", fund_cancel),
                CommandHandler("markdown", reply_markdown),
            ]
        )

        telegram_bot.add_handlers(
            handlers=[
                MessageHandler(CHAT_TYPE_PRIVATE, handle_dm),
                MessageHandler(CHAT_TYPE_GROUPS & FILTER_MENTION_ABBOT, handle_group_mention),
                MessageHandler(CHAT_TYPE_GROUPS & FilterAbbotReply(), handle_group_reply),
                MessageHandler(CHAT_TYPE_GROUPS & LEFT_CHAT_MEMEBERS, handle_group_kicks_bot),
                MessageHandler(CHAT_TYPE_GROUPS, handle_group_default),
            ]
        )
        telegram_bot.add_error_handler(error_handler)

        self.telegram_bot = telegram_bot

    def run(self):
        log_name: str = f"{FILE_NAME}: TelegramBotBuilder.run"
        debug_bot.log(log_name, f"Telegram abbot polling")
        self.telegram_bot.run_polling()
