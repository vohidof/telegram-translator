import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from groq import Groq

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
CHANNEL_ID = "@goedu_uz"

logging.basicConfig(level=logging.INFO)
client = Groq(api_key=GROQ_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\n"
        "Ushbu bot rus tilidan o'zbek tiliga tarjima qilish xizmatini taqdim etadi.\n\n"
        "Tarjima qilish uchun matnni yuboring — bot tez orada natijani qaytaradi.\n\n"
        "Barcha formatlash (qalin shrift, kursiv, havolalar) to'liq saqlanadi. ✅"
    )

async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.text:
        await message.reply_text("Iltimos, matnli xabar yuboring.")
        return

    original_text = message.text_html
    context.user_data["original"] = original_text
    context.user_data["waiting_correction"] = False

    keyboard = [
        [
            InlineKeyboardButton("💬 Faqat tarjima", callback_data="only_translate"),
            InlineKeyboardButton("📢 Kanal uchun", callback_data="for_publish")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(
        "Qanday tarjima qilish kerak?",
        reply_markup=reply_markup
    )

async def do_translate(text, mode):
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
{text}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    translated = response.choices[0].message.content.strip()

    if mode == "publish":
        footer = (
            "\n\n"
            "<a href='https://t.me/goedu_uz'>Telegram</a> | "
            "<a href='https://instagram.com/goedu.uz'>Instagram</a>"
        )
        translated += footer

    return translated

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "only_translate":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("⏳ Tarjima qilinmoqda...")
        try:
            original = context.user_data.get("original", "")
            translated = await do_translate(original, mode="only")
            await query.message.reply_text(translated, parse_mode="HTML")
        except Exception as e:
            await query.message.reply_text(f"❌ Xatolik: {str(e)}")

    elif query.data == "for_publish":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("⏳ Tarjima qilinmoqda...")
        try:
            original = context.user_data.get("original", "")
            translated = await do_translate(original, mode="publish")
            context.user_data["translated"] = translated

            keyboard = [
                [
                    InlineKeyboardButton("✅ Opublikovat'", callback_data="publish"),
                    InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                translated,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception as e:
            await query.message.reply_text(f"❌ Xatolik: {str(e)}")

    elif query.data == "publish":
        translated = context.user_data.get("translated")
        if translated:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=translated,
                parse_mode="HTML"
            )
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text("✅ Kanal muvaffaqiyatli joylashtirildi!")
        else:
            await query.message.reply_text("❌ Xatolik: matn topilmadi.")

    elif query.data == "cancel":
        await query.edit_message_reply_markup(reply_markup=None)
        keyboard = [
            [
                InlineKeyboardButton("✅ Ha", callback_data="yes_correction"),
                InlineKeyboardButton("❌ Yo'q", callback_data="no_correction")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "Tahrirlangan versiyani yubormoqchimisiz?",
            reply_markup=reply_markup
        )

    elif query.data == "yes_correction":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "✏️ Tahrirlangan matnni yuboring — uni kanalga joylashtiramiz."
        )
        context.user_data["waiting_correction"] = True

    elif query.data == "no_correction":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("🚫 Nashr bekor qilindi.")
        context.user_data["waiting_correction"] = False

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_correction"):
        corrected_text = update.message.text_html
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=corrected_text,
            parse_mode="HTML"
        )
        context.user_data["waiting_correction"] = False
        await update.message.reply_text("✅ Tahrirlangan matn kanalga joylashtirildi!")
    else:
        await translate_message(update, context)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
