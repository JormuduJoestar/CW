from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.jobstores.base import JobLookupError
from utils.db_api import get_all_posts_with_status, delete_post_from_db

router = Router()

@router.message(F.text == "⏳ Запланированные")
@router.message(Command("scheduled"))
async def show_scheduled_posts(message: Message):
    posts = await get_all_posts_with_status(message.from_user.id, "scheduled")
    
    if not posts:
        await message.answer("📭 Нет запланированных постов.")
        return

    for post in posts:
        text = (
            f"📅 **Пост #{post.id}**\n"
            f"Время: {post.publish_date.strftime('%d.%m %H:%M')}\n"
            f"Каналов: {len(post.target_channels)}\n"
            f"Удаление: {'Нет' if not post.delete_after_minutes else f'{post.delete_after_minutes} мин.'}"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="❌ Отменить", callback_data=f"cancel_post_{post.id}")
        
        await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("cancel_post_"))
async def cancel_post_handler(callback: CallbackQuery, bot: Bot):
    post_id = int(callback.data.split("_")[2])
    
    job_id = f"post_send_{post_id}"
    try:
        bot.scheduler.remove_job(job_id)
        print(f"Задача {job_id} успешно удалена из планировщика.")
    except JobLookupError:
        print(f"Не удалось найти задачу {job_id} в планировщике. Возможно, она уже выполнена.")

    deleted = await delete_post_from_db(post_id)
    
    if deleted:
        await callback.message.edit_text(f"❌ Пост #{post_id} и его задача на отправку отменены.")
    else:
        await callback.message.edit_text(f"❌ Пост #{post_id} уже был удален или обработан.")
    
    await callback.answer("Отменено")
