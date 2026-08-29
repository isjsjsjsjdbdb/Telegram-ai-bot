import os
import io
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from huggingface_hub import InferenceClient

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
HF_TOKEN = os.environ["HF_TOKEN"]

client = InferenceClient(
    provider="hf-inference",
    api_key=HF_TOKEN
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 🤖\n\n"
        "Напиши, какую картинку создать.\n"
        "Например: реалистичный BMW M5 ночью в Хельсинки"
    )

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text

    await update.message.reply_text("Генерирую изображение... 🎨")

    try:
        image = client.text_to_image(
            prompt,
            model="black-forest-labs/FLUX.1-schnell"
        )

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        await update.message.reply_photo(photo=buffer)

    except Exception as e:
        await update.message.reply_text(
            f"Ошибка генерации: {str(e)[:500]}"
        )

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image)
    )

    app.run_polling()

if __name__ == "__main__":
    main()
