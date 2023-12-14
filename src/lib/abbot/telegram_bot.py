# core
import json
import time
import uuid
import traceback

from os.path import abspath
from datetime import datetime

from typing import Any, Dict, List, Optional, Tuple

from bson import json_util
from pymongo.results import InsertOneResult

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
    BOT_LIGHTNING_ADDRESS,
    BOT_SYSTEM_CORE_DMS,
    BOT_SYSTEM_CORE_GROUPS,
    BOT_NAME,
    BOT_TELEGRAM_HANDLE,
    BOT_TELEGRAM_SUPPORT_CONTACT,
    ORG_INPUT_TOKEN_COST,
    ORG_OUTPUT_TOKEN_COST,
    ORG_PER_TOKEN_COST_DIV,
    ORG_TOKEN_COST_MULT,
)

FULL_TELEGRAM_HANDLE = f"@{BOT_TELEGRAM_HANDLE}"
RAW_MESSAGE_JL_FILE = abspath("src/data/raw_messages.jsonl")
MATRIX_IMG_FILEPATH = abspath("src/assets/unplugging_matrix.jpg")
KOOLAID_GIF_FILEPATH = abspath("src/assets/koolaid.gif")
DEFAULT_GROUP_HISTORY = [{"role": "system", "content": BOT_SYSTEM_CORE_GROUPS}]
DEFAULT_DM_HISTORY = [{"role": "system", "content": BOT_SYSTEM_CORE_DMS}]

# packages
from telegram import ChatMember, Update, Message, Chat, User
from telegram.constants import MessageEntityType, ParseMode
from telegram.ext import (
    ContextTypes,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
)
from telegram.ext.filters import ChatType, StatusUpdate, Regex, Entity, REPLY, Mention

MARKDOWN_V2 = ParseMode.MARKDOWN_V2
MENTION = MessageEntityType.MENTION

GROUPS = ChatType.GROUPS
GROUP = ChatType.GROUP
PRIVATE = ChatType.PRIVATE

GROUP_CHAT_CREATED = StatusUpdate.CHAT_CREATED
NEW_GROUP_CHAT_MEMBERS = StatusUpdate.NEW_CHAT_MEMBERS
LEFT_GROUP_CHAT_MEMEBERS = StatusUpdate.LEFT_CHAT_MEMBER
REGEX_BOT_TELEGRAM_HANDLE = Regex(BOT_TELEGRAM_HANDLE)
FILTER_MENTION_ABBOT = Mention(FULL_TELEGRAM_HANDLE)
ENTITY_MENTION = Entity(MENTION)

# local
from ..logger import debug_bot, error_bot
from ..utils import error, qr_code, success, try_get, successful
from ..db.utils import successful_insert_one, successful_update_one
from ..db.mongo import TelegramDM, TelegramGroup, mongo_abbot
from ..abbot.core import Abbot
from ..abbot.utils import (
    parse_chat,
    parse_chat_data,
    parse_message,
    parse_message_data,
    parse_message_data_keys,
    parse_user,
    parse_user_data,
    squawk_error,
)
from ..abbot.exceptions.exception import try_except, try_except_raise
from ..payments import Coinbase, CoinbasePrice, Strike, init_payment_processor, init_price_provider

strike: Strike = init_payment_processor()
price_provider: Coinbase = init_price_provider()

import tiktoken

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)


def usd_to_sats(usd_amount: int):
    btc_price = mongo_abbot.find_prices()[-1]
    return (usd_amount / btc_price) * SATOSHIS_PER_BTC


def sats_to_usd(sats_amount: int):
    btc_price = mongo_abbot.find_prices()[-1]
    return (sats_amount / SATOSHIS_PER_BTC) * btc_price


