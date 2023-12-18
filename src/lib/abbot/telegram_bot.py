# core
import time
import uuid
import traceback
from json import dumps

from os.path import abspath
from datetime import datetime

from typing import Any, Dict, List, Optional

RAW_MESSAGE_JL_FILE = abspath("src/data/raw_messages.jsonl")
MATRIX_IMG_FILEPATH = abspath("src/assets/unplugging_matrix.jpg")
KOOLAID_GIF_FILEPATH = abspath("src/assets/koolaid.gif")

# packages
from telegram import Bot, Update, Message, Chat, User
from telegram.constants import MessageEntityType, ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, BaseHandler
from telegram.ext.filters import ChatType, StatusUpdate, Regex, Entity, Mention, UpdateFilter, UpdateType, REPLY

from constants import (
    ABBOT_SQUAWKS,
    HELP_MENU,
    INTRODUCTION,
    OPENAI_MODEL,
    RULES,
    SATOSHIS_PER_BTC,
    THE_ARCHITECT_ID,
    THE_ARCHITECT_USERNAME,
    THE_ARCHITECT_HANDLE,
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
    BOT_TELEGRAM_USERNAME,
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
CHAT_CREATED = StatusUpdate.CHAT_CREATED
NEW_CHAT_MEMBERS = StatusUpdate.NEW_CHAT_MEMBERS
LEFT_CHAT_MEMEBERS = StatusUpdate.LEFT_CHAT_MEMBER
REGEX_BOT_TELEGRAM_HANDLE = Regex(BOT_TELEGRAM_HANDLE)
FILTER_MENTION_ABBOT = Mention(BOT_TELEGRAM_HANDLE)
ENTITY_MENTION = Entity(MENTION)
ENTITY_REPLY = Entity(REPLY)
MESSAGE_OR_EDITED = UpdateType.MESSAGES

# local
from ..logger import debug_bot, error_bot
from ..utils import error, qr_code, safe_cast_to_int, success, try_get, successful
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
FILE_NAME = __name__


# ---------------------------------------------------------------------------------------
# --                      Telegram Handlers Helper Functions                           --
# ---------------------------------------------------------------------------------------
async def get_live_price() -> int:
    log_name: str = f"{FILE_NAME}: get_live_price: "
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
    sats = int((usd_amount / btc_price_usd) * SATOSHIS_PER_BTC)
    if sats <= 0:
        sats = 50
    return sats


async def sat_to_usd(sats_amount: int) -> int:
    price_dict: Dict[CoinbasePrice] = mongo_abbot.find_prices()[-1]
    btc_price_usd: int = try_get(price_dict, "amount")
    if btc_price_usd:
        if type(btc_price_usd) != int:
            btc_price_usd: int = int(btc_price_usd)
    else:
        btc_price_usd: int = await get_live_price()
    usd = float((sats_amount / SATOSHIS_PER_BTC) * int(btc_price_usd))
    if usd <= 0.01:
        usd = 0.01
    return usd


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
        await bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")
        err_msg = "Failed to calculate remaining balance"
        raise abbot_exception


# ---------------------------------------------------------------------------------------
# --                      Core Telegram Handler Functions                              --
# ---------------------------------------------------------------------------------------


async def handle_chat_creation_members_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: handle_chat_creation_members_added"
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


async def handle_edited(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO: handle message edited
    pass


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: help"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        await message.reply_markdown_v2(f"{HELP_MENU}")
    except AbbotException as abbot_exception:
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: rules"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")
        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")
        message: Message = try_get(update_data, "message")
        await message.reply_markdown_v2(RULES)
    except AbbotException as abbot_exception:
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: start"
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
        _, username = parse_user_data(user)

        if chat_type in ("group", "supergroup", "channel"):
            admins: Any = [admin.to_dict() for admin in await chat.get_administrators()] or []
            debug_bot.log(log_name, f"admins={admins}")

        chat_id_filter = {"id": chat_id}
        new_message_dict = message.to_dict()
        intro_history_dict = {"role": "assistant", "content": INTRODUCTION}
        new_history_dict = {"role": "user", "content": f"@{username} said: {message_text} on {message_date}"}
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
                    "balance": 50000,
                    "messages": [new_message_dict],
                    "history": [BOT_SYSTEM_OBJECT_GROUPS, intro_history_dict, new_history_dict],
                    "config": BOT_GROUP_CONFIG_STARTED,
                }
            }
        else:
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
                    "history": new_history_dict,
                },
            }

        group_config: Dict = mongo_abbot.get_group_config(chat_id_filter)
        debug_bot.log(log_name, f"group_config={group_config}")
        started: Dict = try_get(group_config, "started")
        if started:
            already_started_msg = f"{BOT_NAME} already started for your group"
            rules_msg = f"Rules of engagement: {RULES}"
            full_msg = f"{already_started_msg}\n\n{rules_msg}"
            debug_bot.log(log_name, f"full_msg={full_msg}")
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {full_msg}")
            return await message.reply_text(full_msg)

        debug_bot.log(log_name, f"started={started}")
        group: TelegramGroup = mongo_abbot.find_one_group_and_update(chat_id_filter, group_update)
        debug_bot.log(log_name, f"group={group}")
        current_balance: TelegramGroup = mongo_abbot.get_group_balance(chat_id_filter)
        if current_balance == 0:
            group_msg = f"⚡️ Group: {chat_title} ⚡️ "
            sats_balance_msg = f"⚡️ Bitcoin Balance: {current_balance} SAT ⚡️"
            usd_balance = await sat_to_usd(current_balance)
            usd_balance_msg = f"💰 Dollar Balance: {usd_balance} USD 💰"
            fund_msg = "Please run /fund <amount> <currency> to topup (e.g. /fund 50000 sats or /fund 10 usd)."
            await message.reply_text(f"{group_msg} \n {sats_balance_msg} \n {usd_balance_msg} \n {fund_msg}")
        debug_bot.log(log_name, f"current_balance={current_balance}")

        await message.reply_photo(MATRIX_IMG_FILEPATH, f"Please wait while {BOT_NAME} is unplugged from the Matrix")

        time.sleep(3)

        await message.reply_text(INTRODUCTION)
    except AbbotException as abbot_exception:
        await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: stop"
        response: Dict = await parse_update_data(update, context)
        if not successful(response):
            debug_bot.log(log_name, f"Failed to parse_update_data response={response}")

        update_data: Dict = try_get(response, "data")
        debug_bot.log(log_name, f"update_data={update_data}")

        message: Message = try_get(update_data, "message")
        message_text, message_date = parse_message_data(message)
        debug_bot.log(log_name, f"message={message}")

        chat: Chat = try_get(update_data, "chat")
        chat_id, chat_title, chat_type = parse_chat_data(chat)
        debug_bot.log(log_name, f"chat={chat}")

        if chat_type in ("group", "supergroup", "channel"):
            admins: Any = [admin.to_dict() for admin in await chat.get_administrators()] or []
            debug_bot.log(log_name, f"admins={admins}")

        user: User = try_get(update_data, "user")
        _, username = parse_user_data(user)
        debug_bot.log(log_name, f"user={user}")

        chat_id_filter = {"id": chat_id}
        new_message_dict = message.to_dict()
        new_history_dict = {"role": "user", "content": f"@{username} said: {message_text} on {message_date}"}
        group_exists: bool = mongo_abbot.group_does_exist(chat_id_filter)
        if not group_exists:
            group_dne_err = f"Group does not exist"
            reply_msg = f"Did you run /start{BOT_TELEGRAM_HANDLE}?"
            await message.reply_text(f"{group_dne_err} {reply_msg}")
            abbot_squawk = f"{group_dne_err}\n\nchat_id={chat_id}, chat_title={chat_title}"
            return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=group_dne_err)

        group_config: Dict = mongo_abbot.get_group_config(chat_id_filter)
        debug_bot.log(log_name, f"group_config={group_config}")

        started: bool = not try_get(group_config, "started")
        debug_bot.log(log_name, f"started={started}")
        if not started:
            reply_text_err = f"{BOT_NAME} has not been started - Please run /start{BOT_TELEGRAM_HANDLE}"
            abbot_squawk = f"{log_name}: {reply_text_err} - chat_id={chat_id}, chat_title={chat_title}"
            error_bot.log(log_name, abbot_squawk)
            await message.reply_text(reply_text_err)
            return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)

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
                "$push": {"messages": new_message_dict, "history": new_history_dict},
            },
        )
        debug_bot.log(log_name, f"group={group}")

        still_running: bool = not try_get(group, "config", "started")
        reply_text_err = f"Failed to stop {BOT_NAME}. Please contact {THE_ARCHITECT_HANDLE} for assistance."
        abbot_squawk = f"{log_name}: {reply_text_err} => chat_id={chat_id}, chat_title={chat_title}"
        if still_running:
            error_bot.log(log_name, abbot_squawk)
            await message.reply_text(reply_text_err)
            return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
        await message.reply_text(f"Thanks for using {BOT_NAME}! Come back soon!")
        abbot_squawk = f"{BOT_NAME} stopped\n\nchat_id={chat_id}, chat_title={chat_title}"
        await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
    except AbbotException as abbot_exception:
        await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


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
        chat_title: str = try_get(chat, "title")
        chat_id_filter = {"id": chat.id}
        group: TelegramGroup = mongo_abbot.find_one_group(chat_id_filter)

        group_balance = try_get(group, "balance", default=0)
        if group_balance and type(group_balance) == float:
            group: TelegramGroup = mongo_abbot.find_one_dm_and_update(
                chat_id_filter, {"$set": {"balance": int(group_balance)}}
            )
            group_balance = try_get(group, "balance", default=0)
        usd_balance = await sat_to_usd(group_balance)
        group_msg = f"⚡️ Group: {chat_title} ⚡️"
        sats_balance_msg = f"⚡️ SAT Balance: {group_balance} ⚡️"
        usd_balance_msg = f"💰 USD Balance: {usd_balance} 💰"
        return await message.reply_text(f"{group_msg}\n{sats_balance_msg}\n{usd_balance_msg}")
    except AbbotException as abbot_exception:
        await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def fund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: fund"

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

        user: User = try_get(update_data, "user")
        debug_bot.log(log_name, f"user={user}")
        _, username = parse_user_data(user)
        debug_bot.log(log_name, f"username={username}")
        message_text: str = message_text.split()

        args = message_text
        debug_bot.log(log_name, f"args={args}")

        invalid_usage = "Invalid usage"
        amount_currency_required = f"{invalid_usage}: Amount & currency required"
        currency_required = f"{invalid_usage}: Currency required"
        amount_must_be = f"{invalid_usage}: Amount must be a number greater than 0"
        currency_must_be = f'{invalid_usage}: Currency must be either "sat" or "usd"'
        sat_example = "Request SAT invoice: /fund 50000 sat"
        usd_example = "Request USD invoice: /fund 10 usd"

        args_len = len(args)
        if args_len == 2:
            return await message.reply_text(f"{currency_required}\n\n{sat_example}\n\n{usd_example}")
        elif args_len == 1:
            return await message.reply_text(f"{amount_currency_required}\n\n{sat_example}\n\n{usd_example}")

        if args_len == 3:
            requested_amount: int = safe_cast_to_int(try_get(args, 1))
            debug_bot.log(log_name, f"requested_amount={requested_amount}")

            requested_currency: str = try_get(args, 2, default="SAT").upper()
            debug_bot.log(log_name, f"requested_currency={requested_currency}")

            if requested_amount == 0:
                return await message.reply_text(f"{amount_must_be}\n\n{sat_example}\n\n{usd_example}")
            elif requested_currency not in ("SAT", "SATS", "USD"):
                return await message.reply_text(f"{currency_must_be}\n\n{sat_example}\n\n{usd_example}")

        req_emoji = "⚡️"
        req_symbol = "₿"
        cnv_emoji = "💰"
        cnv_symbol = "$"
        sat_amount = requested_amount
        usd_amount = await sat_to_usd(sat_amount)
        balance_inc = requested_amount
        if requested_currency == "USD":
            req_emoji = "💰"
            req_symbol = "$"
            cnv_emoji = "⚡️"
            cnv_symbol = "₿"
            sat_amount = await usd_to_sat(usd_amount)
            usd_amount = requested_amount
            balance_inc = sat_amount

        debug_bot.log(log_name, f"req_emoji={req_emoji}")
        debug_bot.log(log_name, f"req_symbol={req_symbol}")
        debug_bot.log(log_name, f"sat_amount={sat_amount}")
        debug_bot.log(log_name, f"usd_amount={usd_amount}")
        debug_bot.log(log_name, f"balance_inc={balance_inc}")

        await message.reply_text("Creating your invoice, please wait ...")

        chat_type: str = try_get(chat, "type")
        debug_bot.log(log_name, f"chat_type={chat_type}")

        chat_id: int = try_get(chat, "id")
        debug_bot.log(log_name, f"chat_id={chat_id}")

        title_detail: str = f"{username} x Abbot" if chat_type == "private" else chat_title
        debug_bot.log(log_name, f"title_detail={title_detail}")

        requester_detail: str = f"@{username}"
        debug_bot.log(log_name, f"requester={requester_detail}")

        chat_details = f"*🤖 Chat 🤖*\n*Type*\n\t{chat_type}\n*Title*\n\t{title_detail}"
        chat_details = f"{chat_details}\n*Requester*\n\t{requester_detail}"

        sat_per_dollar: int = price_provider.get_latest_bitcoin_price()

        inv_details = "*⚡️ Invoice Details ⚡️*\n\n"
        inv_date = f"*🗓️ Date 🗓️*\n\t{message_date}\n"
        inv_amount = f"{req_symbol}{requested_amount} {requested_currency}"
        inv_amt_req = f"*{req_emoji} Amount Requested {req_emoji}*\n\t{inv_amount}\n"
        inv_fx = f"*📈 Exchange Rate 📈*\n\t$1 = ⚡️{sat_per_dollar}\n\t"
        invoice_next_line = f"{inv_fx}*📝 Description 📝*\n\tTopup Abbot balance"
        if sat_per_dollar:
            invoice_next_line = f""

        inv_details_msg = (
            f"{inv_details}{inv_date}{inv_amt_req}\n\t{inv_amount}\n{invoice_next_line}\n{inv_description}"
        )
        inv_expiration = f"🕰️ Expires in *_57_* seconds on {message_date + 57} 🕰️"
        description = ""
        debug_bot.log(log_name, f"description={description} coorelation_id={coorelation_id}")
        f"""
        *⚡️ Invoice Details ⚡️*

        *🗓️ Date 🗓️*
            {message_date} 
        *💰 Amount Requested 💰*
            $1 USD
            {req_symbol}{requested_amount} {requested_currency}
        *📈 Exchange Rate 📈*
            $1 USD = ⚡️ 2434 SAT
            $1 USD = ⚡️ {sat_per_dollar} SAT
        *⚡️ Amount Conversion ⚡️*
            ⚡️ 2500 SAT
            {cnv_emoji} snv_
        *📝 Description 📝*
            Topup Abbot balance
        
        """

        coorelation_id = str(uuid.uuid1())
        response = await strike.get_invoice(coorelation_id, description, usd_amount, chat_id)
        debug_bot.log(log_name, f"response={response}")

        invoice_creation_failed = f"Invoice creation failed"
        abbot_squawk = f"{invoice_creation_failed}: {dumps(response, indent=2)}"
        reply_msg = f"{invoice_creation_failed} try command again /fund {requested_amount} {requested_currency}"
        reply_msg = f"{reply_msg} or pay amount {req_symbol}{requested_amount}"
        reply_msg = f"{reply_msg} to {BOT_LIGHTNING_ADDRESS} & contact @{BOT_TELEGRAM_SUPPORT_CONTACT} for confirmation"
        if not successful(response):
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
            return await message.reply_text(reply_msg)

        invoice_id = try_get(response, "invoice_id")
        invoice = try_get(response, "lnInvoice")
        expiration_in_sec = try_get(response, "expirationInSec")
        strike.CHAT_ID_INVOICE_ID_MAP[chat_id] = invoice_id
        if None in (invoice_id, invoice, expiration_in_sec):
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=abbot_squawk)
            return await message.reply_text(reply_msg)
        now = int(time.time())
        expiration_time = now + expiration_in_sec
        await message.reply_photo(
            photo=qr_code(invoice),
            caption=f"{description}\n\Expiration: {expiration_time} ({expiration_in_sec} seonds)",
        )
        await message.reply_markdown_v2(f"`{invoice}`")

        cancel_squawk = f"Failed to cancel strike invoice: description={description}, invoice_id={invoice_id}"
        cancel_fail = "Failed to cancel invoice. Please try again or pay to abbot@atlbitlab.com and contact {THE_ARCHITECT_HANDLE}"
        is_paid = False
        while expiration_in_sec >= 0 and not is_paid:
            debug_bot.log(log_name, f"expiration_in_sec={expiration_in_sec}")
            if expiration_in_sec == 0:
                debug_bot.log(log_name, f"expiration_in_sec == 0, cancelling invoice_id={invoice_id}")
                cancelled = await strike.expire_invoice(invoice_id)
                debug_bot.log(log_name, f"cancelled={cancelled}")
                if not cancelled:
                    await context.bot.send_message(chat_id=THE_ARCHITECT_ID, text=cancel_squawk)
                    return await message.reply_text(cancel_fail)
            is_paid = await strike.invoice_is_paid(invoice_id)
            debug_bot.log(log_name, f"is_paid={is_paid}")
            expiration_in_sec -= 1
            time.sleep(1)

        if is_paid:
            group: TelegramGroup = mongo_abbot.find_one_group_and_update(
                {"id": chat.id}, {"$inc": {"balance": balance_inc}}
            )
            if not group:
                error_bot.log(log_name, f"not group")
                return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=group)
            balance: int = try_get(group, "balance", default=requested_amount)
            await message.reply_text(f"Invoice Paid! ⚡️ {chat_title} balance: {balance} sats ⚡️")
        else:
            await message.reply_text(f"Invoice expired! Please run {message_text} again.")
    except AbbotException as abbot_exception:
        await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def fund_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: fund_cancel"

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
        cancel_fail = "Failed to cancel invoice. Try again or pay abbot@atlbitlab.com & contact {THE_ARCHITECT_HANDLE} for confirmation"
        cancelled = await strike.expire_invoice(invoice_id)
        if not cancelled:
            await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=cancel_squawk)
            return await message.reply_text(cancel_fail)

        await message.reply_text(f"Invoice id {invoice_id} successfully cancelled for {chat_title}")
    except AbbotException as abbot_exception:
        await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


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

        chat_id, chat_title, chat_type = parse_chat_data(chat)
        debug_bot.log(log_name, f"chat_id={chat_id} chat_title={chat_title} chat_type={chat_type}")

        user: User = try_get(update_data, "user")
        debug_bot.log(log_name, f"user={user}")

        _, username = parse_user_data(user)
        debug_bot.log(log_name, f"username={username}")
        if not username:
            username = try_get(user, "first_name")

        if chat_type in ("group", "supergroup", "channel"):
            admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]
            debug_bot.log(log_name, f"admins={admins}")

        chat_id_filter = {"id": chat_id}
        stopped_err = f"{BOT_NAME} not started - Please run /start{BOT_TELEGRAM_HANDLE}"
        no_group_or_config_err = "No group or group config"

        group: TelegramGroup = mongo_abbot.find_one_group(chat_id_filter)
        group_config: Dict = try_get(group, "config")
        if not group or not group_config:
            abbot_squawk = f"{log_name}: {no_group_or_config_err}: id={chat_id}, title={chat_title}"
            error_msg = f"{no_group_or_config_err}: group={group} group_config={group_config}"
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

        new_history_dict = {"role": "user", "content": f"@{username} said: {message_text} on {message_date}"}
        if not message_text:
            message_text_err = f"{log_name}: No message text: message={message} update={update}"
            return await context.bot.send_message(chat_id=THE_ARCHITECT_ID, text=message_text_err)

        if not username and not message_date:
            new_history_dict = {"role": "user", "content": f"someone said: {message_text}"}
        elif username and message_date:
            new_history_dict = {"role": "user", "content": f"@{username} said: {message_text} on {message_date}"}
        elif not username and message_date:
            new_history_dict = {"role": "user", "content": f"someone said: {message_text} on {message_date}"}
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
            abbot_squawk = f"{log_name}: {no_group_or_config_err}: id={chat_id}, title={chat_title}"
            error_msg = f"{no_group_or_config_err}: group={group} group_config={group_config}"
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
        await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


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

        chat_id, chat_title, chat_type = parse_chat_data(chat)
        debug_bot.log(log_name, f"chat_id={chat_id} chat_title={chat_title} chat_type={chat_type}")

        _, username = parse_user_data(user)
        if not username:
            username = try_get(user, "first_name")

        reply_to_message: Optional[Message] = try_get(message, "reply_to_message")
        debug_bot.log(log_name, f"reply_to_message={reply_to_message}")

        reply_to_message_from_user: Optional[User] = try_get(reply_to_message, "from_user")
        replied_to_bot = try_get(reply_to_message_from_user, "is_bot")
        debug_bot.log(log_name, f"replied_to_bot={replied_to_bot}")

        replied_to_abbot = try_get(reply_to_message_from_user, "username") == BOT_TELEGRAM_USERNAME
        debug_bot.log(log_name, f"replied_to_abbot={replied_to_abbot}")

        if chat_type in ("group", "supergroup", "channel") and replied_to_bot and replied_to_abbot:
            chat_id_filter = {"id": chat_id}
            stopped_err = f"{BOT_NAME} not started - Please run /start{BOT_TELEGRAM_HANDLE}"
            no_group_or_config_err = "No group or group config"

            group: TelegramGroup = mongo_abbot.find_one_group(chat_id_filter)
            group_config: Dict = try_get(group, "config")
            started: bool = try_get(group_config, "started")
            debug_bot.log(log_name, f"started={started}")
            if not group or not group_config:
                abbot_squawk = f"{log_name}: {no_group_or_config_err}: id={chat_id}, title={chat_title}"
                reply_msg = f"{no_group_or_config_err} - Did you run /start{BOT_TELEGRAM_HANDLE}?"
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

            new_history_dict = {"role": "user", "content": f"@{username} said: {message_text} on {message_date}"}
            if not message_text:
                message_text_err = f"{log_name}: No message text: message={message} update={update}"
                return await context.bot.send_message(chat_id=THE_ARCHITECT_ID, text=message_text_err)

            if not username and not message_date:
                new_history_dict = {"role": "user", "content": f"someone said: {message_text}"}
            elif username and message_date:
                new_history_dict = {"role": "user", "content": f"@{username} said: {message_text} on {message_date}"}
            elif not username and message_date:
                new_history_dict = {"role": "user", "content": f"someone said: {message_text} on {message_date}"}
            elif username and not message_date:
                new_history_dict = {"role": "user", "content": f"@{username} said: {message_text}"}

            admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]
            debug_bot.log(log_name, f"admins={admins}")

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
                abbot_squawk = f"{log_name}: {no_group_or_config_err}: id={chat_id}, title={chat_title}"
                error_msg = f"{no_group_or_config_err}: group={group} group_config={group_config}"
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
    except AbbotException as abbot_exception:
        await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def handle_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: handle_chat_creation_members_added"
        # debug_bot.log(log_name, update)
        # debug_bot.log(log_name, context)
        # return await update.message.reply_text("DMs are temporarily disabled! Come back soon!")

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
        # user_id, username = parse_user_data(user)
        first_name: int = try_get(user, "first_name") or try_get(chat, "first_name")
        user_id: int = try_get(user, "id")
        username: int = try_get(user, "username") or try_get(chat, "username")

        chat_id = try_get(chat, "id")
        new_message_dict = message.to_dict()
        chat_id_filter = {"id": chat_id}
        dm: TelegramDM = mongo_abbot.find_one_dm_and_update(
            chat_id_filter,
            {
                "$set": {"id": chat_id, "username": username, "type": chat_type},
                "$push": {
                    "messages": new_message_dict,
                    "history": {"role": "user", "content": f"@{username} said: {message_text} on {message_date}"},
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
        await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


async def handle_bot_kicked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: handle_bot_kicked"
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
        await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {abbot_exception}")


"""
async def handle_chat_migrated():
        => check for old chat doc
        => update old id -> new id
"""


async def handle_default_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_name: str = f"{FILE_NAME}: handle_default_group"
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
        debug_bot.log(log_name, f"user={user}")
        group_admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]
        # debug_bot.log(log_name, f"user={user}")
        chat_id_filter = {"id": chat_id}
        new_message_dict = message.to_dict()
        new_history_dict = {"role": "user", "content": f"@{username} said: {message_text} on {message_date}"}
        group_update = {
            "$set": {"title": chat_title, "id": chat_id, "type": chat_type, "admins": group_admins},
            "$push": {
                "messages": new_message_dict,
                "history": new_history_dict,
            },
        }
        # debug_bot.log(log_name, f"user={user}")
        group: TelegramGroup = mongo_abbot.find_one_group(chat_id_filter)
        # debug_bot.log(log_name, f"user={user}")
        # debug_bot.log(log_name, f"user={user}")
        if group:
            group_history: List = try_get(group, "history")
            # debug_bot.log(log_name, f"user={user}")
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
        else:
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

        group: TelegramGroup = mongo_abbot.find_one_group_and_update(chat_id_filter, group_update)
        group_id: int = try_get(group, "id")
        group_title: str = try_get(group, "title")
        msg = f"Existing group updated:\n\ngroup_id={group_id}\ngroup_title={group_title}"
        # debug_bot.log(log_name, f"user={user}")
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=msg)
    except AbbotException as abbot_exception:
        return await context.bot.send_message(
            chat_id=ABBOT_SQUAWKS, text=f"{log_name}: {THE_ARCHITECT_HANDLE} {abbot_exception}"
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    log_name: str = f"{FILE_NAME}: error_handler"

    exception = context.error
    formatted_traceback = "".join(traceback.format_exception(None, exception, exception.__traceback__))

    base_message = "Exception while handling Telegram update"
    base_message = f"{base_message}\n\tUpdate={update.to_dict()}\n\tContext={context}"
    base_message = f"{base_message}\n\n\tException: {exception}\n\n\tTraceback: {formatted_traceback}"
    # error_bot.log(log_name, base_message)

    error_bot.log(log_name, "Exception while handling update")
    update_dict = update.to_dict()
    error_bot.log(log_name, f"Update={dumps(update_dict, indent=4)}")

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
                MessageHandler(GROUPS & (NEW_CHAT_MEMBERS | CHAT_CREATED), handle_chat_creation_members_added),
                MessageHandler(UpdateFilter(GROUPS & MESSAGE_OR_EDITED), handle_edited),
            ]
        )

        telegram_bot.add_handlers(
            handlers=[
                CommandHandler("help", help),
                CommandHandler("rules", rules),
                CommandHandler("start", start),
                CommandHandler("stop", stop),
                CommandHandler("balance", balance),
                CommandHandler("fund", fund),
                CommandHandler("cancel", fund_cancel),
            ]
        )

        telegram_bot.add_handlers(
            handlers=[
                MessageHandler(PRIVATE, handle_dm),
                MessageHandler(GROUPS & FILTER_MENTION_ABBOT, handle_group_mention),
                MessageHandler(GROUPS & REPLY, handle_group_reply),
                MessageHandler(GROUPS & LEFT_CHAT_MEMEBERS, handle_bot_kicked),
                MessageHandler(GROUPS, handle_default_group),
            ]
        )
        telegram_bot.add_error_handler(error_handler)

        self.telegram_bot = telegram_bot

    def run(self):
        log_name: str = f"{FILE_NAME}: TelegramBotBuilder.run"
        debug_bot.log(log_name, f"Telegram abbot polling")
        self.telegram_bot.run_polling()
