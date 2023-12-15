# core
import json
import time
import uuid
import traceback

from os.path import abspath
from datetime import datetime

from typing import Any, Dict, List, Optional

RAW_MESSAGE_JL_FILE = abspath("src/data/raw_messages.jsonl")
MATRIX_IMG_FILEPATH = abspath("src/assets/unplugging_matrix.jpg")
KOOLAID_GIF_FILEPATH = abspath("src/assets/koolaid.gif")

# packages
from telegram import Update, Message, Chat, User
from telegram.constants import MessageEntityType, ParseMode
from telegram.ext import (
    ContextTypes,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
)
from telegram.ext.filters import ChatType, StatusUpdate, Regex, Entity, REPLY, Mention

from constants import (
    ABBOT_SQUAWKS,
    HELP_MENU,
    INTRODUCTION,
    OPENAI_MODEL,
    RULES,
    SATOSHIS_PER_BTC,
    THE_CREATOR,
)
from ..abbot.config import (
    BOT_GROUP_CONFIG_DEFAULT,
    BOT_GROUP_CONFIG_STARTED,
    BOT_LIGHTNING_ADDRESS,
    BOT_SYSTEM_OBJECT_DMS,
    BOT_SYSTEM_OBJECT_GROUPS,
    BOT_NAME,
    BOT_TELEGRAM_HANDLE,
    BOT_TELEGRAM_SUPPORT_CONTACT,
    ORG_INPUT_TOKEN_COST,
    ORG_OUTPUT_TOKEN_COST,
    ORG_PER_TOKEN_COST_DIV,
    ORG_TOKEN_COST_MULT,
)

MARKDOWN_V2 = ParseMode.MARKDOWN_V2
MENTION = MessageEntityType.MENTION

GROUPS = ChatType.GROUPS
GROUP = ChatType.GROUP
PRIVATE = ChatType.PRIVATE

GROUP_CHAT_CREATED = StatusUpdate.CHAT_CREATED
NEW_GROUP_CHAT_MEMBERS = StatusUpdate.NEW_CHAT_MEMBERS
LEFT_GROUP_CHAT_MEMEBERS = StatusUpdate.LEFT_CHAT_MEMBER
REGEX_BOT_TELEGRAM_HANDLE = Regex(BOT_TELEGRAM_HANDLE)
FILTER_MENTION_ABBOT = Mention(BOT_TELEGRAM_HANDLE)
ENTITY_MENTION = Entity(MENTION)

# local
from ..logger import debug_bot, error_bot
from ..utils import error, qr_code, success, try_get, successful
from ..db.mongo import TelegramDM, TelegramGroup, mongo_abbot
from ..abbot.core import Abbot
from ..abbot.utils import (
    calculate_tokens,
    parse_chat_data,
    parse_message_data,
    parse_message_data_keys,
    parse_user_data,
    parse_update_data,
)
from ..payments import Coinbase, CoinbasePrice, Strike, init_payment_processor, init_price_provider
from ..abbot.exceptions.exception import AbbotException

strike: Strike = init_payment_processor()
price_provider: Coinbase = init_price_provider()

import tiktoken

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)


async def get_live_price() -> int:
    log_name: str = f"{__name__}: get_live_price"
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


def usd_to_sats(usd_amount: int) -> int:
    price_dict: Dict[CoinbasePrice] = mongo_abbot.find_prices()[-1]
    btc_price_usd: int = try_get(price_dict, "amount")
    if btc_price_usd:
        if type(btc_price_usd) != int:
            btc_price_usd: int = int(btc_price_usd)
    else:
        btc_price_usd: int = get_live_price()
    return (usd_amount / int(btc_price_usd)) * SATOSHIS_PER_BTC


def sats_to_usd(sats_amount: int) -> int:
    price_dict: Dict[CoinbasePrice] = mongo_abbot.find_prices()[-1]
    btc_price_usd: int = try_get(price_dict, "amount")
    if btc_price_usd:
        if type(btc_price_usd) != int:
            btc_price_usd: int = int(btc_price_usd)
    else:
        btc_price_usd: int = get_live_price()
    return (sats_amount / SATOSHIS_PER_BTC) * int(btc_price_usd)


