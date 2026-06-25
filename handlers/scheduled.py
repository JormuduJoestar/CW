from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.jobstores.base import JobLookupError
from utils.db_api import get_all_posts_with_status, delete_post_from_db

router = Router()

@router.message(F.text == "⏳ Запланированные") # Реагируем на кнопку
@router.message(Command("scheduled"))           # И на команду
async def show_scheduled_posts(message: Message):
    posts = await get_all_posts_with_status(message.from_user.id, "scheduled")
    
    if not posts:
        await message.answer("📭 Нет запланированных постов.")
        return

    for post in posts:
        # Формируем карточку поста
        text = (
            f"📅 **Пост #{post.id}**\n"
            f"Время: {post.publish_date.strftime('%d.%m %H:%M')}\n"
            f"Каналов: {len(post.target_channels)}\n"
            f"Удаление: {'Нет' if not post.delete_after_minutes else f'{post.delete_after_minutes} мин.'}"
        )
        
        # Кнопка отмены
        builder = InlineKeyboardBuilder()
        builder.button(text="❌ Отменить", callback_data=f"cancel_post_{post.id}")
        
        await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("cancel_post_"))
async def cancel_post_handler(callback: CallbackQuery, bot: Bot):
    post_id = int(callback.data.split("_")[2])
    
    # 1. Сначала пытаемся удалить задачу из планировщика
    job_id = f"post_send_{post_id}"
    try:
        bot.scheduler.remove_job(job_id)
        print(f"Задача {job_id} успешно удалена из планировщика.")
    except JobLookupError:
        print(f"Не удалось найти задачу {job_id} в планировщике. Возможно, она уже выполнена.")

    # 2. А теперь удаляем из БД
    deleted = await delete_post_from_db(post_id)
    
    if deleted:
        await callback.message.edit_text(f"❌ Пост #{post_id} и его задача на отправку отменены.")
    else:
        # Эта ситуация маловероятна, если кнопка еще висит
        await callback.message.edit_text(f"❌ Пост #{post_id} уже был удален или обработан.")
    
    await callback.answer("Отменено")
"""
@router.callback_query(F.data.startswith("cancel_post_"))
async def cancel_post_handler(callback: CallbackQuery, bot: Bot):
    post_id = int(callback.data.split("_")[2])
    
    # 1. Удаляем из БД
    deleted = await delete_post_from_db(post_id)
    
    if deleted:
        # 2. Удаляем из Планировщика (если задача уже там)
        # В APScheduler задачи имеют ID. Мы их не сохраняли явно, 
        # но APScheduler не умеет удалять задачу по аргументам.
        # ХАК: Мы просто удалили пост из БД.
        # Когда планировщик проснется (send_post_task), он попытается достать пост get_post_for_sending(post_id).
        # Функция вернет None.
        # В scheduler_tasks.py у нас есть проверка: if not post: return.
        # ЗНАЧИТ: Задача сработает вхолостую и ничего не отправит. Это безопасно.
        
        await callback.message.edit_text(f"❌ Пост #{post_id} отменен и удален.")
    else:
        await callback.answer("Ошибка: Пост не найден.", show_alert=True)
"""