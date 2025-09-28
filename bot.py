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
            text = f"📆 До дембеля осталось {delta} дней,бусинка и мы будем вместе ❤"
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
# 1. Импорты (добавь к уже существующим)
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

# 2. Тексты-подарки для неё
LOVE_LINES = [
    "Моя самая стойкая девчонка, ты — мой пост №1, который я несу в сердце каждый день.",
    "Сколько бы ни было нарядов, самая красивая форма — это твоя улыбка на фото.",
    "Считаю дни, а потом буду считать поцелуи — обещаю догнать все пропущенные.",
    "Ты мой тыл и мой фронт любви: пока ты ждёшь — я не боюсь ни одной проверки.",
    "Каждый вечер записываю тебя в рапорт: «Девушка ждёт, мотивация 100 %».",
    "Готов обойти весь полигон, лишь бы скорее оказаться рядом и просто обнять.",
    "Твои «спокойной ночи» греют лучше любого костра в поле.",
    "Дома уже пахнет твоим шампунем — я помню и мечтаю вдохнуть этот запах вживую.",
    "Ты — мой личный приказ №1: «Вернуться и сделать её самой счастливой».",
    "Пока служу, храню каждое твоё фото в груди, как бронежилет для души."
]

# 3. Клавиатура с одной кнопкой
def girl_menu_mini() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💌 Трогательное письмо", callback_data="love")]
    ])

# 4. Обработчик нажатия кнопки
async def send_love(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await ctx.bot.send_message(
        update.effective_chat.id,
        text=random.choice(LOVE_LINES)
    )

# 5. Где показать кнопку (пример в /start)
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Нажми кнопку ниже:",
        reply_markup=girl_menu_mini()
    )

# 6. Регистрация хендлеров (добавь в main())
app.add_handler(CommandHandler("start", cmd_start))
app.add_handler(CallbackQueryHandler(send_love, pattern="^love$"))

def main():
    app = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dembel", dembel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    print("Bot started on Render …")
    app.run_polling(stop_signals=None)   # Render не любит SIGINT

if __name__ == "__main__":
    main()
