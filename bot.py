import logging
from telegram import Update, ChatPermissions, ChatMember
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from collections import defaultdict
from datetime import timedelta
from telegram import User
from telegram.ext import CommandHandler

# Включаем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ключевые слова, которые считаются рекламой
AD_KEYWORDS = ["http", "https", "t.me", "bit.ly", "promo", "advertise", "buy now", "sale", "discount"]

# Хранилище предупреждений
warnings = defaultdict(int)

# Проверка текста на рекламу
def contains_advertising(text: str) -> bool:
    return any(word in text.lower() for word in AD_KEYWORDS)

# Основная обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    text = message.text
    user = message.from_user
    user_id = user.id
    chat_id = message.chat.id

    if contains_advertising(text):
        member = await context.bot.get_chat_member(chat_id, user_id)
        status = member.status

        # Проверка — если не админ и не владелец, то реагируем
        if status not in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
            await message.delete()

            # Увеличиваем счётчик предупреждений
            warnings[user_id] += 1
            warn_count = warnings[user_id]

            if warn_count < 3:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ Нарушение: {user.mention_html()} получил предупреждение {warn_count}/3",
                    parse_mode="HTML"
                )
            else:
                warnings[user_id] = 0  # сбрасываем после мута
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=message.date + timedelta(minutes=5)
                )
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⛔ {user.mention_html()} получил 3 предупреждения и замучен на 5 минут.",
                    parse_mode="HTML"
                )

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat_id = update.effective_chat.id
    sender = update.effective_user

    # Проверяем, админ ли отправитель
    sender_member = await context.bot.get_chat_member(chat_id, sender.id)
    if sender_member.status not in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
        await update.message.reply_text("⛔ Только админы могут использовать эту команду.")
        return

    if not context.args:
        await update.message.reply_text("❗ Используй: /mute @username")
        return

    # Получаем пользователя по username
    try:
        username = context.args[0].lstrip('@')
        target = await context.bot.get_chat_member(chat_id, username)
        user = target.user
    except Exception as e:
        await update.message.reply_text("❌ Не удалось найти пользователя.")
        return

    await context.bot.restrict_chat_member(
        chat_id=chat_id,
        user_id=user.id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=update.message.date + timedelta(minutes=5)
    )
    await update.message.reply_text(f"🔇 {user.mention_html()} замучен на 5 минут.", parse_mode="HTML")

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat_id = update.effective_chat.id
    sender = update.effective_user

    sender_member = await context.bot.get_chat_member(chat_id, sender.id)
    if sender_member.status not in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
        await update.message.reply_text("⛔ Только админы могут использовать эту команду.")
        return

    if not context.args:
        await update.message.reply_text("❗ Используй: /unmute @username")
        return

    try:
        username = context.args[0].lstrip('@')
        target = await context.bot.get_chat_member(chat_id, username)
        user = target.user
    except Exception as e:
        await update.message.reply_text("❌ Не удалось найти пользователя.")
        return

    await context.bot.restrict_chat_member(
        chat_id=chat_id,
        user_id=user.id,
        permissions=ChatPermissions(can_send_messages=True)
    )
    await update.message.reply_text(f"✅ {user.mention_html()} размучен.", parse_mode="HTML")



# Запуск бота
def main():
    BOT_TOKEN = "7790547022:AAG5iIbkd5wE9Jh2X_fBFUuX535s4C4YUBc"

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("mute", mute_command))
    app.add_handler(CommandHandler("unmute", unmute_command))

    logger.info("🤖 Бот запущен и работает...")
    app.run_polling()

if __name__ == "__main__":
    main()
