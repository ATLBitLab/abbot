# core
import time
import uuid

from os.path import abspath
from datetime import datetime
from httpx import Response, AsyncClient

from lib.abbot.exceptions.exception import try_except

async_client: AsyncClient = AsyncClient(
    base_url="https://api.coinbase.com/v2",
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
    },
)
from typing import Dict, List, Optional, Tuple

from ..abbot.config import (
    BOT_CORE_SYSTEM_CHANNEL,
    BOT_CORE_SYSTEM_DM,
    BOT_NAME,
    BOT_TELEGRAM_HANDLE,
    ORG_INPUT_TOKEN_COST,
    ORG_OUTPUT_TOKEN_COST,
    ORG_PER_TOKEN_COST_DIV,
    ORG_TOKEN_COST_MULT,
)

# packages
from telegram import ChatMember, Update, Message, Chat, User
from telegram.constants import MessageEntityType, ParseMode
from telegram.ext import (
    CallbackContext,
    ContextTypes,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
)
from telegram.ext.filters import ChatType, StatusUpdate, Regex, Entity, REPLY, ALL

MARKDOWN_V2 = ParseMode.MARKDOWN_V2
MENTION = MessageEntityType.MENTION

GROUPS = ChatType.GROUPS
GROUP = ChatType.GROUP
PRIVATE = ChatType.PRIVATE

GROUP_CHAT_CREATED = StatusUpdate.CHAT_CREATED
NEW_GROUP_CHAT_MEMBERS = StatusUpdate.NEW_CHAT_MEMBERS
REGEX_BOT_TELEGRAM_HANDLE = Regex(BOT_TELEGRAM_HANDLE)

ENTITY_REPLY = Entity(REPLY)
ENTITY_MENTION = Entity(MENTION)


# local
from constants import HELP_MENU, INTRODUCTION, OPENAI_MODEL, RULES, SECONDARY_INTRODUCTION, THE_CREATOR
from ..logger import bot_debug, bot_error
from ..utils import error, qr_code, success, try_get, successful
from ..db.utils import successful_insert_one, successful_update_one
from ..db.mongo import TelegramDM, TelegramGroup, mongo_abbot
from ..abbot.core import Abbot
from ..abbot.utils import (
    parse_chat,
    parse_message,
    parse_user,
    squawk_error,
)
from ..payments import Strike, init_payment_processor

import tiktoken

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)
# constants
STRIKE: Strike = init_payment_processor()
FULL_TELEGRAM_HANDLE = f"@{BOT_TELEGRAM_HANDLE}"
RAW_MESSAGE_JL_FILE = abspath("src/data/raw_messages.jsonl")
MATRIX_IMG_FILEPATH = abspath("src/assets/unplugging_matrix.jpg")
KOOLAID_GIF_FILEPATH = abspath("src/assets/koolaid.gif")
DEFAULT_GROUP_HISTORY = [
    {"role": "system", "content": BOT_CORE_SYSTEM_CHANNEL},
    {"role": "assistant", "content": INTRODUCTION},
]


async def parse_update_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[Message, Chat, User]:
    response: Dict = parse_message(update, context)
    message: Message = try_get(response, "data")
    if not successful(response) or not message:
        return await squawk_error(message, context)

    response: Dict = parse_chat(message, context)
    chat: Chat = try_get(response, "data")
    if not successful(response) or not chat:
        error_message = try_get(message, "data")
        return await squawk_error(error_message, context)

    response: Dict = parse_user(message, context)
    user: User = try_get(response, "data")
    if not successful(response) or not user:
        return await squawk_error(user, context)

    return (message, chat, user)


def init_telegram_group_doc(chat: Chat, admins):
    return {
        "title": chat.title,
        "id": chat.id,
        "created_at": datetime.now(),
        "type": chat.type,
        "admins": list(admins),
        "balance": 50000,
        "message": [],
        "history": DEFAULT_GROUP_HISTORY,
        "config": {"started": False, "introduced": False, "unleashed": False, "count": None},
    }


