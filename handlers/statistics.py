# statistics.py
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, func
from utils.db_api import async_session, Post, Statistics, get_all_posts_with_status
from parser import collect_and_save_views # Импортируем наш парсер

router = Router()

@router.message(F.text == "📊 Статистика")
@router.message(Command("stats"))
async def show_statistics(message: Message, bot: Bot):
    user_id = message.from_user.id
    
    # 1. Отправляем пользователю уведомление о начале сбора данных
    wait_message = await message.answer("🔄 Собираю актуальные данные по активным постам, пожалуйста, подождите...")

    # 2. Получаем 5 последних активных постов для сбора "живой" статистики
    # Ограничение в 5 постов необходимо, чтобы избежать долгого ожидания и бана от Telegram
    published_posts = await get_all_posts_with_status(user_id, "published")
    # Сортируем по ID, чтобы взять самые свежие
    posts_to_check = sorted(published_posts, key=lambda p: p.id, reverse=True)[:5]

    if posts_to_check:
        await bot.edit_message_text(
            f"🔄 Проверяю {len(posts_to_check)} последних активных постов...",
            chat_id=wait_message.chat.id,
            message_id=wait_message.message_id
        )
        # Запускаем парсер для каждого поста
        for post in posts_to_check:
            await collect_and_save_views(post.id)

    # 3. Собираем все данные для финального отчета
    scheduled_posts_count = len(await get_all_posts_with_status(user_id, "scheduled"))
    
    # 4. Получаем детальную статистику по всем постам из БД (теперь там есть и обновленные)
    async with async_session() as session:
        query = (
            select(Post, Statistics)
            .outerjoin(Statistics, Post.id == Statistics.post_id) # outerjoin, чтобы включить посты без статистики
            .where(Post.user_id == user_id)
            .order_by(Post.id.desc())
        )
        all_posts_with_stats = await session.execute(query)
        all_posts_with_stats = all_posts_with_stats.all()

    # 5. Формируем финальный отчет
    report = "📊 **Сводка по вашим постам:**\n\n"
    report += f"⏳ Запланировано: <b>{scheduled_posts_count}</b>\n\n"
    
    # Разделяем посты на активные и архивные
    active_report = "<b>✅ Активные посты (статистика обновлена):</b>\n"
    archived_report = "<b>🗄 Архив (статистика на момент удаления):</b>\n"
    
    active_count = 0
    archived_count = 0

    for post, stats in all_posts_with_stats:
        content_preview = (post.content or "Медиа-пост").strip()[:30] + "..."
        views = stats.views_at_delete if stats else 0
        
        if post.status == 'published':
            active_report += f"  • Пост #{post.id} (<em>«{content_preview}»</em>) - 👁 <b>{views}</b>\n"
            active_count += 1
        elif post.status == 'deleted':
            archived_report += f"  • Пост #{post.id} (<em>«{content_preview}»</em>) - 👁 <b>{views}</b>\n"
            archived_count += 1

    if active_count == 0:
        active_report += "  <em>Нет активных постов.</em>\n"
    if archived_count == 0:
        archived_report += "  <em>Архив пуст.</em>\n"
        
    final_report = report + active_report + "\n" + archived_report

    # 6. Отправляем итоговый отчет, редактируя исходное сообщение
    await bot.edit_message_text(
        final_report,
        chat_id=wait_message.chat.id,
        message_id=wait_message.message_id
    )