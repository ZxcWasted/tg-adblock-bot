import os
import logging
from datetime import timedelta
from collections import defaultdict
from telegram import (
    Update,
    ChatMember,
    ChatPermissions,
    User,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ключевые слова рекламы
AD_KEYWORDS = ["http", "https", "t.me", "bit.ly", "promo", "advertise", "buy now", "sale", "discount"]

# Храним предупреждения
warnings = defaultdict(int)

BOT_TOKEN = os.getenv("BOT_TOKEN")

def contains_advertising(text: str) -> bool:
    return any(word in text.lower() for word in AD_KEYWORDS)

# Обработка обычных сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    user = message.from_user
    chat_id = message.chat.id
    user_id = user.id
    text = message.text

    if contains_advertising(text):
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status not in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
            await message.delete()
            warnings[user_id] += 1
            warn_count = warnings[user_id]

            if warn_count < 3:
                await message.reply_html(
                    f"{user.mention_html()}, ⚠️ это реклама. У вас {warn_count}/3 предупреждений."
                )
            else:
                warnings[user_id] = 0
                await context.bot.restrict_chat_member(
                    chat_id,
                    user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=message.date + timedelta(minutes=5),
                )
                await message.reply_html(
                    f"{user.mention_html()}, вы получили 3 предупреждения. Вас замутили на 5 минут."
                )

# Команда /mute @user
async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat.id

    if not await is_admin(context, chat_id, message.from_user.id):
        await message.reply_text("⛔ Только администраторы могут использовать эту команду.")
        return

    if not message.reply_to_message:
        await message.reply_text("❗ Используй команду в ответ на сообщение пользователя.")
        return

    user_to_mute = message.reply_to_message.from_user
    await context.bot.restrict_chat_member(
        chat_id,
        user_to_mute.id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=message.date + timedelta(minutes=5)
    )
    await message.reply_text(f"🔇 {user_to_mute.mention_html()} был замучен на 5 минут.", parse_mode="HTML")

# Команда /unmute @user
async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat.id

    if not await is_admin(context, chat_id, message.from_user.id):
        await message.reply_text("⛔ Только администраторы могут использовать эту команду.")
        return

    if not message.reply_to_message:
        await message.reply_text("❗ Используй команду в ответ на сообщение пользователя.")
        return

    user_to_unmute = message.reply_to_message.from_user
    await context.bot.restrict_chat_member(
        chat_id,
        user_to_unmute.id,
        permissions=ChatPermissions(can_send_messages=True)
    )
    await message.reply_text(f"🔊 {user_to_unmute.mention_html()} теперь может писать сообщения.", parse_mode="HTML")

# Проверка, админ ли
async def is_admin(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
    member = await context.bot.get_chat_member(chat_id, user_id)
    return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]

# Запуск
async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("mute", mute_command))
    app.add_handler(CommandHandler("unmute", unmute_command))

    logger.info("Бот запущен с поддержкой mute/unmute.")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
