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


# AI-мозг
brain = InferenceClient(
    api_key=HF_TOKEN
)

# Генератор изображений
image_client = InferenceClient(
    provider="fal-ai",
    api_key=HF_TOKEN
)


async def improve_prompt(user_prompt):
    """
    Превращает обычный запрос пользователя
    в подробный prompt для генератора изображений.
    """

    system_prompt = """
You are an expert image-generation prompt engineer.

The user will write a short or imperfect request in Russian.

Your job is to understand exactly what the user means
and rewrite it as one detailed English prompt for an image generator.

Rules:
- Preserve the user's intended meaning.
- If the user says man, make it clearly an adult male.
- If the user says woman, make it clearly an adult female.
- Do not change the requested subject.
- Add useful visual details only when they do not contradict the request.
- Make clothing, environment, lighting and composition clear.
- Prefer photorealistic photography when the user asks for realism.
- Do not add extra people unless requested.
- Do not explain anything.
- Return ONLY the final English image prompt.
"""

    response = brain.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.3,
        max_tokens=500,
    )

    return response.choices[0].message.content.strip()


async def improve_edit_prompt(user_prompt):
    """
    Превращает обычную просьбу пользователя
    в точную инструкцию для редактирования фотографии.
    """

    system_prompt = """
You are an expert image-editing prompt engineer.

The user will describe in Russian what they want changed
in an existing photograph.

Rewrite the request as one precise English image-editing instruction.

Rules:
- Preserve the person's identity and face.
- Preserve the original person's pose unless the user asks otherwise.
- Preserve the original composition unless requested otherwise.
- Change ONLY what the user asks to change.
- Clearly describe the requested modification.
- Do not invent additional changes.
- If the user asks to change clothing, modify the clothing only.
- Return ONLY the final English editing instruction.
"""

    response = brain.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.2,
        max_tokens=400,
    )

    return response.choices[0].message.content.strip()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 🤖\n\n"
        "🎨 Напиши, что хочешь создать.\n"
        "Можно писать простыми словами — я сам улучшу запрос.\n\n"
        "📸 Или отправь фото с подписью, что изменить."
    )


async def generate_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user_prompt = update.message.text

    await update.message.reply_text(
        "🧠 Понимаю запрос и готовлю промпт..."
    )

    try:
        improved_prompt = await improve_prompt(user_prompt)

        await update.message.reply_text(
            "🎨 Создаю изображение..."
        )

        image = image_client.text_to_image(
            prompt=improved_prompt,
            model="black-forest-labs/FLUX.1-dev",
        )

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        await update.message.reply_photo(
            photo=buffer
        )

    except Exception as e:
        await update.message.reply_text(
            "Ошибка генерации:\n"
            + str(e)[:1500]
        )


async def edit_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user_prompt = update.message.caption

    if not user_prompt:
        await update.message.reply_text(
            "📸 Добавь подпись к фотографии.\n\n"
            "Например:\n"
            "«Сделай мою кофту чёрной»"
        )
        return

    await update.message.reply_text(
        "🧠 Понимаю, что нужно изменить..."
    )

    try:
        improved_prompt = await improve_edit_prompt(
            user_prompt
        )

        await update.message.reply_text(
            "📸 Редактирую фотографию..."
        )

        photo = update.message.photo[-1]

        file = await photo.get_file()

        photo_bytes = await file.download_as_bytearray()

        image = image_client.image_to_image(
            bytes(photo_bytes),
            prompt=improved_prompt,
            model="black-forest-labs/FLUX.2-dev",
        )

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        await update.message.reply_photo(
            photo=buffer
        )

    except Exception as e:
        await update.message.reply_text(
            "Ошибка редактирования:\n"
            + str(e)[:1500]
        )


def run_web_server():
    port = int(
        os.environ.get("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )


def run_bot():
    telegram_app = (
        Application
        .builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    telegram_app.add_handler(
        CommandHandler("start", start)
    )

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