async def balance_remaining(input_token_count: int, output_token_count: int, current_group_balance: int):
    log_name: str = f"{__name__}: balance_remaining"
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
        btcusd_price: int = get_live_price()
    btcusd_price = float(btcusd_price)

    cost_input_tokens = (input_token_count / ORG_PER_TOKEN_COST_DIV) * (ORG_INPUT_TOKEN_COST * ORG_TOKEN_COST_MULT)
    cost_output_tokens = (output_token_count / ORG_PER_TOKEN_COST_DIV) * (ORG_OUTPUT_TOKEN_COST * ORG_TOKEN_COST_MULT)
    total_token_cost_usd = cost_input_tokens + cost_output_tokens
    total_token_cost_sats = (total_token_cost_usd / btcusd_price) * SATOSHIS_PER_BTC
    if total_token_cost_sats > current_group_balance or current_group_balance == 0:
        return 0
    remaining_balance = current_group_balance - total_token_cost_sats
    return success("Success calculate remaining balance", data=int(remaining_balance))


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{__name__}: help"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        await message.reply_text(HELP_MENU)
    except AbbotException as abbot_exception:
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{__name__}: rules"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        await message.reply_text(RULES)
    except AbbotException as abbot_exception:
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{__name__}: start"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        message_text, message_date = parse_message_data(message)
        chat: Chat = try_get(update_data, "chat")
        chat_id, chat_title, chat_type = parse_chat_data(chat)
        user: User = try_get(update_data, "user")
        user_id, username = parse_user_data(user)
        admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]
        debug_bot.log(log_name, f"admins={admins}")
        new_message_dict = message.to_dict()
        group_update = {
            "$set": {
                "created_at": datetime.now().isoformat(),
                "title": chat.title,
                "id": chat.id,
                "type": chat.type,
                "admins": admins,
                "balance": 50000,
                "messages": [new_message_dict],
                "history": [
                    BOT_SYSTEM_OBJECT_GROUPS,
                    {"role": "assistant", "content": f"Please wait while {BOT_NAME} is unplugged from the Matrix"},
                    {"role": "assistant", "content": INTRODUCTION},
                    {"role": "user", "content": f"{username} said: {message_text} on {message_date}"},
                ],
                "config": BOT_GROUP_CONFIG_DEFAULT,
            }
        }
        chat_id_filter = {"id": chat_id}
        group_config: Dict = mongo_abbot.get_group_config(chat_id_filter)
        debug_bot.log(log_name, f"group_config={group_config}")
        if group_config:
            group_update = {
                "$set": {
                    "title": chat_title,
                    "id": chat_id,
                    "type": chat_type,
                    "admins": admins,
                    "config": BOT_GROUP_CONFIG_STARTED,
                },
                "$push": {
                    "messages": new_message_dict,
                    "history": {
                        "$each": [
                            {"role": "assistant", "content": INTRODUCTION},
                            {"role": "user", "content": f"{username} said: {message_text} on {message_date}"},
                        ]
                    },
                },
            }
        group: TelegramGroup = mongo_abbot.find_one_group_and_update(chat_id_filter, group_update)
        debug_bot.log(log_name, f"group={group}")
        current_balance: TelegramGroup = mongo_abbot.get_group_balance(chat_id_filter)
        if current_balance == 0:
            group_msg = f"⚡️ Group: {chat_title} ⚡️ "
            sats_balance_msg = f"⚡️ Bitcoin Balance: {current_balance} SATs ⚡️"
            usd_balance = sats_to_usd(current_balance)
            usd_balance_msg = f"💰 Dollar Balance: {usd_balance} USD 💰"
            fund_msg = "Please run /fund <amount> <currency> to topup (e.g. /fund 50000 sats or /fund 10 usd)."
            await message.reply_text(f"{group_msg} \n {sats_balance_msg} \n {usd_balance_msg} \n {fund_msg}")
        debug_bot.log(log_name, f"current_balance={current_balance}")
        started: Dict = try_get(group_config, "started", default=try_get(group, "config", "started"))
        if started:
            already_started_msg = f"{BOT_NAME} already started for your group"
            rules_msg = f"Rules of engagement: {RULES}"
            full_msg = f"{already_started_msg} \n\n {rules_msg}"
            debug_bot.log(log_name, f"full_msg={full_msg}")
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {full_msg}")
            return await message.reply_text(full_msg)
        debug_bot.log(log_name, f"started={started}")
        await message.reply_photo(MATRIX_IMG_FILEPATH, f"Please wait while {BOT_NAME} is unplugged from the Matrix")
        time.sleep(5)
        await message.reply_text(INTRODUCTION)
    except AbbotException as abbot_exception:
        await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{__name__}: stop"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        debug_bot.log(log_name, f"message={message}")
        chat: Chat = try_get(update_data, "chat")
        debug_bot.log(log_name, f"chat={chat}")
        chat_id, chat_title, chat_type = parse_chat_data(chat)
        debug_bot.log(log_name, f"chat_id, chat_title, chat_type={chat_id, chat_title, chat_type}")
        admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]
        debug_bot.log(log_name, f"admins={admins}")
        chat_id_filter = {"id": chat_id}
        group_config: Dict = mongo_abbot.get_group_config(chat_id_filter)
        debug_bot.log(log_name, f"group_config={group_config}")
        if not group_config:
            return await message.reply_text("Group does not exist. Did you run /start?")
        started: bool = not try_get(group_config, "started")
        debug_bot.log(log_name, f"started={started}")
        stopped: bool = not started
        debug_bot.log(log_name, f"stopped={stopped}")
        if stopped:
            reply_text_err = f"{BOT_NAME} has not been started. Please run the /start command first."
            abbot_squawk = f"{log_name}: {reply_text_err} - chat_id={chat_id}, chat_title={chat_title}"
            error_bot.log(log_name, abbot_squawk)
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
            return await message.reply_text(reply_text_err)
        group: TelegramGroup = mongo_abbot.find_one_group_and_update(
            chat_id_filter,
            {
                "$set": {
                    "id": chat_id,
                    "title": chat_title,
                    "type": chat_type,
                    "admins": admins,
                    "config.started": False,
                },
                "$push": {"messages": message.to_dict()},
                "$setOnInsert": {"created_at": datetime.now().isoformat()},
            },
        )
        debug_bot.log(log_name, f"group={group}")
        is_stopped: bool = not try_get(group, "config", "started")
        if not is_stopped:
            reply_text_err = f"Failed to stop {BOT_NAME}. Please contact @nonni_io for assistance."
            abbot_squawk = f"{log_name}: {reply_text_err} => chat_id={chat_id}, chat_title={chat_title}"
            error_bot.log(log_name, abbot_squawk)
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
            return await message.reply_text(reply_text_err)
        await message.reply_text(f"Stop successful. Thanks for using {BOT_NAME}! Come back soon!")
    except AbbotException as abbot_exception:
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def handle_group_mention(update: Update, context: ContextTypes.DEFAULT_TYPE, reply=False):
    try:
        fn = "handle_group_reply" if reply else "handle_group_mention"
        log_name: str = f"{__name__}: {fn}"

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
        chat_id, chat_title, chat_type = parse_chat_data(chat)
        debug_bot.log(log_name, f"chat_id={chat_id} chat_title={chat_title} chat_type={chat_type}")

        chat_id_filter = {"id": chat_id}
        group_config: Dict = mongo_abbot.get_group_config(chat_id_filter)
        if not group_config:
            reply_text_err = f"{BOT_NAME} is stopped. Please run the /start command."
            abbot_squawk = f"{log_name}: {reply_text_err}: id={chat_id}, title={chat_title}"
            error_bot.log(log_name, f"No group_config! {group_config}")
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
            return await message.reply_text(reply_text_err)
        debug_bot.log(log_name, f"group_config={group_config}")

        started: bool = try_get(group_config, "started")
        debug_bot.log(log_name, f"started={started}")
        stopped: bool = not started
        debug_bot.log(log_name, f"stopped={stopped}")
        if stopped:
            reply_text_err = f"{BOT_NAME} has not been started. Please run the /start command first."
            abbot_squawk = f"{log_name}: {reply_text_err}: id={chat_id}, title={chat_title}"
            error_bot.log(log_name, abbot_squawk)
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
            # return await message.reply_text(reply_text_err)

        user: User = try_get(update_data, "user")
        user_id, username = parse_user_data(user)

        admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]
        debug_bot.log(log_name, f"admins={admins}")

        group: TelegramGroup = mongo_abbot.find_one_group_and_update(
            chat_id_filter,
            {
                "$push": {
                    "messages": message.to_dict(),
                    "history": {"role": "user", "content": f"{username} said: {message_text} on {message_date}"},
                },
            },
        )
        group_history = try_get(group, "history")
        if not group_history:
            reply_text_err = f"{BOT_NAME} has not been started. Please run the /start command first."
            abbot_squawk = f"{log_name}: {reply_text_err}: id={chat_id}, title={chat_title}"
            error_bot.log(log_name, abbot_squawk)
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
        abbot = Abbot(chat_id, "group", group_history)
        answer, input_tokens, output_tokens, _ = abbot.chat_completion()

        current_balance: TelegramGroup = mongo_abbot.get_group_balance(chat_id_filter)
        if current_balance == 0:
            return await message.reply_text("No Funds Available. Please run /fund to topup.")

        response: Dict = await balance_remaining(input_tokens, output_tokens, current_balance)
        if not successful(response):
            error_bot.log(log_name, f"response={response}")
            msg = f"{log_name}: Failed to calculate balance:"
            msg = f"{msg} balance_remaining.response={response}\nchat=(id={chat_id}, title=({chat_title})"
            return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=msg)

        remaining_balance: int = try_get(response, "data", default=0)
        error_bot.log(log_name, f"remaining_balance={remaining_balance}")

        group: TelegramGroup = mongo_abbot.find_one_group_and_update(
            chat_id_filter,
            {
                "$set": {
                    "id": chat_id,
                    "title": chat_title,
                    "type": chat_type,
                    "admins": admins,
                    "balance": remaining_balance,
                }
            },
        )
        debug_bot.log(log_name, f"group={group}")
        return await message.reply_text(answer)
    except AbbotException as abbot_exception:
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def handle_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{__name__}: handle_group_reply: "
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")

        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")

        message: Message = try_get(update_data, "message")
        from_user: Optional[User] = try_get(message, "reply_to_message", "from_user")
        if from_user.is_bot and from_user.username == BOT_TELEGRAM_HANDLE:
            return await handle_group_mention(update, context, reply=True)
    except AbbotException as abbot_exception:
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def handle_chat_creation_members_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{__name__}: handle_chat_creation_members_added"
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
        chat_id, chat_title, chat_type = parse_chat_data(chat)

        # user: User = try_get(update_data, "user")
        # user_id, username = parse_user_data(user)

        admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]
        debug_bot.log(log_name, f"admins={admins}")

        if not group_chat_created and new_chat_members:
            if BOT_TELEGRAM_HANDLE not in [username for username in new_chat_members]:
                return debug_bot.log(log_name, "Abbot not added to group")
        new_message_dict = message.to_dict()
        group: TelegramGroup = mongo_abbot.find_one_group_and_update(
            {"id": chat_id},
            {
                "$set": {
                    "id": chat_id,
                    "title": chat_title,
                    "type": chat_type,
                    "admins": admins,
                },
                "$push": {"messages": new_message_dict},
                "$setOnInsert": {
                    "created_at": datetime.now().isoformat(),
                    "balance": 50000,
                    "messages": [],
                    "history": [BOT_SYSTEM_OBJECT_GROUPS],
                },
            },
        )
        debug_bot.log(log_name, f"group={group}")
        group_title: str = try_get(group, "title")
        group_id: str = try_get(group, "id")
        return await context.bot.send_message(
            chat_id=ABBOT_SQUAWKS, text=f"{log_name}: Abbot added to new group: title={group_title}, id={group_id})"
        )
    except AbbotException as abbot_exception:
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def handle_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{__name__}: handle_chat_creation_members_added"

        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")

        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")

        message: Message = try_get(update_data, "message")
        message_text, message_date = parse_message_data(message)

        chat: Chat = try_get(update_data, "chat")
        chat_id, _, chat_type = parse_chat_data(chat)

        user: User = try_get(update_data, "user")
        user_id, username = parse_user_data(user)
        if not username:
            username = try_get(chat, "username")

        chat_id = try_get(chat, "id")
        new_message_dict = message.to_dict()
        chat_id_filter = {"id": chat_id}
        dm: TelegramDM = mongo_abbot.find_one_dm_and_update(
            chat_id_filter,
            {
                "$set": {"id": chat_id, "username": username, "type": chat_type},
                "$push": {
                    "messages": new_message_dict,
                    "history": {"role": "user", "content": f"{username} said: {message_text} on {message_date}"},
                },
                "$setOnInsert": {
                    "created_at": datetime.now().isoformat(),
                    "messages": [new_message_dict],
                    "history": [BOT_SYSTEM_OBJECT_DMS],
                },
            },
        )

        debug_bot.log(log_name, f"handle_dm => found or inserted chat=(id={chat.id}, user=({user.username}")
        dm_msg = f"dm={dm}\nchat=(id={chat.id}, title=({chat.title})"
        await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=dm_msg)

        dm_history: List = try_get(dm, "history")
        debug_bot.log(log_name, f"dm_history={dm_history[-1]}")

        abbot = Abbot(chat.id, "dm", dm_history)
        answer, _, _, _ = abbot.chat_completion()
        # TODO: Add balance to DMs
        dm: TelegramDM = mongo_abbot.find_one_group_and_update(
            chat_id_filter,
            {"$push": {"history": {"role": "assistant", "content": answer}}},
        )
        debug_bot.log(log_name, f"{dm_msg}\nAbbot DMs with {user.username}")
        return await message.reply_text(answer)
    except AbbotException as abbot_exception:
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{__name__}: balance"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")

        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")

        message: Message = try_get(update_data, "message")
        chat: Chat = try_get(update_data, "chat")
        group: TelegramGroup = mongo_abbot.find_one_group({"id": chat.id})

        sats_balance = try_get(group, "balance", default=0)
        usd_balance = sats_to_usd(sats_balance)
        group_msg = f"⚡️ Group: {chat.title} ⚡️"
        sats_balance_msg = f"⚡️ SAT Balance: {sats_balance} ⚡️"
        usd_balance_msg = f"💰 USD Balance: {usd_balance} 💰"
        return await message.reply_text(f"{group_msg}\n{sats_balance_msg}\n{usd_balance_msg}")
    except AbbotException as abbot_exception:
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def fund_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{__name__}: fund_cancel"

        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")

        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")

        message: Message = try_get(update_data, "message")
        chat: Chat = try_get(update_data, "chat")

        message_text: str = message.text
        debug_bot.log(log_name, f"message_text={message_text}")

        args = message_text.split()
        debug_bot.log(log_name, f"args={args}")

        chat_title: int = try_get(chat, "title")
        chat_id: int = try_get(chat, "id")
        invoice_id = try_get(args, 1) or strike.CHAT_ID_INVOICE_ID_MAP.get(chat_id, None)
        if not invoice_id:
            return await message.reply_text("Invoice not found")
        debug_bot.log(log_name, f"invoice_id={invoice_id}")

        await message.reply_text("Attempting to cancel your invoice, please wait ...")
        debug_bot.log(log_name, f"payment_processor={strike.to_dict()}")

        cancel_squawk = f"Failed to cancel invoice: chat_id={chat_id}, chat_title={chat_title}, invoice_id={invoice_id}"
        cancel_fail = (
            "Failed to cancel invoice. Try again or pay abbot@atlbitlab.com & contact @nonni_io for confirmation"
        )
        cancelled = await strike.expire_invoice(invoice_id)
        if not cancelled:
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=cancel_squawk)
            return await message.reply_text(cancel_fail)

        await message.reply_text(f"Invoice id {invoice_id} successfully cancelled for {chat_title}")
    except AbbotException as abbot_exception:
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def fund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{__name__}: fund"

        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")

        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")

        message: Message = try_get(update_data, "message")
        chat: Chat = try_get(update_data, "chat")
        user: User = try_get(update_data, "user")

        message_text: str = message.text
        debug_bot.log(log_name, f"message_text={message_text}")

        args = message_text.split()
        args_len = len(args)
        debug_bot.log(log_name, f"args={args}")
        sats_example = "For sats: /fund 50000 sats"
        usd_example = "For usd: /fund 10 usd"
        invoice_error_args = (
            "InvoiceError: Missing amount and currency unit. Did you pass an amount and a currency unit?"
        )
        invoice_error_unit = "InvoiceError: Unrecognized currency unit. Did you pass one of usd or sats?"
        if args_len < 2:
            return await message.reply_text(f"{invoice_error_args}.\n\n{sats_example}\n\n{usd_example}")
        elif args_len < 3:
            return await message.reply_text(f"{invoice_error_args}\n\n{sats_example}\n\n{usd_example}")

        amount: int = int(try_get(args, 1))
        debug_bot.log(log_name, f"amount={amount}")

        currency_unit: str = try_get(args, 2, default="sats")
        currency_unit = currency_unit.lower()
        debug_bot.log(log_name, f"currency_unit={currency_unit}")
        if currency_unit == "sats":
            symbol = ""
            # ₿
            amount = sats_to_usd(amount)
        elif currency_unit == "usd":
            currency_unit = ""
            symbol = "$"
            amount = sats_to_usd(amount)
        else:
            return await message.reply_text(f"{invoice_error_unit}\n\n{sats_example}\n\n{usd_example}")

        await message.reply_text("Creating your invoice, please wait ...")
        debug_bot.log(log_name, f"strike={strike}")
        chat_type: str = try_get(chat, "type")
        chat_id: int = try_get(chat, "id")
        topup_for: str = try_get(chat, "username") if chat_type == "dm" else try_get(chat, "title")
        topup_by: str = try_get(chat, "username", default="") if chat_type == "dm" else try_get(user, "username")

        d0 = f"{chat_type.capitalize()} balance topup"
        d1 = f"\n\nTitle: {topup_for}\n\nSender: @{topup_by}\n\nAmount: {symbol}{amount} {currency_unit}"
        description = f"{d0} {d1}"

        cid = str(uuid.uuid1())
        debug_bot.log(log_name, f"description={description} cid={cid}")
        response = await strike.get_invoice(cid, description, amount, chat.id)
        debug_bot.log(log_name, f"response={response}")

        create_squawk = f"Failed to create strike invoice: {json.dumps(response)}"
        create_fail_0 = f"Failed to create invoice. Please try again"
        create_fail_1 = f"or pay to {BOT_LIGHTNING_ADDRESS} and contact @{BOT_TELEGRAM_SUPPORT_CONTACT}"
        create_fail = f"{create_fail_0} {create_fail_1}"
        if not successful(response):
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=create_squawk)
            return await message.reply_text(create_fail)

        invoice_id = try_get(response, "invoice_id")
        invoice = try_get(response, "lnInvoice")
        expirationInSec = try_get(response, "expirationInSec")
        strike.CHAT_ID_INVOICE_ID_MAP[chat_id] = invoice_id
        if None in (invoice_id, invoice, expirationInSec):
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=create_squawk)
            return await message.reply_text(create_fail)

        await message.reply_photo(photo=qr_code(invoice), caption=f"{description}\n\nExpires in: {expirationInSec}")
        await message.reply_markdown_v2(invoice)

        cancel_squawk = f"Failed to cancel strike invoice: description={description}, invoice_id={invoice_id}"
        cancel_fail = "Failed to cancel invoice. Please try again or pay to abbot@atlbitlab.com and contact @nonni_io"
        is_paid = False
        while expirationInSec >= 0 and not is_paid:
            debug_bot.log(log_name, f"expirationInSec={expirationInSec}")
            if expirationInSec == 0:
                debug_bot.log(log_name, f"expirationInSec == 0, cancelling invoice_id={invoice_id}")
                cancelled = await strike.expire_invoice(invoice_id)
                debug_bot.log(log_name, f"cancelled={cancelled}")
                if not cancelled:
                    await context.bot.send_message(chat_id=THE_CREATOR, text=cancel_squawk)
                    return await message.reply_text(cancel_fail)
            is_paid = await strike.invoice_is_paid(invoice_id)
            debug_bot.log(log_name, f"is_paid={is_paid}")
            expirationInSec -= 1
            time.sleep(1)

        if is_paid:
            group: TelegramGroup = mongo_abbot.find_one_group_and_update({"id": chat.id}, {"$inc": {"balance": amount}})
            if not group:
                error_bot.log(log_name, f"not group")
                return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=group)
            balance: int = try_get(group, "balance", default=amount)
            await message.reply_text(f"Invoice Paid! ⚡️ {chat.title} balance: {balance} sats ⚡️")
        else:
            await message.reply_text(f"Invoice expired! Please run {message.text} again.")
    except AbbotException as abbot_exception:
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def handle_bot_kicked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{__name__}: handle_bot_kicked"
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
                chat_id=THE_CREATOR, text=f"Bot kicked from group:\n\ntitle={chat.title}\nid={chat.id}"
            )
    except AbbotException as abbot_exception:
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