def handle_insert_channel(chat: Chat, admins: Tuple[ChatMember]) -> Dict:
    group_doc: TelegramGroup = init_telegram_group_doc(chat, admins)
    insert = mongo_abbot.insert_one_channel(group_doc)
    if not successful_insert_one(insert):
        bot_error.log(__name__, f"handle_chat_creation_members_added => insert failed={insert}")
        return error("Insert new group doc success", data=insert)
    group: TelegramGroup = mongo_abbot.find_one_channel({"id": chat.id})
    return success("New group doc inserted", data=group)


@try_except
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, _, _ = update_data
    await message.reply_text(HELP_MENU)


@try_except
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, _, _ = update_data
    await message.reply_text(RULES)


@try_except
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, _ = update_data
    admins: Tuple[Dict] = [admin.to_dict() for admin in await chat.get_administrators()]
    group: TelegramGroup = mongo_abbot.find_one_channel({"id": chat.id})
    if not group:
        response: Dict = init_telegram_group_doc(chat, admins)
        if not successful(response):
            bot_error.log(__name__, f"Insert new channel fail")
            return await context.bot.send_message(chat_id=THE_CREATOR, text=response.get("message"))
        group: TelegramGroup = try_get(response, "data")
    started: Dict = try_get(group, "config", "started", default=False)
    bot_debug.log(__name__, f"started={started}")
    introduced: Dict = try_get(group, "config", "introduced", default=False)
    bot_debug.log(__name__, f"introduced={introduced}")
    current_balance: TelegramGroup = mongo_abbot.get_group_balance(chat.id)
    bot_debug.log(__name__, f"current_balance={current_balance}")
    if started:
        answer = f"{BOT_NAME} is already started for your group. Rules of engagement: {RULES}"
        if current_balance == 0:
            answer = f"{answer}. Note: Your group SATs balance is 0. Please run /fund to topup."
        return await message.reply_text(message)
    await message.reply_photo(MATRIX_IMG_FILEPATH, f"Please wait while {BOT_NAME} is unplugged from the Matrix")
    await message.reply_text(INTRODUCTION)
    update: TelegramGroup = mongo_abbot.find_one_channel_and_update(
        {"id": chat.id}, {"$set": {"config.started": True, "config.introduced": True}}
    )


@try_except
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, _ = update_data
    admins: Tuple[Dict] = [admin.to_dict() for admin in await chat.get_administrators()]
    group: TelegramGroup = mongo_abbot.find_one_channel({"id": chat.id})
    if not group:
        response: Dict = init_telegram_group_doc(chat, admins)
        if not successful(response):
            bot_error.log(__name__, f"Insert new channel fail")
            return await context.bot.send_message(chat_id=THE_CREATOR, text=response.get("message"))
        group: TelegramGroup = try_get(response, "data")
    started: Dict = try_get(group, "config", "started", default=False)
    bot_debug.log(__name__, f"started={started}")
    introduced: Dict = try_get(group, "config", "introduced", default=False)
    bot_debug.log(__name__, f"introduced={introduced}")
    current_balance: TelegramGroup = mongo_abbot.get_group_balance(chat.id)
    bot_debug.log(__name__, f"current_balance={current_balance}")
    if not started:
        return await message.reply_text(f"{BOT_NAME} is already stopped for your group. Please run /start to begin.")
    update: TelegramGroup = mongo_abbot.find_one_channel_and_update(
        {"id": chat.id}, {"$set": {"config.started": False}}
    )
    await message.reply_text("Thanks for using Abbot! Come back soon!")


@try_except
async def calculate_remaining_balance(input_token_count: int, output_token_count: int, current_group_balance: int):
    response: Response = await async_client.get("https://api.coinbase.com/v2/prices/BTC-USD/spot")
    data = response.json()
    data = try_get(data, "data")
    price_usd = float(try_get(data, "amount"))
    price_doc = {"_id": int(time.time()), **data, "amount": price_usd}
    mongo_abbot.insert_one_price(price_doc)
    cost_input_tokens = (input_token_count / ORG_PER_TOKEN_COST_DIV) * (ORG_INPUT_TOKEN_COST * ORG_TOKEN_COST_MULT)
    cost_output_tokens = (output_token_count / ORG_PER_TOKEN_COST_DIV) * (ORG_OUTPUT_TOKEN_COST * ORG_TOKEN_COST_MULT)
    total_token_cost_usd = cost_input_tokens + cost_output_tokens
    total_token_cost_sats = int((total_token_cost_usd / price_usd) * 100000000)
    if total_token_cost_sats > current_group_balance or current_group_balance == 0:
        return 0
    return current_group_balance - total_token_cost_sats


