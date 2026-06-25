import asyncio

try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client
from pyrogram.errors import FloodWait, ChannelPrivate, ChannelInvalid

import config
from utils.db_api import get_messages_for_post_parsing, update_or_create_statistics 

API_ID = config.API_ID
API_HASH = config.API_HASH
SESSION_NAME = config.SESSION_NAME

PARSER_LOCK = asyncio.Lock()

async def collect_and_save_views(post_id: int):
    async with PARSER_LOCK:
        print(f"[Парсер] Получена задача: собрать просмотры для поста #{post_id}")
        
        messages_to_check = await get_messages_for_post_parsing(post_id)
        
        if not messages_to_check:
            print(f"[Парсер] Для поста #{post_id} не найдено отправленных сообщений. Пропускаем.")
            await update_or_create_statistics(post_id=post_id, views=0) 
            return

        total_views = 0
        
        try:
            async with Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH) as app:
                print(f"[Парсер] Юзербот '{SESSION_NAME}' запущен.")
                
                unique_channel_ids = {chat_id for chat_id, msg_id in messages_to_check}
                print(f"[Парсер] Необходимо проверить каналы: {list(unique_channel_ids)}. Прогреваем кэш...")
                
                async for dialog in app.get_dialogs():
                    if not unique_channel_ids:
                        break
                    if dialog.chat and dialog.chat.id in unique_channel_ids:
                        print(f"  -> Кэш для канала '{dialog.chat.title}' ({dialog.chat.id}) прогрет.")
                        unique_channel_ids.remove(dialog.chat.id)
                
                if unique_channel_ids:
                    print(f"  -> ⚠️ Внимание: Не удалось найти в диалогах каналы: {list(unique_channel_ids)}")

                for chat_id, message_id in messages_to_check:
                    try:
                        msg_object = await app.get_messages(chat_id=chat_id, message_ids=message_id)
                        
                        if msg_object and msg_object.views:
                            total_views += msg_object.views
                            print(f"  -> Канал {chat_id}, Сообщение {message_id}: найдено {msg_object.views} просмотров.")
                        else:
                            print(f"  -> Канал {chat_id}, Сообщение {message_id}: не удалось получить просмотры (сообщение удалено?).")

                    except Exception as e:
                        print(f"  -> ⚠️ Предупреждение при получении сообщения {message_id} из канала {chat_id}: {e}")

        except Exception as e:
            print(f"❌ Критическая ошибка при инициализации или работе юзербота: {e}")

        await update_or_create_statistics(post_id=post_id, views=total_views) 


if __name__ == '__main__':
    pass
