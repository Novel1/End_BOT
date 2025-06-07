import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from telegram.ext import CommandHandler


BOT_TOKEN = "8054818207:AAFq18jcwhO0h1i28mH-H2B_btNIMRyJLqQ"

# Настрой логгирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"Получено сообщение от {user.id}: {update.message.text}")
    await update.message.reply_text(
        f"Hello, {user.first_name}!\nYour Telegram ID is: {user.id}"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Welcome, {user.first_name}! Your Telegram ID is: {user.id}"
    )

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot is running...")
app.run_polling()
