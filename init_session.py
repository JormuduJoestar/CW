import asyncio

try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client
import config

API_ID = config.API_ID
API_HASH = config.API_HASH
SESSION_NAME = config.SESSION_NAME

async def main():
    print("Начинаем процесс создания сессии для юзербота...")
    print("Вам потребуется ввести номер телефона, код из Telegram и, возможно, пароль 2FA.")
    
    async with Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH, proxy=config.PROXY) as app:
        me = await app.get_me()
        print("-" * 30)
        print(f"✅ Сессия успешно создана для пользователя: {me.first_name}")
        print(f"   ID: {me.id}")
        print(f"   Username: @{me.username}")
        print("-" * 30)
        print(f"Файл '{SESSION_NAME}.session' был создан в папке проекта.")
        print("Этот скрипт больше запускать не нужно.")

if __name__ == "__main__":
    if not API_ID or not API_HASH:
        print("❌ Ошибка: API_ID и/или API_HASH не указаны в вашем .env файле.")
        print("Пожалуйста, заполните их и попробуйте снова.")
    else:
        try:
            asyncio.run(main())
        except Exception as e:
            print(f"\n❌ Произошла ошибка во время создания сессии: {e}")
