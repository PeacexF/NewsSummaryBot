# There is no logging for the bot messages and messages from users, only technical server side stuff.
# There never will be for privacy reasons.
# I value it a lot and i think that the client's / user's privacy should be respected
# Also, it accepts API Keys, which is the second reason for 'no logging'
# `python bot/main.py` to start the bot

from __future__ import annotations

import asyncio
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.handlers import router as main_router
from log.log import logger
from database.database import init_models, AsyncSessionLocal

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def start_bot():
    if not BOT_TOKEN:
        logger.error("BOT | Missing `TELEGRAM_BOT_TOKEN` in .env")
        return
    
    logger.info("BOT | Initializing database tables...")
    await init_models()

    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(main_router)

    logger.info("BOT | Telegram bot interface has been started")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(start_bot())