async def parse_update_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Dict:
    log_name: str = f"{__name__}: parse_update_data"

    response: Dict = parse_message(update, context)
    if not successful(response):
        error_message: str = try_get(response, "data")
        error_bot.log(log_name, f"parse_message failed:\n\nresponse={response}\nerror_message={error_message}")
        await squawk_error(error_message, context)
        error_bot.log(log_name, f"parse_message failed:\n\nerror_message={error_message}")
        return error(f"Parse message from update failed: {error_message}", data=message)

    message: Message = try_get(response, "data")

    response: Dict = parse_chat(message, context)
    chat: Chat = try_get(response, "data")
    if not successful(response):
        error_message = try_get(chat, "data")
        error_bot.log(log_name, f"parse_chat failed:\n\nresponse={response}\nmessage={message}")
        await squawk_error(error_message, context)
        error_bot.log(log_name, f"parse_chat failed:\n\nerror_message={error_message}")
        return error(f"Failed to parse chat from update: {error_message}", data=chat)

    response: Dict = parse_user(message, context)
    user: User = try_get(response, "data")
    if not successful(response):
        error_message = try_get(chat, "data")
        error_bot.log(log_name, f"parse_user failed:\n\nresponse={response}\nmessage={message}")
        await squawk_error(user, context)
        error_bot.log(log_name, f"parse_user failed:\n\nerror_message={error_message}")
        return error(f"Failed to parse user from update: {error_message}", data=user)

    return success("Parse update success", message=message, chat=chat, user=user)


async def balance_remaining(input_token_count: int, output_token_count: int, current_group_balance: int):
    log_name: str = f"{__name__}: balance_remaining"

    response: Dict[CoinbasePrice] = price_provider.get_bitcoin_price()
    debug_bot.log(log_name, f"response={response}")
    data = try_get(response, "data")
    amount = try_get(data, "amount")
    if not data or not amount:
        error_bot.log(log_name, f"response={response}")
        error_message = try_get(response, "msg")
        error_data = try_get(response, "data")
        error_bot.log(log_name, f"error_message={error_message}\nerror_data={error_data}")
        return error(error_message, data=error_data)
    debug_bot.log(log_name, f"data={data}\namount={amount}")

    price_usd = float(amount)
    mongo_abbot.insert_one_price(data)
    cost_input_tokens = (input_token_count / ORG_PER_TOKEN_COST_DIV) * (ORG_INPUT_TOKEN_COST * ORG_TOKEN_COST_MULT)
    cost_output_tokens = (output_token_count / ORG_PER_TOKEN_COST_DIV) * (ORG_OUTPUT_TOKEN_COST * ORG_TOKEN_COST_MULT)
    total_token_cost_usd = cost_input_tokens + cost_output_tokens
    total_token_cost_sats = (total_token_cost_usd / price_usd) * SATOSHIS_PER_BTC
    if total_token_cost_sats > current_group_balance or current_group_balance == 0:
        return 0
    remaining_balance = current_group_balance - total_token_cost_sats
    return success("Success calculate remaining balance", data=remaining_balance)


def create_telegram_group_doc(message: Message, chat: Chat, admins: Tuple[ChatMember]) -> Dict:
    log_name: str = f"{__name__}: create_telegram_group_doc: "
    debug_bot.log(log_name, f"creating doc for chat.id={chat.id}")
    return {
        "title": chat.title,
        "id": chat.id,
        "created_at": datetime.now().isoformat(),
        "type": chat.type,
        "admins": list(admins),
        "balance": 50000,
        "messages": [message.to_dict()],
        "history": DEFAULT_GROUP_HISTORY,
        "config": {"started": False, "introduced": False, "unleashed": False, "count": None},
    }


def update_telegram_group_doc(existing: Dict, update: Dict) -> Dict:
    log_name: str = f"{__name__}: update_telegram_group_doc"

    chat_id = try_get(existing, "id")
    doc_filter = {"id": chat_id}

    updates = {}
    for key, value in update.items():
        if existing.get(key) != value:
            updates[key] = value

    group: TelegramGroup = mongo_abbot.update_one_group(doc_filter, {"$set": updates})
    if not successful_update_one(group):
        error_bot.log(log_name, f"Failed to update group doc")
        return error("Failed to update group doc", data=group)
    group: TelegramGroup = mongo_abbot.find_one_group(doc_filter)
    if not group:
        error_bot.log(log_name, f"")
        return error("Failed to update group doc", data=group)
    object_id = try_get(group, "_id")
    if object_id:
        group = {**group, "_id": str(object_id)}
    created_at = try_get(group, "created_at")
    if created_at and type(created_at) == datetime:
        group = {**group, "created_at": json_util.dumps(created_at)}
    return success("Success update group doc", data=group)


