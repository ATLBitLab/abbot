# core
import time
import uuid

from os.path import abspath
from typing import Dict, Tuple

# packages
from telegram import Update, Message, Chat, User
from telegram.constants import MessageEntityType
from telegram.ext import (
    CallbackContext,
    ContextTypes,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
)
from telegram.ext.filters import ChatType, Regex, Entity, REPLY

# local
from constants import HELP_MENU, THE_CREATOR
from ..logger import bot_debug, bot_error
from ..utils import sender_is_group_admin, try_get, successful
from ..db.utils import successful_insert_one
from ..db.mongo import MongoTelegramDocument, mongo_abbot
from ..abbot.core import Abbot
from ..abbot.exceptions.exception import try_except
from ..abbot.config import BOT_NAME, BOT_TELEGRAM_HANDLE
from ..abbot.utils import (
    parse_chat,
    parse_message,
    parse_user,
    squawk_error,
)
from ..admin.admin_service import AdminService

import tiktoken

encoding = tiktoken.encoding_for_model(OPENAI_MODEL)
# constants
STRIKE: Strike = init_payment_processor()
FULL_TELEGRAM_HANDLE = f"@{BOT_TELEGRAM_HANDLE}"
MENTION = MessageEntityType.MENTION
ENTITY_REPLY = Entity(REPLY)

RAW_MESSAGE_JL_FILE = abspath("src/data/raw_messages.jsonl")
MATRIX_IMG_FILEPATH = abspath("src/assets/unplugging_matrix.jpg")
KOOLAID_GIF_FILEPATH = abspath("src/assets/koolaid.gif")
DEFAULT_GROUP_HISTORY = [
    {"role": "system", "content": BOT_CORE_SYSTEM_CHANNEL},
    {"role": "assistant", "content": INTRODUCTION},
]


@try_except
async def parse_message_chat_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[Message, Chat, User]:
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


