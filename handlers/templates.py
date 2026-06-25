from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states import TemplateState
from utils.db_api import create_template, get_user_templates, delete_template
from keyboards.builders import templates_management_kb, templates_list_kb, main_menu_kb

router = Router()

# 1. Вход в меню шаблонов
@router.message(F.text == "📂 Шаблоны")
async def open_templates_menu(message: Message):
    await message.answer("Управление шаблонами:", reply_markup=templates_management_kb())

# 2. Создание шаблона - Шаг 1: Имя
@router.callback_query(F.data == "create_template")
async def ask_template_name(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите название для нового шаблона:")
    await state.set_state(TemplateState.waiting_for_name)

# Шаг 2: Имя получено, ждем контент
@router.message(TemplateState.waiting_for_name)
async def ask_template_content(message: Message, state: FSMContext):
    await state.update_data(tpl_name=message.text)
    await message.answer("Теперь пришлите текст или фото с подписью для шаблона.")
    await state.set_state(TemplateState.waiting_for_content)

# Шаг 3: Сохранение
@router.message(TemplateState.waiting_for_content)
async def save_new_template(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data['tpl_name']
    
    content_text = message.text or message.caption
    media_id = None
    media_type = 'text'
    
    if message.photo:
        media_id = message.photo[-1].file_id
        media_type = 'photo'
    elif message.video:
        media_id = message.video.file_id
        media_type = 'video'
    elif not content_text:
        await message.answer("Пришлите текст, фото или видео.")
        return

    await create_template(message.from_user.id, name, content_text, media_id, media_type)
    await message.answer(f"✅ Шаблон «{name}» сохранен!", reply_markup=main_menu_kb())
    await state.clear()

# 3. Удаление шаблона
@router.callback_query(F.data == "delete_template_menu")
async def show_delete_list(callback: CallbackQuery):
    tpls = await get_user_templates(callback.from_user.id)
    if not tpls:
        await callback.answer("Список пуст", show_alert=True)
        return
    await callback.message.edit_text(
        "Нажмите на шаблон, чтобы удалить его:",
        reply_markup=templates_list_kb(tpls, mode="delete")
    )

@router.callback_query(F.data.startswith("del_tpl_"))
async def delete_tpl_action(callback: CallbackQuery):
    tpl_id = int(callback.data.split("_")[2])
    await delete_template(tpl_id)
    await callback.answer("Шаблон удален")
    await callback.message.edit_text("Удалено.", reply_markup=templates_management_kb())