def handle_insert_group(message: Message, chat: Chat, admins: Tuple[ChatMember]) -> Dict:
    log_name: str = f"{__name__}: handle_insert_group"
    group_doc: TelegramGroup = create_telegram_group_doc(message, chat, admins)
    insert: InsertOneResult = mongo_abbot.insert_one_group(group_doc)
    if not successful_insert_one(insert):
        error_bot.log(log_name, f"insert={insert}")
        return error(f"Insert new group doc failed", data=insert)
    group: TelegramGroup = mongo_abbot.find_one_group({"id": chat.id})
    return success("New group doc inserted", data=group)


@try_except
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_name: str = f"{__name__}: help"

    update_data: Dict = await parse_update_data(update, context)
    debug_bot.log(log_name, f"update_data={update_data}")

    message: Message = try_get(update_data, "message")
    # chat: Chat = try_get(update_data, "chat")
    # user: User = try_get(update_data, "user")

    await message.reply_text(HELP_MENU)


@try_except
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_name: str = f"{__name__}: rules"

    update_data: Dict = await parse_update_data(update, context)
    debug_bot.log(log_name, f"update_data={update_data}")

    message: Message = try_get(update_data, "message")
    # chat: Chat = try_get(update_data, "chat")
    # user: User = try_get(update_data, "user")

    await message.reply_text(RULES)


@try_except
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_name: str = f"{__name__}: start"

    update_data: Dict = await parse_update_data(update, context)
    debug_bot.log(log_name, f"update_data={update_data}")

    message: Message = try_get(update_data, "message")
    chat: Chat = try_get(update_data, "chat")

    admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]
    group: TelegramGroup = mongo_abbot.find_one_group_and_update(
        {"id": chat.id},
        {
            "$setOnInsert": {
                "created_at": datetime.now().isoformat(),
                "balance": 50000,
                "history": DEFAULT_GROUP_HISTORY,
            },
            "$push": {
                "messages": message.to_dict(),
                "history": {
                    "$each": [
                        {"role": "assistant", "content": f"Please wait while {BOT_NAME} is unplugged from the Matrix"},
                        {"role": "assistant", "content": INTRODUCTION},
                    ]
                },
            },
            "$set": {"title": chat.title, "id": chat.id, "type": chat.type, "admins": admins},
        },
    )
    # mongo_abbot.find_one_dm(
    #     {
    #         "id": chat.id,
    #         "history": {
    #             "$elemMatch": {"role": "user", "content": {"$in": ["/start", f"/start@{BOT_TELEGRAM_HANDLE}"]}}
    #         },
    #     }
    # )
    started: Dict = try_get(group, "config", "started", default=False)
    debug_bot.log(log_name, f"started={started}")

    introduced: Dict = try_get(group, "config", "introduced", default=False)
    debug_bot.log(log_name, f"introduced={introduced}")

    current_balance: TelegramGroup = mongo_abbot.get_group_balance(chat.id)
    if current_balance == 0:
        await message.reply_text("Note: Group balance is 0 sats. Please run /fund to topup (e.g. /fund 50000 sats).")
    debug_bot.log(log_name, f"current_balance={current_balance}")

    if started:
        answer = f"{BOT_NAME} already started for your group. Rules of engagement: {RULES}"
        if current_balance == 0:
            answer = f"{answer}. Wallet Balance: 0 sats. Please run /fund <amount_in_sats> to topup (e.g. /fund 50000)."
        debug_bot.log(log_name, f"answer={answer}")
        return await message.reply_text(answer)

    await message.reply_photo(MATRIX_IMG_FILEPATH, f"Please wait while {BOT_NAME} is unplugged from the Matrix")
    time.sleep(5)

    group: TelegramGroup = mongo_abbot.find_one_group_and_update(
        {"id": chat.id},
        {
            "$set": {"config.started": True, "config.introduced": True},
        },
    )

    return await message.reply_text(INTRODUCTION)


