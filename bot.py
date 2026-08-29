import os
import io
import threading
import urllib.parse
import requests
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
POLLINATIONS_API_KEY = os.environ["POLLINATIONS_API_KEY"]
app = Flask(__name__)
@app.route("/")
def home():
    return "Telegram AI Photo Bot is running!"
# AI-мозг для понимания запросов
brain = InferenceClient(
    api_key=HF_TOKEN
)
async def improve_prompt(user_prompt):
    system_prompt = """
You are an expert image prompt engineer.
The user writes in Russian, sometimes with mistakes,
short phrases, or incomplete descriptions.
Understand what the user means and convert it
into ONE detailed English prompt for an image generator.
Important:
- Preserve the user's exact intention.
- If the user says MAN or МУЖЧИНА, it must be an adult male.
- If the user says WOMAN or ЖЕНЩИНА, it must be an adult female.
- Do not change the requested gender.
- Do not add extra people.
- Make clothing, environment, lighting and composition clear.
- If realism is requested, use photorealistic photography.
- Do not explain anything.
- Return ONLY the final English prompt.
"""
    response = brain.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0.2,
        max_tokens=500,
    )
    return response.choices[0].message.content.strip()
async def improve_edit_prompt(user_prompt):
    system_prompt = """
You are an expert photo editing prompt engineer.
The user describes in Russian what they want changed
in an existing photograph.
Create ONE precise English instruction for image editing.
Rules:
- Preserve the person's identity and face.
- Preserve the person's gender.
- Preserve the person's pose unless specifically asked to change it.
- Preserve the original image composition.
- Change ONLY what the user requests.
- If the user asks to change clothing, change the clothing.
- Do not invent additional modifications.
- Return ONLY the final English editing instruction.
"""
    response = brain.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0.1,
        max_tokens=400,
    )
    return response.choices[0].message.content.strip()
def generate_pollinations_image(prompt):
    encoded_prompt = urllib.parse.quote(prompt)
    url = (
        "https://gen.pollinations.ai/image/"
        + encoded_prompt
        + "?model=flux"
        + "&width=1024"
        + "&height=1024"
    )
    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {POLLINATIONS_API_KEY}"
        },
        timeout=180,
    )
    response.raise_for_status()
    return response.content
def edit_pollinations_image(image_bytes, prompt):
    """
    Отправляет исходное изображение и инструкцию
    в Pollinations для редактирования.
    """
    files = {
        "image": (
            "photo.jpg",
            image_bytes,
            "image/jpeg",
        )
    }
    data = {
        "prompt": prompt,
        "model": "kontext",
    }
    response = requests.post(
        "https://gen.pollinations.ai/image/edit",
        headers={
            "Authorization": f"Bearer {POLLINATIONS_API_KEY}"
        },
        files=files,
        data=data,
        timeout=240,
    )
    response.raise_for_status()
    return response.content
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 🤖\n\n"
        "🎨 Напиши, какую картинку создать.\n"
        "Можно писать обычными словами.\n\n"
        "📸 Или отправь фотографию с подписью,\n"
        "что нужно изменить."
    )
async def generate_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_prompt = update.message.text
    await update.message.reply_text(
        "🧠 Понимаю твой запрос..."
    )
    try:
        improved_prompt = await improve_prompt(
            user_prompt
        )
        await update.message.reply_text(
            "🎨 Создаю изображение..."
        )
        image_bytes = generate_pollinations_image(
            improved_prompt
        )
        buffer = io.BytesIO(image_bytes)
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
    context: ContextTypes.DEFAULT_TYPE,
):
    user_prompt = update.message.caption
    if not user_prompt:
        await update.message.reply_text(
            "📸 Напиши в подписи, что изменить.\n\n"
            "Например:\n"
            "Сделай мою кофту чёрной."
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
        result = edit_pollinations_image(
            bytes(photo_bytes),
            improved_prompt,
        )
        buffer = io.BytesIO(result)
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
        port=port,
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
            edit_photo,
        )
    )
    telegram_app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            generate_image,
        )
    )
    telegram_app.run_polling()
if __name__ == "__main__":
    threading.Thread(
        target=run_web_server,
        daemon=True,
    ).start()
    run_bot()
