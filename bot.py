#!/usr/bin/env python3
import pytz, datetime as dt, asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, PicklePersistence, filters
import os, time, threading, datetime as dt
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, PicklePersistence
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, PicklePersistence, filters
)

BOT_TOKEN = os.environ["BOT_TOKEN"]          # Render подставит сам
PORT        = int(os.environ.get("PORT", 10000))  # порт, который даст Render

# --- фейковый HTTP-сервер, чтобы Render не гасил инстанс ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
async def daily_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Шлёт всем пользователям, у кого задана дата, сколько дней осталось."""
    bot_data = context.application.bot_data
    for user_id, data in bot_data.items():
        if "date" not in data:
            continue
        dembel_date = dt.date.fromisoformat(data["date"])
        delta = (dembel_date - dt.date.today()).days
        if delta < 0:                       # уже дембель
            text = "🎉 Поздравляю, ты уже дембель!"
        elif delta == 0:
            text = "🎊 Сегодня день Х – ДЕМБЕЛЬ!"
        else:
            text = f"📆 До дембеля осталось {delta} дней"
        try:
            await context.bot.send_message(chat_id=user_id, text=text)
        except Exception as e:
            # пользователь мог заблокировать бота
            print(f"skip {user_id}: {e}")

def keep_alive():
    with HTTPServer(("", PORT), Handler) as srv:
        srv.serve_forever()

threading.Thread(target=keep_alive, daemon=True).start()

# --- логика бота ---
persistence = PicklePersistence("bot_data.pickle")

async def start(update: Update, _):
    await update.message.reply_text(
        "👋 Привет! Я считаю дни до дембеля.\n"
        "Отправь дату в формате ДД.ММ.ГГГГ"
    )

async def dembel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = ctx.bot_data.get(user.id)
    if not data or "date" not in data:
        await update.message.reply_text("Сначала отправь дату дембеля!")
        return
    dembel_date = dt.date.fromisoformat(data["date"])
    delta = (dembel_date - dt.date.today()).days
    if delta < 0:
        await update.message.reply_text("🎉 Ты уже дембель!")
    elif delta == 0:
        await update.message.reply_text("🎊 Сегодня дембель!")
    else:
        await update.message.reply_text(f"📆 До дембеля осталось: {delta} дней")


async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        dembel_date = dt.datetime.strptime(update.message.text, "%d.%m.%Y").date()
    except ValueError:
        await update.message.reply_text("❌ Формат: ДД.ММ.ГГГГ")
        return
    if dembel_date <= dt.date.today():
        await update.message.reply_text("Дата должна быть в будущем.")
        return
    ctx.bot_data.setdefault(user.id, {})["date"] = dembel_date.isoformat()
    await update.message.reply_text("✅ Сохранил!")
def set_daily_job(job_queue: JobQueue):
    # 09:00 каждый день; first=(ближайшее 09:00)
    now = dt.datetime.utcnow()
    target = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if target < now:
        target += dt.timedelta(days=1)
    job_queue.run_repeating(daily_reminder, interval=dt.timedelta(days=1), first=target)
def main():
    app = Application.builder().token(BOT_TOKEN).persistence(persistence).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dembel", dembel))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
def set_daily_job(job_queue: JobQueue):
    import pytz
    msk = pytz.timezone("Europe/Moscow")
    now = dt.datetime.now(msk)
    target = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if target <= now:
        target += dt.timedelta(days=1)
    utc_target = target.astimezone(pytz.utc)
    job_queue.run_repeating(daily_reminder, interval=dt.timedelta(days=1), first=utc_target)

    # ежедневное напоминание
    set_daily_job(app.job_queue)

    print("Bot + daily reminder started …")
    app.run_polling(stop_signals=None)

def main():
    app = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dembel", dembel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    print("Bot started on Render …")
    app.run_polling(stop_signals=None)   # Render не любит SIGINT

if __name__ == "__main__":
    main()