@try_except
async def handle_group_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, user = update_data
    bot_debug.log(__name__, f"{user.username} message tagged abbot in chat {chat.title} (chat_id={chat.id})")
    chat_id_filter = {"id": chat.id}
    history_message = {"role": "user", "content": message.text}
    bot_debug.log(__name__, f"message.text={message.text}")
    group_history: List = mongo_abbot.get_group_history(chat.id)
    bot_debug.log(__name__, f"group_history={group_history}")
    current_balance: TelegramGroup = mongo_abbot.get_group_balance(chat.id)
    if current_balance == 0:
        return await message.reply_text("NoFundsError: Your group SATs balance is 0. Please run /fund to topup.")
    if len(group_history) == 0:
        group: TelegramGroup = mongo_abbot.find_one_channel(chat_id_filter)
        bot_debug.log(__name__, f"group={group}")
        group_history: List = try_get(group, "history", default=[])
        bot_debug.log(__name__, f"group_history={group_history}")
    group_history.append(history_message)
    bot_debug.log(__name__, f"group_history={group_history}")
    abbot = Abbot(chat.id, "channel", group_history)
    answer, input_tokens, output_tokens, _ = abbot.chat_completion()
    new_balance: int = await calculate_remaining_balance(input_tokens, output_tokens, current_balance)
    group: TelegramGroup = mongo_abbot.find_one_channel_and_update(
        chat_id_filter,
        {
            "$push": {"messages": message.to_dict(), "history": {"role": "assistant", "content": answer}},
            "$set": {"balance": new_balance},
        },
    )
    bot_debug.log(__name__, f"group={group}")
    return await message.reply_text(answer)


@try_except
async def handle_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    bot_debug.log(__name__, f"=> handle_group_reply => update_data={update_data}")
    message, _, _ = update_data
    from_user: Optional[User] = try_get(message, "reply_to_message", "from_user")
    if from_user.is_bot and from_user.username == BOT_TELEGRAM_HANDLE:
        return await handle_group_mention(update, context)


@try_except
async def handle_chat_creation_members_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_debug.log(__name__, f"handle_chat_creation_members_added")
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, _ = update_data
    bot_debug.log(__name__, f"update_data={update_data}")
    abbot_added = False
    if not message.group_chat_created and message.new_chat_members:
        if BOT_TELEGRAM_HANDLE not in [user.username for user in message.new_chat_members]:
            return bot_debug.log(f"handle_chat_creation_members_added => abbot_added={abbot_added}")
    admins: Tuple[Dict] = [admin.to_dict() for admin in await chat.get_administrators()]
    bot_debug.log(__name__, f"admins={admins}")
    group: TelegramGroup = mongo_abbot.find_one_channel({"id": chat.id})
    bot_debug.log(__name__, f"group={group}")
    if not group:
        response: Dict = init_telegram_group_doc(chat, admins)
        if not successful(response):
            bot_error.log(__name__, f"Insert new channel fail")
            return await context.bot.send_message(chat_id=THE_CREATOR, text=response.get("message"))
        group: TelegramGroup = try_get(response, "data")
    introduced = try_get(group, "config", "introduced")
    if not introduced:
        print("not introduced", introduced)
        await message.reply_text(INTRODUCTION)
        update: TelegramGroup = mongo_abbot.find_one_channel_and_update(
            {"id": chat.id}, {"$set": {"config.introduced": True}}
        )
    else:
        await message.reply_animation(animation=KOOLAID_GIF_FILEPATH, caption=SECONDARY_INTRODUCTION)
        await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"{BOT_NAME} added to new group:\n\nTitle={chat.title}\nID={chat.id}"
        )


