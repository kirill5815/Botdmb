#!/usr/bin/env python3
"""
Telegram-бот «Дембель» (бесплатный 24/7)
- Background Worker на Render
- Сам себя будит раз в 7 мин через Deploy Hook
- Секундный счётчик до дембеля (МСК)
- Утро 06:00, вечер 21:00 – напоминания
"""
import os
import random
import datetime as dt
import asyncio
import aiohttp
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    PicklePersistence,
    filters,
    JobQueue,
)

BOT_TOKEN   = os.getenv("BOT_TOKEN")
HOOK_URL    = os.getenv("RENDER_DEPLOY_HOOK")   # Deploy Hook Render
if not BOT_TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не задана")

MOSCOW      = pytz.timezone("Europe/Moscow")
PERSIST_FILE= "bot_data.pickle"

# ---------- тексты ----------
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
    "Пока служу, храню каждое твоё фото в груди, как бронежилет для души.",
]

# ---------- клавиатура ----------
def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📆 Сколько до дембеля", callback_data="now"),
            InlineKeyboardButton("💌 Трогательное письмо", callback_data="love"),
        ]
    ])

# ---------- обратный отсчёт ----------
def format_countdown(target_date: dt.date) -> str:
    now = dt.datetime.now(MOSCOW)
    target_dt = MOSCOW.localize(dt.datetime.combine(target_date, dt.time(0, 0)))
    delta = target_dt - now
    if delta.total_seconds() <= 0:
        return "🎉 Дембель настал!"
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    mins, secs = divmod(rem, 60)
    return f"До встречи: {days} дн. {hours:02d}:{mins:02d}:{secs:02d}"

# ---------- ежедневные напоминания ----------
async def send_morning(context: ContextTypes.DEFAULT_TYPE) -> None:
    await daily_reminder(context, prefix="☀️ Доброе утро! ")

async def send_evening(context: ContextTypes.DEFAULT_TYPE) -> None:
    await daily_reminder(context, prefix="🌙 Спокойной ночи! ")

async def daily_reminder(context: ContextTypes.DEFAULT_TYPE, prefix: str = "") -> None:
    bot_data = context.application.bot_data
    for user_id, data in bot_data.items():
        if "date" not in data:
            continue
        dembel_date = dt.date.fromisoformat(data["date"])
        days_left = (dembel_date - dt.date.today()).days
        if days_left < 0:
            text = prefix + "Ты уже дембель! 🎉"
        elif days_left == 0:
            text = prefix + "Сегодня день Х! Дембель! 🎊"
        else:
            text = prefix + f"До встречи осталось: {days_left} дней."
        try:
            await context.bot.send_message(chat_id=user_id, text=text)
        except Exception as e:
            print(f"skip {user_id}: {e}")

# ---------- команды и кнопки ----------
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = ctx.bot_data.setdefault(user.id, {})
    if "date" not in data:
        await update.message.reply_text("Введи дату дембеля в формате ДД.ММ.ГГГГ")
        data["expect_date"] = True
        return
    msg = await update.message.reply_text(
        format_countdown(dt.date.fromisoformat(data["date"])),
        reply_markup=main_kb()
    )
    ctx.job_queue.run_repeating(
        update_countdown,
        interval=1,
        first=0,
        data={"chat_id": msg.chat_id, "message_id": msg.message_id},
        name=f"countdown_{user.id}"
    )

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = ctx.bot_data.setdefault(user.id, {})
    if data.get("expect_date"):
        try:
            target = dt.datetime.strptime(update.message.text, "%d.%m.%Y").date()
        except ValueError:
            await update.message.reply_text("❌ Формат: ДД.ММ.ГГГГ")
            return
        if target <= dt.date.today():
            await update.message.reply_text("Дата должна быть в будущем.")
            return
        data["date"] = target.isoformat()
        data.pop("expect_date", None)
        msg = await update.message.reply_text(
            format_countdown(target),
            reply_markup=main_kb()
        )
        ctx.job_queue.run_repeating(
            update_countdown,
            interval=1,
            first=0,
            data={"chat_id": msg.chat_id, "message_id": msg.message_id},
            name=f"countdown_{user.id}"
        )

async def update_countdown(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_data = context.job.data
    user_id = int(context.job.name.split("_")[1])
    user_data = context.application.bot_data.get(user_id, {})
    if "date" not in user_data:
        context.job.schedule_removal()
        return
    try:
        await context.bot.edit_message_text(
            chat_id=job_data["chat_id"],
            message_id=job_data["message_id"],
            text=format_countdown(dt.date.fromisoformat(user_data["date"])),
            reply_markup=main_kb()
        )
    except Exception:
        context.job.schedule_removal()

async def btn_now(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = ctx.bot_data.get(user.id, {})
    if "date" not in data:
        await ctx.bot.send_message(user.id, "Сначала укажи дату дембеля.")
        return
    await ctx.bot.send_message(
        user.id,
        format_countdown(dt.date.fromisoformat(data["date"]))
    )

async def send_love(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await ctx.bot.send_message(
        update.effective_chat.id,
        text=random.choice(LOVE_LINES)
    )

# ---------- self-ping (анти-сон) ----------
async def self_ping():
    """Раз в 7 мин дергаем Deploy Hook → Render не засыпает."""
    while True:
        await asyncio.sleep(7 * 60)
        if HOOK_URL:
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.post(HOOK_URL) as r:
                        print(f"[ping] {r.status}")
            except Exception as e:
                print(f"[ping] error {e}")

# ---------- запуск ----------
def main() -> None:
    persistence = PicklePersistence(filepath=PERSIST_FILE)
    app = Application.builder().token(BOT_TOKEN).persistence(persistence).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(btn_now, pattern="^now$"))
    app.add_handler(CallbackQueryHandler(send_love, pattern="^love$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # ежедневные напоминания 06:00 и 21:00 по МСК
    app.job_queue.run_daily(
        send_morning,
        time=dt.time(6, 0, tzinfo=MOSCOW),
        name="morning"
    )
    app.job_queue.run_daily(
        send_evening,
        time=dt.time(21, 0, tzinfo=MOSCOW),
        name="evening"
    )

    # фоновый пинг Render
    asyncio.create_task(self_ping())

    print("Bot (MSK + live countdown + 06:00/21:00 + self-ping) started …")
    app.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()
