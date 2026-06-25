from datetime import datetime, timedelta
from aiogram import Bot
from utils.db_api import get_post_for_sending, update_post_status, async_session, post_channels_association, save_message_id
from sqlalchemy import update
from parser import collect_and_save_views

async def delete_post_task(bot: Bot, channel_id: int, message_id: int, post_id: int):
    """
    Задача на удаление поста. Теперь она сначала собирает статистику.
    """
    try:
        print(f"Запущена задача на удаление поста #{post_id}. Сначала собираем статистику...")
        await collect_and_save_views(post_id)
        
        print(f"Статистика для поста #{post_id} собрана. Удаляем сообщение из канала {channel_id}...")
        await bot.delete_message(chat_id=channel_id, message_id=message_id)
        print(f"  -> Сообщение {message_id} удалено.")
        
    except Exception as e:
        print(f"❌ Ошибка в задаче delete_post_task для поста #{post_id}: {e}")
    finally:
        await update_post_status(post_id, "deleted")
        print(f"Пост #{post_id} помечен как 'deleted'.")

async def send_post_task(bot: Bot, post_id: int, scheduler):
    """Задача на отправку поста"""
    post = await get_post_for_sending(post_id)
    if not post:
        print(f"Пост {post_id} не найден (возможно, отменен). Задача не будет выполнена.")
        return

    print(f"🚀 Начинаю рассылку поста #{post_id}...")

    for channel in post.target_channels:
        try:
            msg = None
            
            if post.media_type == 'photo' and post.media_file_id:
                msg = await bot.send_photo(
                    chat_id=channel.channel_telegram_id,
                    photo=post.media_file_id,
                    caption=post.content or ""
                )
            elif post.media_type == 'video' and post.media_file_id:
                msg = await bot.send_video(
                    chat_id=channel.channel_telegram_id,
                    video=post.media_file_id,
                    caption=post.content or ""
                )
            elif post.content:
                msg = await bot.send_message(
                    chat_id=channel.channel_telegram_id,
                    text=post.content
                )
                
            if msg:
                await save_message_id(
                    post_id=post.id,
                    channel_db_id=channel.id,
                    message_id=msg.message_id
                )
                print(f"  -> Успешно отправлено в '{channel.title}'. Message ID: {msg.message_id} сохранен.")
            else:
                print(f"  -> ⚠️ Пост #{post_id} был пустым, отправка в '{channel.title}' пропущена.")
                continue

            if post.delete_after_minutes and post.delete_after_minutes > 0:
                run_date = datetime.now() + timedelta(minutes=post.delete_after_minutes)
                
                job_id = f"del_{post.id}_{channel.id}"

                scheduler.add_job(
                    delete_post_task,
                    "date",
                    run_date=run_date,
                    id=job_id,
                    kwargs={
                        "bot": bot, 
                        "channel_id": channel.channel_telegram_id, 
                        "message_id": msg.message_id,
                        "post_id": post.id
                    }
                )
                print(f"  -> ⏰ Удаление из канала '{channel.title}' (задача {job_id}) запланировано на {run_date}")

        except Exception as e:
            print(f"❌ Ошибка отправки поста #{post_id} в канал '{channel.title}': {e}")

    await update_post_status(post_id, "published")
    print(f"✅ Рассылка поста #{post_id} завершена.")