"""
async def handle_chat_migrated():
        => check for old chat doc
        => update old id -> new id
"""


async def handle_default_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{__name__}: handle_default_group"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")

        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")

        message: Message = try_get(update_data, "message")
        debug_bot.log(log_name, f"message={message}")
        message_text, message_date = parse_message_data(message)

        chat: Chat = try_get(update_data, "chat")
        debug_bot.log(log_name, f"chat={chat}")
        chat_id, chat_title, chat_type = parse_chat_data(chat)

        user: User = try_get(update_data, "user")
        debug_bot.log(log_name, f"user={user}")
        user_id, username = parse_user_data(user)
        username: str = username or try_get(chat, "username", default=user_id)
        group_admins: Any = None
        if chat_type != "private":
            group_admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]

        chat_id_filter = {"id": chat_id}
        new_message_dict = message.to_dict()
        new_history_dict = {"role": "user", "content": f"{username} said: {message_text} on {message_date}"}
        group_update = {
            "$set": {"title": chat_title, "id": chat_id, "type": chat_type, "admins": group_admins},
            "$push": {
                "messages": new_message_dict,
                "history": new_history_dict,
            },
        }
        group: TelegramGroup = mongo_abbot.find_one_group(chat_id_filter)
        if not group:
            group_update = {
                "$set": {
                    "created_at": datetime.now().isoformat(),
                    "title": chat_title,
                    "id": chat_id,
                    "type": chat_type,
                    "admins": group_admins,
                    "balance": 50000,
                    "messages": [new_message_dict],
                    "history": [BOT_SYSTEM_OBJECT_GROUPS],
                    "config": BOT_GROUP_CONFIG_DEFAULT,
                }
            }
            if group_admins:
                group_update["admins"] = group_admins

        group_history: List = try_get(group, "history")
        if group_history:
            group_history = [*group_history, new_history_dict]
            token_count: int = calculate_tokens(group_history)
            group: TelegramGroup = mongo_abbot.find_one_group_and_update(
                chat_id_filter, {"$set": {"tokens": token_count}}
            )

        group_id: int = try_get(group, "id")
        group_title: str = try_get(group, "title")
        msg = f"Existing group updated:\n\ngroup_id={group_id}\ngroup_title={group_title}"
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=msg)
    except AbbotException as abbot_exception:
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    log_name: str = f"{__name__}: TelegramBotBuilder.__init__"

    exception = context.error
    formatted_traceback = "".join(traceback.format_exception(None, exception, exception.__traceback__))

    base_message = "Exception while handling Telegram update"
    base_message = f"{base_message}\n\tUpdate={update.to_dict()}\n\tContext={context}"
    base_message = f"{base_message}\n\n\tException: {exception}\n\n\tTraceback: {formatted_traceback}"
    # error_bot.log(log_name, base_message)

    error_bot.log(log_name, "Exception while handling update")

    error_bot.log(log_name, f"Update={update.to_dict()}")
    error_bot.log(log_name, f"Context={context}")

    error_bot.log(log_name, f"Exception: {exception}")
    error_bot.log(log_name, f"Traceback: {formatted_traceback}")

    await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {exception}")


