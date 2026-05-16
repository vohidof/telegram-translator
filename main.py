import logging
import os
import json
from datetime import datetime, timedelta
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from groq import Groq

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
CHANNEL_ID = "@goedu_uz"
TASHKENT_TZ = pytz.timezone("Asia/Tashkent")
STATS_FILE = "stats.json"
APPROVED_USERS_FILE = "approved_users.json"

logging.basicConfig(level=logging.INFO)
client = Groq(api_key=GROQ_API_KEY)

# --- Статистика ---
def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    return {"translated": 0, "published": 0, "scheduled": 0}

def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)

def increment_stat(key):
    stats = load_stats()
    stats[key] = stats.get(key, 0) + 1
    save_stats(stats)

def reset_stats():
    save_stats({"translated": 0, "published": 0, "scheduled": 0})

# --- Пользователи ---
def load_approved():
    if os.path.exists(APPROVED_USERS_FILE):
        with open(APPROVED_USERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_approved(users):
    with open(APPROVED_USERS_FILE, "w") as f:
        json.dump(users, f)

def is_approved(user_id):
    if user_id == OWNER_ID:
        return True
    return user_id in load_approved()

# --- Перевод ---
async def do_translate(text, lang_pair):
    instruction = "rus tilidan o'zbek tiliga tarjima qil" if lang_pair == "lang_ru_uz" else "ingliz tilidan o'zbek tiliga tarjima qil"
    prompt = f"""Siz professional tarjimon sifatida {instruction}.

MUHIM QOIDALAR:
1. Barcha HTML formatlashni O'ZGARTIRMANG: <b>, <i>, <u>, <s>, <tg-spoiler>, <a href="...">, <code>, <pre> teglari va qator o'tishlarini saqlang.
2. Faqat teglar ichidagi matnni tarjima qiling, teglarning o'zini o'zgartirmang.
3. Faqat tarjima qilingan matnni qaytaring, hech qanday izoh bermang.
4. O'zbek tilining adabiy me'yorlariga rioya qiling.
5. "Розыгрыш" so'zini "Tanlov" deb tarjima qiling.
6. "Вебинар" / "webinar" so'zini "vebinar" deb tarjima qiling.
7. Sanalar va vaqtlarni o'zgartirmang.

Tarjima qilish uchun matn:
{text}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()

def build_full_post(translated, original_html):
    spoiler = f"<tg-spoiler>{original_html}</tg-spoiler>"
    footer = (
        "\n\n"
        "<a href='https://t.me/goedu_uz'>Telegram</a> | "
        "<a href='https://instagram.com/goedu.uz'>Instagram</a>"
    )
    return translated + "\n\n" + spoiler + footer

# --- Команды ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        await update.message.reply_text(
            "Salom! 👋\n\nBotdan foydalanish uchun admin ruxsati kerak.\n"
            "Ruxsat so'rash uchun: /request"
        )
        return
    text = "Assalomu alaykum! 👋\n\nTarjima qilish uchun matnni yuboring. ✅\n\n📊 Statistika: /stats"
    if user_id == OWNER_ID:
        text += "\n👥 Foydalanuvchilar: /users"
    await update.message.reply_text(text)

async def request_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_approved(user.id):
        await update.message.reply_text("✅ Sizda allaqachon ruxsat bor!")
        return
    await update.message.reply_text("⏳ So'rovingiz adminga yuborildi. Kuting.")
    keyboard = [[
        InlineKeyboardButton("✅ Ruxsat berish", callback_data=f"approve_{user.id}"),
        InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{user.id}"),
    ]]
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=(
            f"🔔 <b>Yangi so'rov</b>\n\n"
            f"👤 Ism: {user.full_name}\n"
            f"🆔 ID: <code>{user.id}</code>\n\n"
            f"Bu foydalanuvchiga ruxsat berasizmi?"
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    approved = load_approved()
    if not approved:
        await update.message.reply_text("👥 Hozircha ruxsat berilgan foydalanuvchilar yo'q.")
        return
    text = "👥 <b>Ruxsat berilgan foydalanuvchilar:</b>\n\n"
    keyboard = []
    for uid in approved:
        text += f"🆔 <code>{uid}</code>\n"
        keyboard.append([InlineKeyboardButton(f"❌ {uid} ni o'chirish", callback_data=f"remove_{uid}")])
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_approved(update.effective_user.id):
        return
    stats = load_stats()
    await update.message.reply_text(
        f"📊 <b>Haftalik statistika</b>\n\n"
        f"🔄 Tarjima qilingan: <b>{stats.get('translated', 0)}</b> ta\n"
        f"✅ Joylashtirilgan: <b>{stats.get('published', 0)}</b> ta\n"
        f"🕐 Rejalashtirilgan: <b>{stats.get('scheduled', 0)}</b> ta",
        parse_mode="HTML",
    )

async def send_weekly_stats(context: ContextTypes.DEFAULT_TYPE):
    stats = load_stats()
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=(
            f"📊 <b>Haftalik statistika</b>\n\n"
            f"🔄 Tarjima qilingan: <b>{stats.get('translated', 0)}</b> ta\n"
            f"✅ Joylashtirilgan: <b>{stats.get('published', 0)}</b> ta\n"
            f"🕐 Rejalashtirilgan: <b>{stats.get('scheduled', 0)}</b> ta\n\n"
            f"Yangi hafta boshlanadi! 🚀"
        ),
        parse_mode="HTML",
    )
    reset_stats()

# --- Основной обработчик ---
async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_approved(update.effective_user.id):
        await update.message.reply_text("❌ Ruxsat yo'q. /request buyrug'ini yuboring.")
        return
    original_text = update.message.text_html
    context.user_data["original"] = original_text
    context.user_data["waiting_correction"] = False
    context.user_data["waiting_time"] = False
    keyboard = [[
        InlineKeyboardButton("🇷🇺 Rus → O'zbek", callback_data="lang_ru_uz"),
        InlineKeyboardButton("🇬🇧 Ingliz → O'zbek", callback_data="lang_en_uz"),
    ]]
    await update.message.reply_text(
        "Tarjima yo'nalishini tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("approve_"):
        uid = int(data.split("_")[1])
        approved = load_approved()
        if uid not in approved:
            approved.append(uid)
            save_approved(approved)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"✅ Foydalanuvchi {uid} qabul qilindi.")
        await context.bot.send_message(chat_id=uid, text="✅ Botdan foydalanishga ruxsat berildi! /start yuboring.")

    elif data.startswith("reject_"):
        uid = int(data.split("_")[1])
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"❌ Foydalanuvchi {uid} rad etildi.")
        await context.bot.send_message(chat_id=uid, text="❌ So'rovingiz rad etildi.")

    elif data.startswith("remove_"):
        uid = int(data.split("_")[1])
        approved = load_approved()
        if uid in approved:
            approved.remove(uid)
            save_approved(approved)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"✅ Foydalanuvchi {uid} o'chirildi.")
        await context.bot.send_message(chat_id=uid, text="⚠️ Botdan foydalanish huquqingiz bekor qilindi.")

    elif data in ("lang_ru_uz", "lang_en_uz"):
        await query.edit_message_reply_markup(reply_markup=None)
        context.user_data["lang_pair"] = data
        keyboard = [[
            InlineKeyboardButton("💬 Faqat tarjima", callback_data="only_translate"),
            InlineKeyboardButton("📢 Kanal uchun", callback_data="for_publish"),
        ]]
        await query.message.reply_text("Qanday tarjima qilish kerak?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "only_translate":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("⏳ Tarjima qilinmoqda...")
        try:
            translated = await do_translate(context.user_data.get("original", ""), context.user_data.get("lang_pair", "lang_ru_uz"))
            increment_stat("translated")
            await query.message.reply_text(translated, parse_mode="HTML")
        except Exception as e:
            await query.message.reply_text(f"❌ Xatolik: {str(e)}")

    elif data == "for_publish":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("⏳ Tarjima qilinmoqda...")
        try:
            original = context.user_data.get("original", "")
            translated = await do_translate(original, context.user_data.get("lang_pair", "lang_ru_uz"))
            increment_stat("translated")
            full_text = build_full_post(translated, original)
            context.user_data["translated"] = full_text
            keyboard = [
                [
                    InlineKeyboardButton("✅ Hozir yuborish", callback_data="publish_now"),
                    InlineKeyboardButton("🕐 Vaqt belgilash", callback_data="schedule"),
                ],
                [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")],
            ]
            await query.message.reply_text(full_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            await query.message.reply_text(f"❌ Xatolik: {str(e)}")

    elif data == "publish_now":
        translated = context.user_data.get("translated")
        if translated:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=translated, parse_mode="HTML")
            increment_stat("published")
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text("✅ Post kaналga muvaffaqiyatli joylashtirildi!")

    elif data == "schedule":
        await query.edit_message_reply_markup(reply_markup=None)
        now = datetime.now(TASHKENT_TZ)
        await query.message.reply_text(
            f"🕐 Qaysi vaqtda yuborish kerak?\n\n"
            f"Hozirgi vaqt: <b>{now.strftime('%H:%M')}</b>\n\n"
            f"Vaqtni yuboring, masalan: <b>18:00</b>",
            parse_mode="HTML",
        )
        context.user_data["waiting_time"] = True

    elif data == "cancel":
        await query.edit_message_reply_markup(reply_markup=None)
        keyboard = [[
            InlineKeyboardButton("✅ Ha", callback_data="yes_correction"),
            InlineKeyboardButton("❌ Yo'q", callback_data="no_correction"),
        ]]
        await query.message.reply_text("Tahrirlangan versiyani yubormoqchimisiz?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "yes_correction":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("✏️ Tahrirlangan matnni yuboring.")
        context.user_data["waiting_correction"] = True

    elif data == "no_correction":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("🚫 Nashr bekor qilindi.")
        context.user_data["waiting_correction"] = False

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_approved(update.effective_user.id):
        await update.message.reply_text("❌ Ruxsat yo'q. /request buyrug'ini yuboring.")
        return

    if context.user_data.get("waiting_correction"):
        corrected_text = update.message.text_html
        await context.bot.send_message(chat_id=CHANNEL_ID, text=corrected_text, parse_mode="HTML")
        increment_stat("published")
        context.user_data["waiting_correction"] = False
        await update.message.reply_text("✅ Tahrirlangan matn kanalga joylashtirildi!")

    elif context.user_data.get("waiting_time"):
        time_text = update.message.text.strip()
        try:
            now = datetime.now(TASHKENT_TZ)
            scheduled_time = TASHKENT_TZ.localize(
                datetime.strptime(f"{now.date()} {time_text}", "%Y-%m-%d %H:%M")
            )
            if scheduled_time <= now:
                scheduled_time += timedelta(days=1)
            delay = (scheduled_time - now).total_seconds()
            translated = context.user_data.get("translated")
            context.job_queue.run_once(
                send_scheduled,
                when=delay,
                data={"text": translated, "chat_id": CHANNEL_ID},
            )
            increment_stat("scheduled")
            context.user_data["waiting_time"] = False
            await update.message.reply_text(
                f"✅ Post rejalashtirildi!\n📅 <b>{scheduled_time.strftime('%d.%m.%Y %H:%M')} (Toshkent)</b>",
                parse_mode="HTML",
            )
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri format. Masalan: <b>18:00</b>", parse_mode="HTML")
    else:
        await translate_message(update, context)

async def send_scheduled(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.send_message(chat_id=job.data["chat_id"], text=job.data["text"], parse_mode="HTML")
    increment_stat("published")

async def post_init(app: Application):
    now = datetime.now(TASHKENT_TZ)
    days_until_sunday = (6 - now.weekday()) % 7
    if days_until_sunday == 0 and now.hour >= 19:
        days_until_sunday = 7
    next_sunday = now.replace(hour=19, minute=0, second=0, microsecond=0) + timedelta(days=days_until_sunday)
    delay = (next_sunday - now).total_seconds()
    app.job_queue.run_repeating(
        send_weekly_stats,
        interval=7 * 24 * 3600,
        first=delay,
        name="weekly_stats",
    )

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("request", request_access))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
