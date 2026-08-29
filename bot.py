import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from huggingface_hub import InferenceClient

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
HF_TOKEN = os.environ["HF_TOKEN"]

app = Flask(__name__)

@app.route("/")
def home():
    return "Telegram AI Photo Bot is running!"

client = InferenceClient(
    provider="auto",
    api_key=HF_TOKEN
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 🤖\n\n"
        "Напиши, какую картинку создать."
    )

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text

    await update.message.reply_text("Генерирую изображение... 🎨")

    try:
        image = client.text_to_image(
            prompt,
            model="black-forest-labs/FLUX.1-schnell"
        )

        filename = "generated.png"
        image.save(filename)

        with open(filename, "rb") as photo:
            await update.message.reply_photo(photo=photo)

    except Exception as e:
        await update.message.reply_text(
            "Ошибка: " + str(e)[:500]
        )

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def run_bot():
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image)
    )

    telegram_app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    run_bot()
