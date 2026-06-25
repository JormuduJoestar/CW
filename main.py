import asyncio

# --- ПАТЧ ДЛЯ PYTHON 3.14 (Arch Linux) ---
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
# -----------------------------------------

import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.db_api import init_db
from handlers import common, posting, statistics, scheduled, templates
import config

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
scheduler = AsyncIOScheduler()

async def on_startup():
    print("--- ЗАПУСК СИСТЕМЫ ---")
    await init_db()
    
    # Запуск планировщика
    scheduler.start()
    print("Планировщик запущен.")

async def main():
    dp.startup.register(on_startup)
    
    # Прокидываем scheduler внутрь хендлеров (чтобы мы могли добавлять задачи)
    dp["scheduler"] = scheduler 
    
    dp.include_router(common.router)
    dp.include_router(posting.router)
    dp.include_router(statistics.router)
    dp.include_router(scheduled.router)
    dp.include_router(templates.router)

    bot.scheduler = scheduler
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