@try_except
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_name: str = f"{__name__}: stop"

    update_data: Dict = await parse_update_data(update, context)
    debug_bot.log(log_name, f"update_data={update_data}")

    message: Message = try_get(update_data, "message")
    chat: Chat = try_get(update_data, "chat")

    admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]
    group: TelegramGroup = mongo_abbot.find_one_group({"id": chat.id})
    if not group:
        response: Dict = handle_insert_group(message, chat, admins)
        if not successful(response):
            error_bot.log(log_name, f"response={response}")
            msg = f"{log_name}: Failed to insert group: handle_insert_group.response={response}"
            return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=msg)
        group: TelegramGroup = try_get(response, "data")

    started: Dict = try_get(group, "config", "started", default=False)
    debug_bot.log(log_name, f"started={started}")

    if not started:
        return await message.reply_text(f"{BOT_NAME} already stopped for your group. Please run /start to begin.")

    group: TelegramGroup = mongo_abbot.find_one_group_and_update({"id": chat.id}, {"$set": {"config.started": False}})
    error_bot.log(log_name, f"group={group}")
    if not group:
        error_bot.log(log_name, f"not group")
        return await context.bot.send_message(
            chat_id=THE_CREATOR,
            text=f"{log_name}: find & update group fail: chat.id={chat.id} chat.title={chat.title}",
        )
    await message.reply_text("Thanks for using Abbot! Come back soon!")


@try_except
async def handle_group_mention(update: Update, context: ContextTypes.DEFAULT_TYPE, reply=False):
    fn = "handle_group_reply" if reply else "handle_group_mention"
    log_name: str = f"{__name__}: {fn}"

    update_data: Dict = await parse_update_data(update, context)
    debug_bot.log(log_name, f"update_data={update_data}")

    message: Message = try_get(update_data, "message")
    chat: Chat = try_get(update_data, "chat")
    user: User = try_get(update_data, "user")
    debug_bot.log(log_name, f"{user.username} message tagged abbot in chat {chat.title} (chat_id={chat.id})")

    chat_id_filter = {"id": chat.id}
    admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]
    group: TelegramGroup = mongo_abbot.find_one_group_and_update(
        chat_id_filter,
        {
            "$setOnInsert": {"created_at": datetime.now().isoformat()},
            "$push": {"messages": message.to_dict(), "history": {"$each": group_history}},
            "$set": {
                "title": chat.title,
                "id": chat.id,
                "type": chat.type,
                "admins": admins,
                "balance": new_balance,
                "history": DEFAULT_GROUP_HISTORY,
                "config": {"started": False, "introduced": False, "unleashed": False, "count": None},
            },
        },
    )
    current_balance: TelegramGroup = mongo_abbot.get_group_balance(chat_id_filter)
    if current_balance == 0:
        return await message.reply_text("No Funds: Your wallet is empty. Please run /fund to topup.")
    group_history: List = mongo_abbot.get_group_history(chat_id_filter)
    debug_bot.log(log_name, f"group_history={group_history[-1]}")

    group_history.append({"role": "user", "content": f"{chat.username} said: {message.text} on {message.date}"})
    debug_bot.log(log_name, f"group_history={group_history[-1]}")

    abbot = Abbot(chat.id, "group", group_history)
    answer, input_tokens, output_tokens, _ = abbot.chat_completion()

    response: Dict = await balance_remaining(input_tokens, output_tokens, current_balance)
    if not successful(response):
        error_bot.log(log_name, f"response={response}")
        msg = f"{log_name}: Failed to calculate balance:"
        msg = f"{msg} balance_remaining.response={response}\nchat=(id={chat.id}, title=({chat.title})"
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=msg)
    new_balance: int = try_get(response, "data", default=0)
    error_bot.log(log_name, f"new_balance={new_balance}")
    group: TelegramGroup = mongo_abbot.find_one_group_and_update(
        chat_id_filter,
        {
            "$push": {"messages": message.to_dict(), "history": {"$each": group_history}},
            "$set": {"balance": new_balance},
        },
    )
    debug_bot.log(log_name, f"group={group}")
    if not group:
        error_bot.log(log_name, f"not group")
        return await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"{log_name}: find & update group fail: chat.id={chat.id} chat.title={chat.title}"
        )

    return await message.reply_text(answer)


