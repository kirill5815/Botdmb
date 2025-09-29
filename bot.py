#!/usr/bin/env python3
import os
import random
import datetime as dt
import asyncio
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    PicklePersistence,
    MessageHandler,
    filters,
)


BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не задана")

MOSCOW = pytz.timezone("Europe/Moscow")
PERSIST_FILE = "bot_data.pickle"

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
        [InlineKeyboardButton("💌 Трогательное письмо", callback_data="love")]
    ])

# ---------- обратный отсчёт ----------
def format_countdown(target_date: dt.date) -> str:
    """Возвращает строку дн. чч:мм:сс до целевой даты по МСК."""
    now = dt.datetime.now(MOSCOW)
    target_dt = MOSCOW.localize(dt.datetime.combine(target_date, dt.time(0, 0)))
    delta = target_dt - now
    if delta.total_seconds() <= 0:
        return "🎉 Дембель настал!"
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    mins, secs = divmod(rem, 60)
    return f"До встречи: {days} дн. {hours:02d}:{mins:02d}:{secs:02d}"

# ---------- команды ----------
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = ctx.bot_data.setdefault(user.id, {})
    if "date" not in data:
        # просим дату, если ещё не задана
        await update.message.reply_text("Введи дату дембеля в формате ДД.ММ.ГГГГ")
        data["expect_date"] = True
        return

    # сразу показываем счётчик
    msg = await update.message.reply_text(
        format_countdown(dt.date.fromisoformat(data["date"])),
        reply_markup=main_kb()
    )
    # запускаем ежесекундное обновление
    ctx.job_queue.run_repeating(
        update_countdown,
        interval=1,
        first=0,
        data={"chat_id": msg.chat_id, "message_id": msg.message_id},
        name=f"countdown_{user.id}"
    )

async def update_countdown(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_data = context.job.data
    user_id = context.job.name.split("_")[1]
    user_data = context.application.bot_data.get(int(user_id), {})
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
    except Exception as e:
        # сообщение могли удалить
        context.job.schedule_removal()

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
        # показываем счётчик
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

async def send_love(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await ctx.bot.send_message(
        update.effective_chat.id,
        text=random.choice(LOVE_LINES)
    )

# ---------- запуск ----------
def main() -> None:
    persistence = PicklePersistence(filepath=PERSIST_FILE)
    app = Application.builder().token(BOT_TOKEN).persistence(persistence).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(send_love, pattern="^love$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("Bot (MSK + live countdown) started …")
    app.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()