@try_except
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fn = "handle_text_message:"
    if not update or not context:
        return bot_error.log(f"{fn} No update or context")

    bot_debug.log(f"{fn} Update={update}")
    bot_debug.log(f"{fn} Context={context}")

    response: Dict = parse_message(update, context)
    message: Message = try_get(response, "data")
    if not successful(response):
        return await squawk_error(message, context)

    response: Dict = parse_chat(message, context)
    chat: Chat = try_get(response, "data")
    if not successful(response):
        error_message = try_get(message, "data")
        return await squawk_error(error_message, context)
    chat_data: Dict = parse_chat_data(chat)
    chat_id: int = try_get(chat_data, "id")
    chat_type: str = try_get(chat_data, "type")
    is_private_chat: bool = chat_type == "private"
    is_group_chat: bool = not is_private_chat
    chat_title: str = try_get(chat_data, "title", default="private" if is_private_chat else None)
    response: Dict = parse_user(message, context)
    user: User = try_get(response, "data")
    if not successful(response):
        return await squawk_error(user, context)
    user_data: Dict = parse_user_data(user)
    user_id: int = try_get(user_data, "user_id")

    # log all data for debugging
    abbot_context = "group"

    all_data: Dict = dict(**message_data, **chat_data, **user_data)
    for k, v in all_data.items():
        bot_debug.log(f"{fn} {k}={v}")

    abbot_message = dict(role="user", content=message_text)
    if is_group_chat and "test" not in BOT_TELEGRAM_HANDLE:
        bot_debug.log(f"{fn} is_group_chat={is_group_chat}")
        bot_debug.log(f"{fn} test not in BOT_TELEGRAM_HANDLE={BOT_TELEGRAM_HANDLE}")
        message_dump = json.dumps(
            {"message": {**message_data}, "chat": {**chat_data}, "user": {**user_data}, "abbot": abbot_message}
        )
        bot_debug.log(f"{fn} message_dump={message_dump}")
        raw_messages_jsonl = open(RAW_MESSAGE_JL_FILE, "a")
        raw_messages_jsonl.write(message_dump)
        raw_messages_jsonl.write("\n")
        raw_messages_jsonl.close()
    else:
        abbot_context = "private"
        bot_debug.log(f"{fn} is_private_chat={is_private_chat}")
    bot_debug.log(f"{fn} abbot_context={abbot_context}")

    abbot = Abbot(chat_id)

    # not_introduced: bool = abbot.is_forgotten()
    # if not_introduced:
    #     debug. log(f"{fn} Abbot not introduced!")
    #     abbot.introduce()
    #     introduced = abbot.is_introduced()
    #     debug. log(f"introduced={introduced}")
    #     abbots.update_abbots(chat_id, abbot)
    #     return await message.reply_text(
    #         "Thank you for talking to Abbot (@atl_bitlab_bot), a bitcoiner bot for bitcoin communities, by the Atlanta Bitcoin community!\n\n"
    #         "Abbot is meant to provide education to local bitcoin communities and help community organizers with various tasks.\n\n"
    #         "To start Abbot in a group chat, have a channel admin run /start\n"
    #         "To start Abbot in a DM, simply run /start.\n\n"
    #         "By running /start, you agree to our Terms & policies: https://atlbitlab.com/abbot/policies.\n\n"
    #         "If you have multiple bots in one channel, you may need to run /start@atl_bitlab_bot to avoid bot confusion!\n\n"
    #         "If you have questions, concerns, feature requests or find bugs, please contact @nonni_io or @ATLBitLab on Telegram."
    #     )

    # not_started: bool = abbot.is_stopped()
    # if not_started:
    #     debug. log(f"{fn} Abbot introduced!")
    #     debug. log(f"{fn} Abbot not started!")
    #     return

    message_reply = try_get(message, "reply_to_message")
    message_reply_text = try_get(message_reply, "text")
    message_reply_from = try_get(message_reply, "from")
    if is_private_chat:
        abbot.update_chat_history(abbot_message)
        bot_debug.log(f"{fn} is private, not group_in_name")
        answer = abbot.chat_history_completion()
    else:
        chat_history_len: int = abbot.chat_history_len
        is_unleashed, count = abbot.is_unleashed()
        bot_debug.log(f"{fn} group_in_name: name={abbot.name}")
        if handle not in message_text and handle not in message_reply_text:
            bot_debug.log(f"{fn} handle not in message_text or message_reply_text")
            return
        if not replied_to_abbot:
            bot_debug.log(f"{fn} not replied_to_abbot!")
            return
        if not is_unleashed or not count:
            bot_debug.log(f"{fn} not is_unleashed or not count")
            return
        if chat_history_len % count != 0:
            bot_debug.log(f"{fn} chat_history_len % count != 0!")
            return
        bot_debug.log(f"{fn} All checks passed!")
        answer = abbot.chat_history_completion()
    # if not answer:
    #     await context.bot.send_message(
    #         chat_id=THE_CREATOR,
    #         text=f"{abbot.name} completion failed ⛔️: abbot={abbot} answer={answer}",
    #     )
    # i = 0
    # while not answer and i < 5:
    #     abbot.sleep(10)
    #     answer = abbot.chat_history_completion()
    #     debug. log(f"{fn} answer={answer}")
    #     if answer:
    #         continue
    #     i += 1
    # if not answer:
    #     return await context.bot.send_message(
    #         chat_id=user_id, text="Sorry, I seem to have bugged out bug 🐜 please contact @nonni_io for help."
    #     )
    return await message.reply_text(answer)


@try_except
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, _, _ = update_data
    await message.reply_text(HELP_MENU)


@try_except
async def unleash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, user = update_data
    pass
    # TODO: finish this logic
    # if abbot.is_stopped():
    #     return await message.reply_text(f"I'm already stopped for {chat_title}! Please run /start to begin!")
    # unleashed, count = abbot.is_unleashed()
    # if unleashed:
    #     return await message.reply_text(f"I'm already unleashed for {chat_title}! To leash me, please run /leash!")

    # abbot.unleash()
    # unleashed, count = abbot.is_unleashed()
    # bot_debug.log(f"{fn} {abbot} unleashed={unleashed}")
    # return await message.reply_text(
    #     f"I have been unleashed! I will now respond every {count} messages until"
    #     "you run /leash or /unleash <insert_new_number> (e.g. /unleash 10)"
    # )