@try_except
async def handle_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_name: str = f"{__name__}: handle_group_reply: "

    update_data: Dict = await parse_update_data(update, context)
    debug_bot.log(log_name, f"update_data={update_data}")

    message: Message = try_get(update_data, "message")
    chat: Chat = try_get(update_data, "chat")
    user: User = try_get(update_data, "user")

    from_user: Optional[User] = try_get(message, "reply_to_message", "from_user")
    if from_user.is_bot and from_user.username == BOT_TELEGRAM_HANDLE:
        return await handle_group_mention(update, context, reply=True)


@try_except
async def handle_chat_creation_members_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_name: str = f"{__name__}: handle_chat_creation_members_added"
    update_data: Dict = await parse_update_data(update, context)
    debug_bot.log(log_name, f"update_data={update_data}")

    message: Message = try_get(update_data, "message")
    message_text, message_date = parse_message_data(message)
    
    message_data: Dict = parse_message_data_keys(message, keys=["group_chat_created", "new_chat_members"])
    group_chat_created = message_data.get("group_chat_created", None)
    new_chat_members = message_data.get("new_chat_members", None)

    chat: Chat = try_get(update_data, "chat")
    chat_id, chat_title, chat_type = parse_chat_data(chat)
    
    user: User = try_get(update_data, "user")
    username, _ = parse_user_data(user)
    
    admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]
    debug_bot.log(log_name, f"admins={admins}")

    if not group_chat_created and new_chat_members:
        if BOT_TELEGRAM_HANDLE not in [username for username in new_chat_members]:
            return debug_bot.log(log_name, "Abbot not added to group")
    
    new_history_obj: Dict = {"role": "user", "content": f"{username} said: {message_text} on {message_date}"}
    group: TelegramGroup = mongo_abbot.find_one_group_and_update(
        {"id": chat_id},
        {
            "$set": {"id": chat_id, "title": chat_title, "type": chat_type, "admins": admins},
            "$push": {
                "messages": message.to_dict(),
                "history": {"role": "user", "content": f"{username} said: {message_text} on {message_date}"}
            },
            "$setOnInsert": {
                "created_at": datetime.now().isoformat(),
                "balance": 50000,
                "history": [*DEFAULT_GROUP_HISTORY, new_history_obj],
            },
        })
    debug_bot.log(log_name, f"group={group}")
    group_title: str = try_get(group, "title")
    group_id: str = try_get(group, "id")
    return await context.bot.send_message(
        chat_id=ABBOT_SQUAWKS, text=f"{log_name}: Abbot added to new group: title={group_title}, id={group_id})"
    )


@try_except
async def handle_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_name: str = f"{__name__}: handle_chat_creation_members_added"

    update_data: Dict = await parse_update_data(update, context)
    debug_bot.log(log_name, f"update_data={update_data}")

    message: Message = try_get(update_data, "message")
    message_text, message_date = parse_message_data(message)
    
    chat: Chat = try_get(update_data, "chat")
    chat_id, _, chat_type = parse_chat_data(chat)
    
    user: User = try_get(update_data, "user")
    username, _ = parse_user_data(user)
    if not username:
        username = try_get(chat, "username")

    chat_id = try_get(chat, "id")
    dm: TelegramDM = mongo_abbot.find_one_dm_and_update(
        {"id": chat_id},
        {
            "$set": {"id": chat_id, "username": username, "type": chat_type},
            "$push": {
                "messages": message.to_dict(),
                "history": {
                    "$each": [*DEFAULT_DM_HISTORY, {"role": "user", "content": f"{username} said: {message_text} on {message_date}"}]
                },
            },
            "$setOnInsert": {"created_at": datetime.now().isoformat()},
        },
    )

    debug_bot.log(log_name, f"handle_dm => found or inserted chat=(id={chat.id}, user=({user.username}")
    dm_msg = f"dm={dm}\nchat=(id={chat.id}, title=({chat.title})"
    await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=dm_msg)

    dm_history: List = try_get(dm, "history")
    debug_bot.log(log_name, f"dm_history={dm_history[-1]}")

    abbot = Abbot(chat.id, "dm", dm_history)
    answer, _, _, _ = abbot.chat_completion()
    dm: TelegramDM = mongo_abbot.find_one_group_and_update(
        {"id": chat.id},
        {"$push": {"history": {"role": "assistant", "content": answer}}},
    )
    debug_bot.log(log_name, f"{dm_msg}\nAbbot DMs with {user.username}")
    return await message.reply_text(answer)