class TelegramBotBuilder:
    from lib.abbot.config import BOT_TELEGRAM_TOKEN

    def __init__(self):
        log_name: str = f"{__name__}: TelegramBotBuilder.__init__()"
        debug_bot.log(log_name, f"Telegram abbot initializing: name={BOT_NAME} handle={BOT_TELEGRAM_HANDLE}")
        telegram_bot = ApplicationBuilder().token(self.BOT_TELEGRAM_TOKEN).build()
        debug_bot.log(log_name, f"Telegram abbot initialized")

        # Add command handlers
        telegram_bot.add_handlers(
            handlers=[
                MessageHandler(
                    GROUPS & (NEW_GROUP_CHAT_MEMBERS | GROUP_CHAT_CREATED), handle_chat_creation_members_added
                ),
                CommandHandler("help", help),
                CommandHandler("rules", rules),
                CommandHandler("start", start),
                CommandHandler("stop", stop),
                CommandHandler("balance", balance),
                CommandHandler("fund", fund),
                CommandHandler("cancel", fund_cancel),
                MessageHandler(PRIVATE, handle_dm),
                MessageHandler(GROUPS & FILTER_MENTION_ABBOT, handle_group_mention),
                MessageHandler(GROUPS & REPLY, handle_group_reply),
                MessageHandler(GROUPS & LEFT_GROUP_CHAT_MEMEBERS, handle_bot_kicked),
                MessageHandler(GROUPS, handle_default_group),
            ]
        )

        telegram_bot.add_error_handler(error_handler)

        self.telegram_bot = telegram_bot

    def run(self):
        log_name: str = f"{__name__}: TelegramBotBuilder.run"
        debug_bot.log(log_name, f"Telegram abbot polling")
        self.telegram_bot.run_polling()