@try_except
async def handle_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_debug.log(__name__, f"handle_dm")
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, user = update_data
    dm: TelegramDM = mongo_abbot.find_one_dm({"id": chat.id})
    bot_debug.log(__name__, f"handle_dm => dm={dm}")
    history = [{"role": "user", "content": message.text}]
    if not dm:
        history = [{"role": "system", "content": BOT_CORE_SYSTEM_DM}, {"role": "user", "content": message.text}]
        bot_debug.log(__name__, f"if not dm")
        dm = mongo_abbot.insert_one_dm(
            {
                "id": chat.id,
                "username": message.from_user.username,
                "created_at": datetime.now(),
                "messages": [message.to_dict()],
                "history": history,
            }
        )
        if not successful_insert_one(dm):
            bot_error.log(__name__, f"handle_dm => insert dm failed={dm}")
        bot_debug.log(__name__, f"handle_dm => dm={dm}")
        dm = mongo_abbot.find_one_dm({"id": chat.id})
    bot_debug.log(__name__, f"handle_dm => dm={dm}")
    abbot = Abbot(chat.id, "dm", history)
    abbot.update_history_meta(message.text)
    bot_debug.log(__name__, f"chat_id={chat.id}, {user.username} dms with Abbot")
    answer, _, _, _ = abbot.chat_completion()
    return await message.reply_text(answer)


@try_except
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    bot_debug.log(__name__, f"update_data={update_data}")
    message, chat, _ = update_data
    channel: TelegramGroup = mongo_abbot.find_one_channel({"id": chat.id})
    if not channel:
        bot_error.log("balance => Not channel found")
    balance = try_get(channel, "balance")
    if not balance:
        bot_error.log("balance => balance is None")
    return await message.reply_text(f"⚡️ {chat.title} balance: {balance} sats ⚡️")


@try_except
async def fund_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    bot_debug.log(__name__, f"update_data={update_data}")
    message, chat, _ = update_data
    message_text: str = message.text
    bot_debug.log(__name__, f"message_text={message_text}")
    args = message_text.split()
    bot_debug.log(__name__, f"args={args}")
    invoice_id = try_get(args, 1) or STRIKE.CHAT_ID_INVOICE_ID_MAP.get(chat.id, None)
    if not invoice_id:
        return await message.reply_text("Invoice not found")
    bot_debug.log(__name__, f"invoice_id={invoice_id}")
    await message.reply_text("Attempting to cancel your invoice, please wait ...")
    bot_debug.log(__name__, f"STRIKE={STRIKE}")
    if not invoice_id:
        return await message.reply_text("No invoice exists")
    cancelled = await STRIKE.expire_invoice(invoice_id)
    if not cancelled:
        await context.bot.send_message(chat_id=THE_CREATOR, text=f"Error cancelling strike invoice {invoice_id}")
        return await message.reply_text(
            f"Error cancelling invoice {invoice_id}.\n"
            "Feel free to pay the ATL BitLab Lightning Address: atlbitlab@strike.me"
        )


