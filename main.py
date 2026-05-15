import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import google.generativeai as genai

TELEGRAM_TOKEN = "СЮДА_ВСТАВЬТЕ_ТОКЕН_ОТ_BOTFATHER"
GEMINI_API_KEY = "СЮДА_ВСТАВЬТЕ_КЛЮЧ_GEMINI"

logging.basicConfig(level=logging.INFO)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.text:
        await message.reply_text("Пожалуйста, отправьте текстовое сообщение.")
        return

    original_text = message.text_html
    await message.reply_text("⏳ Перевожу...")

    prompt = f"""Переведи следующий текст на узбекский язык.

ОЧЕНЬ ВАЖНО:
1. Сохрани всё HTML-форматирование БЕЗ ИЗМЕНЕНИЙ: теги <b>, <i>, <u>, <s>, <tg-spoiler>, <a href="...">, <code>, <pre> и переносы строк.
2. Переводи ТОЛЬКО текст внутри тегов, сами теги не трогай.
3. Верни ТОЛЬКО переведённый текст с тегами, без пояснений.

Текст:
{original_text}"""

    try:
        response = model.generate_content(prompt)
        translated = response.text.strip()
        await message.reply_text(translated, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.reply_text(f"❌ Ошибка: {str(e)}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_message))
    print("Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
