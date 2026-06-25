from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def main_menu_kb():
    """Главное меню"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="📝 Создать пост")
    builder.button(text="📂 Шаблоны")
    builder.button(text="📢 Мои каналы")
    builder.button(text="⏳ Запланированные")
    builder.button(text="📊 Статистика")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def content_selection_kb():
    """Кнопки при создании поста (можно выбрать шаблон)"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📂 Загрузить из шаблона", callback_data="pick_template_for_post")
    builder.adjust(1)
    return builder.as_markup()

def templates_management_kb():
    """Меню управления шаблонами"""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Создать шаблон", callback_data="create_template")
    builder.button(text="🗑 Удалить шаблон", callback_data="delete_template_menu")
    builder.adjust(1)
    return builder.as_markup()

def templates_list_kb(templates, mode="load"):
    """
    Список шаблонов.
    mode="load" -> callback=load_tpl_ID
    mode="delete" -> callback=del_tpl_ID
    """
    builder = InlineKeyboardBuilder()
    for tpl in templates:
        prefix = "load_tpl" if mode == "load" else "del_tpl"
        builder.button(text=tpl.name, callback_data=f"{prefix}_{tpl.id}")
    
    builder.button(text="❌ Отмена", callback_data="cancel_creation")
    builder.adjust(1)
    return builder.as_markup()

def channels_select_kb(channels_list, selected_ids: set):
    builder = InlineKeyboardBuilder()
    for ch in channels_list:
        marker = "✅" if ch.id in selected_ids else "❌"
        builder.button(text=f"{marker} {ch.title}", callback_data=f"channel_{ch.id}")
    builder.button(text="Далее ➡️", callback_data="confirm_channels")
    builder.button(text="❌ Отмена", callback_data="cancel_creation") 
    builder.adjust(1)
    return builder.as_markup()

def time_selection_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Опубликовать сейчас", callback_data="time_now")
    builder.button(text="📅 Выбрать дату и время", callback_data="time_custom")
    builder.button(text="❌ Отмена", callback_data="cancel_creation")
    builder.adjust(1)
    return builder.as_markup()