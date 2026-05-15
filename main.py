import logging
import os
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
import google.generativeai as genai

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

logging.basicConfig(level=logging.INFO)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\n"
        "Ushbu bot rus tilidan o'zbek tiliga tarjima qilish xizmatini taqdim etadi.\n\n"
        "Tarjima qilish uchun matnni yuboring — bot tez orada natijani qaytaradi.\n\n"
        "Barcha formatlash (qalin shrift, kursiv, havolalar) to'liq saqlanadi. ✅\n\n"
        "@goedu_uz obuna bo'ling"
    )

async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.text:
        await message.reply_text("Iltimos, matnli xabar yuboring.")
        return

    original_text = message.text_html
    await message.reply_text("⏳ Tarjima qilinmoqda...")

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
        await message.reply_text(f"❌ Xatolik yuz berdi: {str(e)}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_message))
    print("Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