@try_except
async def leash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, user = update_data
    pass
    # TODO: finish this logic
    # abbot: Abbot = Abbot(chat_id)
    # if abbot.is_stopped():
    #     return await message.reply_text(f"I'm already stopped for {chat_title}! Please run /start to begin!")
    # leashed, count = abbot.is_leashed()
    # if leashed:
    #     return await message.reply_text(f"I'm already leashed for {chat_title}! To unleash me, please run /leash!")
    # abbot.leash()
    # leashed, count = abbot.is_leashed()
    # bot_debug.log(f"{fn} leashed={leashed}")
    # return await message.reply_text(
    #     f"I have been leashed! To unleash me again, run /unleash or /unleash <insert_new_number> (e.g. /unleash 10)"
    # )


@try_except
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, _, __annotations__ = update_data
    await message.reply_text(
        "Hey! The name's Abbot but you can think of me as your go-to guide for all things Bitcoin. AKA the virtual Bitcoin whisperer. 😉\n\n"
        "Here's the lowdown on how to get my attention: \n\n"
        "1. Slap an @atl_bitlab_bot before your message in the group chat - I'll come running to answer. \n"
        "2. Feel more comfortable replying directly to my messages? Go ahead! I'm all ears.. err.. code. \n"
        "3. Fancy a one-on-one chat? Slide into my DMs. \n\n"
        "Now, enough with the rules! Let's dive into the world of Bitcoin together! \n\n"
        "Ready. Set. Stack Sats! 🚀"
    )


@try_except
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, user = update_data
    pass
    # TODO: finish this logic
    # if is_group_chat:
    #     is_admin = await sender_is_group_admin(context)
    #     if not is_admin:
    #         return await message.reply_text("Forbidden: Admin only!")
    # else:
    #     abbot_context = "private"
    #     bot_debug.log(f"{fn} is_private_chat={is_private_chat}")
    # bot_debug.log(f"{fn} abbot_context={abbot_context}")
    # abbot: Abbot = Abbot(chat_id)
    # if abbot.is_started():
    #     return await message.reply_text("Abbot already started!")
    # abbot.start()
    # started = abbot.is_started()
    # bot_debug.log(f"{fn} abbot={abbot.to_dict()} started={started}")
    # await message.reply_photo(MATRIX_IMG_FILEPATH, f"Please wait while we unplug {BOT_NAME} from the Matrix")
    # response = abbot.chat_completion()
    # if not response:
    #     return await context.bot.send_message(
    #         chat_id=THE_CREATOR,
    #         text=f"chat_title={chat_title} chat_id={chat_id}",
    #     )
    # await message.reply_text(response)


@try_except
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_data: Tuple[Message, Chat, User] = await parse_update_data(update, context)
    message, chat, user = update_data
    pass
    # TODO: finish this logic    abbot_context = "group"
    # is_private_chat: bool = chat_type == "private"
    # is_group_chat: bool = not is_private_chat
    # if is_group_chat:
    #     admins = await context.bot.get_chat_administrators(chat_id)
    #     admin_ids = [admin.user.id for admin in admins]
    #     if user_id not in admin_ids:
    #         return await update.message.reply_text("Forbidden: Admin only!")
    # else:
    #     abbot_context = "private"
    #     bot_debug.log(f"{fn} is_private_chat={is_private_chat}")
    # bot_debug.log(f"{fn} abbot_context={abbot_context}")
    # abbot: Abbot = Abbot(chat_id)
    # if not abbot.started:
    #     await message.reply_text("Abbot isn't started yet! Have an admin run /start")
    #     return await context.bot.send_message(chat_id=THE_CREATOR, text=f"chat_title={chat_title} chat_id={chat_id}")
    # started = abbot.stop()
    # if not started:
    #     raise Exception(f"Not started! started={started}")
    # await message.reply_text("Thanks for using Abbot! To restart, use the /start command at any time.")


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
async def handle_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_chat_user: Tuple[Message, Chat, User] = await parse_message_chat_user(update, context)
    message, chat, user = message_chat_user
    chat_type: ChatType = chat.type
    if chat_type != "private":
        bot_error.log(__name__, f"chat_type not private")
        return await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"chat_id={chat.id} chat_type={chat_type} chat_title={chat.title}"
        )
    tg_doc: MongoTelegramDocument = MongoTelegramDocument(message=message)
    bot_debug.log("tg_doc", tg_doc)
    tg_doc_dict = tg_doc.to_dict()
    bot_debug.log("tg_doc_dict", tg_doc_dict)
    dm = mongo_abbot.find_one_dm({"id": chat.id})
    bot_debug.log("dm", dm)
    if not dm:
        insert = mongo_abbot.insert_one_dm(tg_doc_dict)
        if not successful_insert_one(insert):
            bot_error.log("insert failed", insert)
        bot_debug.log("insert", insert)
    # abbot = Abbot(chat.id, "dm")
    # abbot.update_history({"role": "user", "content": message.text})
    # bot_debug.log(f"{__name__} chat_id={chat.id}, {user.username} dms with Abbot")
    # answer = abbot.chat_completion()
    return await message.reply_text("answer")