@try_except
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_name: str = f"{__name__}: balance"
    update_data: Dict = await parse_update_data(update, context)
    debug_bot.log(log_name, f"update_data={update_data}")
    message: Message = try_get(update_data, "message")
    chat: Chat = try_get(update_data, "chat")
    group: TelegramGroup = mongo_abbot.find_one_group({"id": chat.id})
    sats_balance = try_get(group, "balance", default=0)
    usd_balance = sats_to_usd(int(sats_balance))
    group_msg = f"⚡️ Group: {chat.title} ⚡️ "
    sats_balance_msg = f"⚡️ SAT Balance: {sats_balance} ⚡️"
    usd_balance_msg = f"💰 USD Balance: {usd_balance} 💰"
    return await message.reply_text(f"{group_msg} \n {sats_balance_msg} \n {usd_balance_msg}")


@try_except
async def fund_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_name: str = f"{__name__}: fund_cancel"

    update_data: Dict = await parse_update_data(update, context)
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
    cancel_fail = "Failed to cancel invoice. Try again or pay abbot@atlbitlab.com & contact @nonni_io for confirmation"
    cancelled = await strike.expire_invoice(invoice_id)
    if not cancelled:
        await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=cancel_squawk)
        return await message.reply_text(cancel_fail)

    await message.reply_text(f"Invoice id {invoice_id} successfully cancelled for {chat_title}")


@try_except
async def fund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_name: str = f"{__name__}: fund"

    update_data: Dict = await parse_update_data(update, context)
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
    invoice_error_args = "InvoiceError: Missing amount and currency unit. Did you pass an amount and a currency unit?"
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


@try_except
async def handle_bot_kicked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_name: str = f"{__name__}: handle_bot_kicked"
    update_data: Dict = await parse_update_data(update, context)
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


@try_except
async def handle_default_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_name: str = f"{__name__}: handle_default_group"
    update_data: Dict = await parse_update_data(update, context)
    debug_bot.log(log_name, f"update_data={update_data}")

    message: Message = try_get(update_data, "message")
    message_text, message_date: Dict = parse_message_data(chat)
    
    chat: Chat = try_get(update_data, "chat")
    chat_id, chat_title, chat_type = parse_chat_data(chat)
    
    user: User = try_get(update_data, "user")
    _, username = parse_user_data(user)
    
    username: str = try_get(chat, "username") or try_get(user, "username")
    admins: Any = [admin.to_dict() for admin in await chat.get_administrators()]
    
    group: TelegramGroup = mongo_abbot.find_one_group_and_update(
        {"id": chat_id},
        {
            "$setOnInsert": {
                "created_at": datetime.now().isoformat(),
                "balance": 50000,
                "history": DEFAULT_GROUP_HISTORY,
            },
            "$set": {"title": chat_title, "id": chat_id, "type": chat_type, "admins": admins},
            "$push": {
                "messages": message.to_dict(),
                "history": {
                    "$each": [
                        {"role": "user", "content": f"{username} said: {message_text} on {message_date}"}
                    ]
                },
            },
        },
    )
    group_id: int = try_get(group, "id")
    group_title: str = try_get(group, "title")
    group_history: List = try_get(group, "history")
    if not group:
        no_group_squawk = f"No group exists or created: group.id={chat.id}"
        debug_bot.log(log_name, no_group_squawk)
        return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=no_group_squawk)
    msg = f"Existing group updated:\n\ngroup_id={group_id}\ngroup_title={group_title}\nmessage={group_history[-1]}"
    return await context.bot.send_message(chat_id=ABBOT_SQUAWKS, text=msg)


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
        log_name: str = f"{__name__}: TelegramBotBuilder.__init__"
        debug_bot.log(log_name, f"Telegram abbot initializing: name={BOT_NAME} handle={FULL_TELEGRAM_HANDLE}")
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
