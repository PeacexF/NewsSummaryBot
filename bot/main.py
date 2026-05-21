from __future__ import annotations

import asyncio
import os
import sys
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.handlers import router as main_router
from log.log import logger

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def start_bot():
    if not BOT_TOKEN:
        logger.error("BOT | Missing `TELEGRAM_BOT_TOKEN` in .env")
        return

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(main_router)

    logger.info("BOT | Telegram bot interface has been started")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(start_bot())