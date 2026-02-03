# Birthday Bot (single-file version)
import os
import sqlite3
from datetime import datetime, time
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings(
    chat_id INTEGER PRIMARY KEY,
    greet_time TEXT DEFAULT '08:00',
    greet_text TEXT DEFAULT '🎉 Bugun tug‘ilgan ustozlarimiz:\n\n{names}'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS teachers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    full_name TEXT,
    day INTEGER,
    month INTEGER
)
""")
conn.commit()

def menu():
    return ReplyKeyboardMarkup([
        ["➕ Ustoz qo‘shish", "📋 Ustozlar ro‘yxati"],
        ["⏰ Tabrik vaqtini o‘zgartirish"]
    ], resize_keyboard=True)

async def birthday_job(context):
    chat_id = context.job.chat_id
    now = datetime.now()

    teachers = cursor.execute(
        "SELECT full_name FROM teachers WHERE chat_id=? AND day=? AND month=?",
        (chat_id, now.day, now.month)
    ).fetchall()

    if not teachers:
        return

    text = cursor.execute(
        "SELECT greet_text FROM settings WHERE chat_id=?",
        (chat_id,)
    ).fetchone()[0]

    names = "\n".join(f"🎉 {t[0]}" for t in teachers)
    await context.bot.send_message(chat_id, text.replace("{names}", names))

async def start(update, context):
    chat_id = update.effective_chat.id

    cursor.execute("INSERT OR IGNORE INTO settings(chat_id) VALUES(?)",(chat_id,))
    conn.commit()

    await update.message.reply_text("Bot ishga tayyor", reply_markup=menu())

ADD_NAME, ADD_DAY, ADD_MONTH = range(3)

async def add_start(update, context):
    await update.message.reply_text("Ism familiya kiriting:")
    return ADD_NAME

async def add_name(update, context):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Kun (1-31):")
    return ADD_DAY

async def add_day(update, context):
    context.user_data["day"] = int(update.message.text)
    await update.message.reply_text("Oy (1-12):")
    return ADD_MONTH

async def add_month(update, context):
    cursor.execute(
        "INSERT INTO teachers(chat_id,full_name,day,month) VALUES(?,?,?,?)",
        (update.effective_chat.id,
         context.user_data["name"],
         context.user_data["day"],
         int(update.message.text))
    )
    conn.commit()

    await update.message.reply_text("Qo‘shildi", reply_markup=menu())
    return ConversationHandler.END

async def list_teachers(update, context):
    rows = cursor.execute(
        "SELECT full_name,day,month FROM teachers WHERE chat_id=?",
        (update.effective_chat.id,)
    ).fetchall()

    txt = ""
    for r in rows:
        txt += f"{r[0]} — {r[1]:02d}.{r[2]:02d}\n"

    await update.message.reply_text(txt or "Bo‘sh")

app = Application.builder().token(BOT_TOKEN).build()

conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^➕ Ustoz qo‘shish$"), add_start)],
    states={
        ADD_NAME:[MessageHandler(filters.TEXT, add_name)],
        ADD_DAY:[MessageHandler(filters.TEXT, add_day)],
        ADD_MONTH:[MessageHandler(filters.TEXT, add_month)]
    },
    fallbacks=[]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv)
app.add_handler(MessageHandler(filters.Regex("^📋 Ustozlar ro‘yxati$"), list_teachers))

print("Bot running...")
app.run_polling()
