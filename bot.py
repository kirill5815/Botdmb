#!/usr/bin/env python3
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

def main():
    app = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dembel", dembel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    print("Bot started on Render …")
    app.run_polling(stop_signals=None)   # Render не любит SIGINT

if __name__ == "__main__":
    main()
