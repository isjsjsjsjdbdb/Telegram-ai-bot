import os
import io
import threading
from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from huggingface_hub import InferenceClient

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
HF_TOKEN = os.environ["HF_TOKEN"]

app = Flask(__name__)

@app.route("/")
def home():
    return "Telegram AI Photo Bot is running!"

client = InferenceClient(
    provider="fal-ai",
    api_key=HF_TOKEN,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 🤖\n\n"
        "🎨 Напиши описание — создам изображение.\n"
        "📸 Или отправь фото с подписью, что изменить."
    )

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text

    await update.message.reply_text("Генерирую изображение... 🎨")

    try:
        image = client.text_to_image(
            prompt,
            model="black-forest-labs/FLUX.2-dev",
        )

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        await update.message.reply_photo(photo=buffer)

    except Exception as e:
        await update.message.reply_text(
            "Ошибка генерации:\n" + str(e)[:1000]
        )


async def edit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]

    prompt = update.message.caption

    if not prompt:
        await update.message.reply_text(
            "Напиши в подписи к фото, что изменить. "
            "Например: «Сделай кофту чёрной»."
        )
        return

    await update.message.reply_text("Редактирую фото... 🖼️")

    try:
        file = await photo.get_file()
        photo_bytes = await file.download_as_bytearray()

        image = client.image_to_image(
            bytes(photo_bytes),
            prompt=prompt,
            model="black-forest-labs/FLUX.2-dev",
        )

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        await update.message.reply_photo(photo=buffer)

    except Exception as e:
        await update.message.reply_text(
            "Ошибка редактирования:\n" + str(e)[:1000]
        )


def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


def run_bot():
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))

    telegram_app.add_handler(
        MessageHandler(
            filters.PHOTO,
            edit_photo
        )
    )

    telegram_app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            generate_image
        )
    )

    telegram_app.run_polling()


if __name__ == "__main__":
    threading.Thread(
        target=run_web_server,
        daemon=True
    ).start()

    run_bot()