@try_except
async def handle_multiperson_chat_message(message: Message, chat: Chat, user: User):
    tg_doc: MongoTelegramDocument = MongoTelegramDocument(message=message)
    bot_debug.log("tg_doc", tg_doc)
    tg_doc_dict = tg_doc.to_dict()
    bot_debug.log("tg_doc_dict", tg_doc_dict)
    channel = mongo_abbot.find_one_channel({"id": chat.id})
    bot_debug.log("channel", channel)
    if not channel:
        mongo_abbot.insert_one_dm(MongoTelegramDocument(message).to_dict())
    abbot = Abbot(chat.id, "channel")
    abbot.update_history({"role": "user", "content": message.text})
    bot_debug.log(f"{__name__} chat_id={chat.id}, {user.username} mentioned Abbot")
    answer = abbot.chat_completion()
    return await message.reply_text(answer)


@try_except
async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_chat_user: Tuple[Message, Chat, User] = await parse_message_chat_user(update, context)
    message, chat, user = message_chat_user
    chat_type: ChatType = chat.type
    valid_chat_types: Tuple[str] = ("channel", "supergroup", "group")
    if chat_type not in valid_chat_types:
        bot_error.log(__name__, f"chat_type not in valid_chat_types: {valid_chat_types}")
        return await context.bot.send_message(
            chat_id=THE_CREATOR, text=f"chat_id={chat.id} chat_type={chat_type} chat_title={chat.title}"
        )
    return await handle_multiperson_chat_message(message, chat, user)


@try_except
async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message and update.message.reply_to_message.from_user.username == BOT_TELEGRAM_HANDLE:
        pass


class TelegramBotBuilder:
    from lib.abbot.config import BOT_TELEGRAM_TOKEN

    def __init__(self):
        bot_debug.log(__name__, f"Telegram abbot initializing: name={BOT_NAME} handle={FULL_TELEGRAM_HANDLE}")
        telegram_bot = ApplicationBuilder().token(self.BOT_TELEGRAM_TOKEN).build()
        bot_debug.log(__name__, f"Telegram abbot initialized")

        # Add command handlers
        telegram_bot.add_handlers(
            handlers=[
                CommandHandler("unplug", admin_unplug),
                CommandHandler("plugin", admin_plugin),
                CommandHandler("kill", admin_kill),
                CommandHandler("nap", admin_nap),
                CommandHandler("status", admin_status),
                CommandHandler("help", help),
                CommandHandler("rules", rules),
                CommandHandler("start", start),
                CommandHandler("stop", stop),
                CommandHandler("unleash", unleash),
                CommandHandler("leash", leash),
            ]
        )
        # Add message handlers
        telegram_bot.add_handlers(
            handlers=[
                MessageHandler(ChatType.PRIVATE, handle_dm),
                MessageHandler(Entity(MENTION) & Regex(FULL_TELEGRAM_HANDLE), handle_mention),
                MessageHandler(ChatType.GROUPS & ENTITY_REPLY, handle_reply),
            ]
        )

        self.telegram_bot = telegram_bot

    def run(self):
        bot_debug.log(__name__, f"Telegram abbot polling")
        self.telegram_bot.run_polling()
