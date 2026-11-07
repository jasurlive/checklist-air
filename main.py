"""Entry point: python main.py (long polling)."""
import asyncio
import logging
import os
from pathlib import Path

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, CallbackQuery, Message

from db import Database
from handlers import router

BASE = Path(__file__).parent


def load_env(path: Path):
    """Minimal .env reader (KEY=VALUE lines); real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class AccessMiddleware(BaseMiddleware):
    """If ALLOWED_USERS is set, only those Telegram IDs can use the bot."""

    def __init__(self, allowed: set[int]):
        self.allowed = allowed

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if self.allowed and (user is None or user.id not in self.allowed):
            if isinstance(event, Message):
                await event.answer(
                    f"⛔ Access denied. Send this ID to the admin: <code>{user.id}</code>\n"
                    f"⛔ Доступ запрещён. Отправьте этот ID администратору: <code>{user.id}</code>"
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Access denied / Доступ запрещён", show_alert=True)
            return None
        return await handler(event, data)


COMMANDS = {
    "en": [("start", "Start / main menu"), ("new", "New flight"), ("flights", "My flights"),
           ("name", "Change my name"), ("lang", "Language"), ("cancel", "Cancel current input")],
    "ru": [("start", "Старт / главное меню"), ("new", "Новый рейс"), ("flights", "Мои рейсы"),
           ("name", "Изменить имя"), ("lang", "Язык"), ("cancel", "Отменить ввод")],
}


async def set_commands(bot: Bot):
    """Command menu in Telegram: English by default, Russian for Russian-language Telegram apps."""
    for lang, items in COMMANDS.items():
        cmds = [BotCommand(command=c, description=d) for c, d in items]
        await bot.set_my_commands(cmds, language_code=None if lang == "en" else lang)


async def cleanup_loop(db: Database, days: int):
    while True:
        try:
            removed = await db.cleanup(days)
            if removed:
                logging.info("cleanup: removed %d flight(s) older than %d days", removed, days)
        except Exception:
            logging.exception("cleanup failed")
        await asyncio.sleep(3600)


async def main():
    load_env(BASE / ".env")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN is not set (see .env.example)")
    allowed = {int(x) for x in os.environ.get("ALLOWED_USERS", "").replace(" ", "").split(",") if x}
    days = int(os.environ.get("RETENTION_DAYS", "3"))
    db_path = os.environ.get("DB_PATH") or str(BASE / "data.sqlite3")

    db = Database(db_path)
    await db.connect()

    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(db=db)
    dp.message.outer_middleware(AccessMiddleware(allowed))
    dp.callback_query.outer_middleware(AccessMiddleware(allowed))
    dp.include_router(router)

    cleaner = asyncio.create_task(cleanup_loop(db, days))
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await set_commands(bot)
        await dp.start_polling(bot)
    finally:
        cleaner.cancel()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
