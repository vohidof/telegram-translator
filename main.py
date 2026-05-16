import logging
import os
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from groq import Groq

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

logging.basicConfig(level=logging.INFO)
client = Groq(api_key=GROQ_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\n"
        "Ushbu bot rus tilidan o'zbek tiliga tarjima qilish xizmatini taqdim etadi.\n\n"
        "Tarjima qilish uchun matnni yuboring — bot tez orada natijani qaytaradi.\n\n"
        "Bizning sahifamizga obuna bo'ling: @goedu_uz"
    )

async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.text:
        await message.reply_text("Iltimos, matnli xabar yuboring.")
        return

    original_text = message.text_html
    await message.reply_text("⏳ Tarjima qilinmoqda...")

    prompt = f"""Siz professional tarjimon sifatida rus tilidan o'zbek tiliga tarjima qilasiz.

MUHIM QOIDALAR:
1. Barcha HTML formatlashni O'ZGARTIRMANG: <b>, <i>, <u>, <s>, <tg-spoiler>, <a href="...">, <code>, <pre> teglari va qator o'tishlarini saqlang.
2. Faqat teglar ichidagi matnni tarjima qiling, teglarning o'zini o'zgartirmang.
3. Faqat tarjima qilingan matnni qaytaring, hech qanday izoh bermang.
4. O'zbek tilining adabiy me'yorlariga rioya qiling.
5. "Розыгрыш" so'zini "Tanlov" deb tarjima qiling.
6. "Вебинар" so'zini "vebinar" deb tarjima qiling.
7. Sanalar va vaqtlarni o'zgartirmang.

Tarjima qilish uchun matn:
{original_text}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        translated = response.choices[0].message.content.strip()
        
        footer = (
            "\n\n"
            "<a href='https://t.me/goedu_uz'>Telegram</a> | "
            "<a href='https://instagram.com/goedu.uz'>Instagram</a>"
        )
        
        await message.reply_text(translated + footer, parse_mode="HTML")
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