@try_except
async def fund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    bot_debug.log(__name__, f"update_data={update_data}")
    message, chat, _ = update_data
    message_text: str = message.text
    bot_debug.log(__name__, f"message_text={message_text}")
    args = message_text.split()
    bot_debug.log(__name__, f"args={args}")
    if len(args) < 2:
        return await message.reply_text("Too few args: did you pass an amount of SATs?\ne.g. /fund 1000000")
    amount: int = int(try_get(args, 1))
    bot_debug.log(__name__, f"amount={amount}")
    await message.reply_text("Creating your invoice, please wait ...")
    bot_debug.log(__name__, f"STRIKE={STRIKE}")
    description = f"Account topup for {chat.title if chat.type == 'group' else chat.username}"
    cid = str(uuid.uuid1())
    bot_debug.log(__name__, f"description={description} cid={cid}")
    response = await STRIKE.get_invoice(cid, description, amount, chat.id)
    bot_debug.log(__name__, f"response={response}")
    if not response:
        await context.bot.send_message(chat_id=THE_CREATOR, text=f"Error creating strike invoice")
        return await message.reply_text(
            "InvoiceError: Try again or our alternative payment method at https://abbot.atlbitlab.com"
            "InvoiceError: If the error persists, contact @nonni_io for help"
        )
    invoice_id = try_get(response, "invoice_id")
    invoice = try_get(response, "lnInvoice")
    expirationInSec = try_get(response, "expirationInSec")
    if not invoice_id or not invoice or not expirationInSec:
        await context.bot.send_message(chat_id=THE_CREATOR, text=f"Error cancelling strike invoice {invoice_id}")
        return await message.reply_text("There was a problem generating the invoice. Contact @nonni_io for help.")
    await message.reply_photo(photo=qr_code(invoice), caption=description)
    await message.reply_markdown_v2(invoice)
    is_paid = False
    while expirationInSec >= 0 and not is_paid:
        bot_debug.log(__name__, f"expirationInSec={expirationInSec}")
        if expirationInSec == 0:
            bot_debug.log(__name__, f"expirationInSec == 0")
            cancelled = await STRIKE.expire_invoice(invoice_id)
            bot_debug.log(__name__, f"cancelled={cancelled}")
            if not cancelled:
                await context.bot.send_message(
                    chat_id=THE_CREATOR, text=f"Error cancelling strike invoice {invoice_id}"
                )
                return await message.reply_text(
                    f"Error cancelling invoice {invoice_id}.\nFeel free to pay the ATL BitLab Lightning Address: atlbitlab@strike.me"
                )
        is_paid = await STRIKE.invoice_is_paid(invoice_id)
        bot_debug.log(__name__, f"is_paid={is_paid}")
        expirationInSec -= 1
        time.sleep(1)
    if is_paid:
        channel: TelegramGroup = mongo_abbot.find_one_channel_and_update({"id": chat.id}, {"$inc": {"balance": amount}})
        if not successful_update_one(channel):
            bot_error.log(__name__, f"fund => find+update channel={channel}")
        balance: int = try_get(channel, "balance", default=amount)
        await message.reply_text(f"Invoice Paid! ⚡️ {chat.title} balance: {balance} sats ⚡️")
    else:
        await message.reply_text(f"Invoice expired! Please run {message.text} again.")


@try_except
async def handle_default(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_debug.log(__name__)
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    bot_debug.log(__name__, f"update_data={update_data}")
    _, chat, _ = update_data
    admins: Tuple[Dict] = [admin.to_dict() for admin in await chat.get_administrators()]
    group_filter = {"id": chat.id}
    group: TelegramGroup = mongo_abbot.find_one_channel(group_filter)
    if not group:
        bot_debug.log(__name__, "no group exists, adding initial group to DB")
        response: Dict = init_telegram_group_doc(chat, admins)
        if not successful(response):
            bot_error.log(__name__, f"Insert new channel fail")
            return await context.bot.send_message(chat_id=THE_CREATOR, text=response.get("message"))
        group: TelegramGroup = try_get(response, "data")
        bot_debug.log(__name__, f"group={group}")
        return await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"{BOT_NAME} added to new group:\n\nTitle={chat.title}\nID={chat.id}"
        )
    group: TelegramGroup = mongo_abbot.find_one_channel_and_update(
        {"id": chat.id}, {"$set": {"config.started": True, "config.introduced": True}}
    )
    bot_debug.log(__name__, f"update_data={update_data}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    base_message = "Exception while handling Telegram update"
    update_d = {**update}
    context_d = {**context}
    error_message = f"{base_message}\n\tUpdate={update_d}\n\tContext={context_d}"
    bot_error.log(__name__, error_message)
    await context.bot.send_message(chat_id=THE_CREATOR, text=f"{__name__}: {error_message}")


class TelegramBotBuilder:
    from lib.abbot.config import BOT_TELEGRAM_TOKEN

    def __init__(self):
        bot_debug.log(__name__, f"Telegram abbot initializing: name={BOT_NAME} handle={FULL_TELEGRAM_HANDLE}")
        telegram_bot = ApplicationBuilder().token(self.BOT_TELEGRAM_TOKEN).build()
        bot_debug.log(__name__, f"Telegram abbot initialized")

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
                MessageHandler(GROUPS & ENTITY_MENTION & REGEX_BOT_TELEGRAM_HANDLE, handle_group_mention),
                MessageHandler(GROUPS & REPLY, handle_group_reply),
                MessageHandler(GROUPS, handle_default),
            ]
        )

        telegram_bot.add_error_handler(error_handler)

        self.telegram_bot = telegram_bot

    def run(self):
        bot_debug.log(__name__, f"Telegram abbot polling")
        self.telegram_bot.run_polling()
