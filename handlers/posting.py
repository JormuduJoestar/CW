from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states import PostCreation
from utils.db_api import get_user_channels, create_post_in_db, get_user_templates, Template
from keyboards.builders import channels_select_kb, time_selection_kb, main_menu_kb, content_selection_kb, templates_list_kb
from utils.scheduler_tasks import send_post_task
from sqlalchemy import select
from utils.db_api import async_session

router = Router()

@router.message(F.text == "📝 Создать пост")
async def start_posting(message: Message, state: FSMContext):
    await message.answer(
        "Отправьте контент (текст/фото) ИЛИ выберите шаблон:",
        reply_markup=content_selection_kb()
    )
    await state.set_state(PostCreation.waiting_for_content)

@router.callback_query(F.data == "pick_template_for_post")
async def show_templates_for_post(callback: CallbackQuery):
    tpls = await get_user_templates(callback.from_user.id)
    if not tpls:
        await callback.answer("У вас нет шаблонов. Создайте их в меню 'Шаблоны'.", show_alert=True)
        return
    
    await callback.message.edit_text(
        "Выберите шаблон:",
        reply_markup=templates_list_kb(tpls, mode="load")
    )

@router.callback_query(F.data.startswith("load_tpl_"))
async def load_template_data(callback: CallbackQuery, state: FSMContext):
    tpl_id = int(callback.data.split("_")[2])
    
    async with async_session() as session:
        res = await session.execute(select(Template).where(Template.id == tpl_id))
        tpl = res.scalar_one_or_none()
    
    if not tpl:
        await callback.answer("Ошибка: шаблон не найден")
        return

    data = {
        'user_id': callback.from_user.id,
        'text': tpl.content,
        'media_id': tpl.media_file_id,
        'media_type': tpl.media_type
    }
    
    await state.update_data(post_data=data, selected_channels=set())
    
    channels = await get_user_channels(callback.from_user.id)
    if not channels:
        await callback.message.edit_text("Нет каналов.")
        await state.clear()
        return

    await callback.message.edit_text(
        f"Шаблон «{tpl.name}» загружен.\nВыберите каналы:",
        reply_markup=channels_select_kb(channels, set())
    )
    await state.set_state(PostCreation.choosing_channels)


@router.message(PostCreation.waiting_for_content)
async def process_content(message: Message, state: FSMContext):
    data = {}
    
    if message.photo:
        data['media_id'] = message.photo[-1].file_id
        data['media_type'] = 'photo'
        data['text'] = message.caption
    elif message.video:
        data['media_id'] = message.video.file_id
        data['media_type'] = 'video'
        data['text'] = message.caption
    elif message.text:
        data['media_id'] = None
        data['media_type'] = 'text'
        data['text'] = message.text
    else:
        await message.answer("⚠️ Текст, фото или видео.")
        return

    data['user_id'] = message.from_user.id
    await state.update_data(post_data=data, selected_channels=set())

    channels = await get_user_channels(message.from_user.id)
    if not channels:
        await message.answer("Нет каналов.", reply_markup=main_menu_kb())
        await state.clear()
        return

    await message.answer(
        "Выберите каналы:",
        reply_markup=channels_select_kb(channels, set())
    )
    await state.set_state(PostCreation.choosing_channels)

@router.callback_query(PostCreation.choosing_channels, F.data.startswith("channel_"))
async def toggle_channel(callback: CallbackQuery, state: FSMContext):
    channel_db_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    selected = data['selected_channels']
    if channel_db_id in selected:
        selected.remove(channel_db_id)
    else:
        selected.add(channel_db_id)
    await state.update_data(selected_channels=selected)
    channels = await get_user_channels(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=channels_select_kb(channels, selected))
    await callback.answer()

@router.callback_query(PostCreation.choosing_channels, F.data == "confirm_channels")
async def confirm_channels_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data['selected_channels']:
        await callback.answer("Выберите канал!", show_alert=True)
        return
    await callback.message.answer("Когда опубликовать?", reply_markup=time_selection_kb())
    await callback.message.delete()
    await state.set_state(PostCreation.setting_time)

@router.callback_query(PostCreation.setting_time, F.data == "time_now")
async def set_time_now(callback: CallbackQuery, state: FSMContext):
    publish_time = datetime.now() + timedelta(seconds=10)
    data = await state.get_data()
    post_data = data['post_data']
    post_data['publish_date'] = publish_time
    post_data['channels'] = list(data['selected_channels'])
    await state.update_data(post_data=post_data)
    await callback.message.answer("⏱ Таймер удаления (мин)? 0 - нет.")
    await state.set_state(PostCreation.setting_autodelete)

@router.callback_query(PostCreation.setting_time, F.data == "time_custom")
async def set_time_custom_ask(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите: ДД.ММ ЧЧ:ММ\nПример: 15.02 14:30\n_(/cancel для отмены)_")
    await state.set_state(PostCreation.waiting_for_custom_time)

@router.message(PostCreation.waiting_for_custom_time)
async def process_custom_time(message: Message, state: FSMContext):
    try:
        now = datetime.now()
        entered_time = datetime.strptime(message.text, "%d.%m %H:%M").replace(year=now.year)
        if entered_time < now:
            await message.answer("Дата в прошлом.")
            return
        data = await state.get_data()
        post_data = data['post_data']
        post_data['publish_date'] = entered_time
        post_data['channels'] = list(data['selected_channels'])
        await state.update_data(post_data=post_data)
        await message.answer(f"Дата: {entered_time}\n⏱ Таймер удаления (мин)? 0 - нет.")
        await state.set_state(PostCreation.setting_autodelete)
    except ValueError:
        await message.answer("Неверный формат.")

@router.message(PostCreation.setting_autodelete)
async def finish_post(message: Message, state: FSMContext, bot: Bot):
    try:
        minutes = int(message.text)
    except ValueError:
        await message.answer("Число.")
        return
    data = await state.get_data()
    post_data = data['post_data']
    
    post_data['delete_after'] = minutes if minutes > 0 else None
    
    post_id = await create_post_in_db(post_data)
    
    if post_id and hasattr(bot, 'scheduler'):
        job_id = f"post_send_{post_id}"
        bot.scheduler.add_job(
            send_post_task,
            trigger="date",
            run_date=post_data['publish_date'],
            id=job_id,
            misfire_grace_time=30,
            kwargs={"bot": bot, "post_id": post_id, "scheduler": bot.scheduler}
        )
        await message.answer(f"✅ Пост #{post_id} запланирован!", reply_markup=main_menu_kb())
    else:
        await message.answer("❌ Произошла ошибка при сохранении поста.")

    await state.clear()
"""
    post_data['delete_after'] = minutes if minutes > 0 else None
    post_id = await create_post_in_db(post_data)
    if hasattr(bot, 'scheduler'):
        bot.scheduler.add_job(send_post_task, trigger="date", run_date=post_data['publish_date'], kwargs={"bot": bot, "post_id": post_id, "scheduler": bot.scheduler})
    await message.answer(f"✅ Пост #{post_id} готов!", reply_markup=main_menu_kb())
    await state.clear()
"""
