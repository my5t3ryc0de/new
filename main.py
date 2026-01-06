from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "ISI_TOKEN_DARI_BOTFATHER"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 BOT TRADING AKTIF\n\n"
        "/buy - Sinyal BUY\n"
        "/sell - Sinyal SELL\n"
        "/signal - Contoh sinyal\n"
        "/help - Panduan"
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 SIGNAL BUY\n\nPair:\nEntry:\nTP:\nSL:")

async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔴 SIGNAL SELL\n\nPair:\nEntry:\nTP:\nSL:")

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📈 CONTOH SINYAL\n\n"
        "Pair: XAUUSD\nArah: BUY\nEntry: 2350-2345\nTP: 2380\nSL: 2325"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Gunakan /buy /sell /signal")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("buy", buy))
app.add_handler(CommandHandler("sell", sell))
app.add_handler(CommandHandler("signal", signal))
app.add_handler(CommandHandler("help", help_command))

print("Bot Trading aktif...")
app.run_polling()
