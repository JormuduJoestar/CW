from aiogram import Router, F, Bot
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from utils.db_api import register_user
from keyboards.builders import main_menu_kb
from aiogram.fsm.context import FSMContext
from states import ChannelSetup

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await register_user(message.from_user.id, message.from_user.username)
    
    await message.answer(
        "Привет! 👋 Я бот для управления твоими каналами.\n\n"
        "1. Сначала добавь меня в канал администратором.\n"
        "2. Нажми '📢 Мои каналы', чтобы добавить канал сюда.\n"
        "3. Потом жми '📝 Создать пост'.",
        reply_markup=main_menu_kb()
    )


@router.message(F.text == "📢 Мои каналы")
async def show_my_channels(message: Message):
    await message.answer(
        "Чтобы добавить новый канал:\n"
        "1. Добавь меня в администраторы канала.\n"
        "2. Нажми /add_channel (или напиши эту команду).\n"
        "3. Перешли мне любой пост из этого канала."
    )

@router.message(Command("cancel"))
@router.message(F.text.casefold() == "отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять.", reply_markup=main_menu_kb())
        return

    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=main_menu_kb())

@router.callback_query(F.data == "cancel_creation")
async def callback_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("❌ Создание поста отменено.", reply_markup=main_menu_kb())
    await callback.answer()

@router.message(Command("add_channel"))
async def start_add_channel(message: Message, state: FSMContext):
    await message.answer(
        "Перешли мне любое сообщение из твоего канала или отправь его ID (начинается с -100...)."
    )
    await state.set_state(ChannelSetup.waiting_for_channel_id)

@router.message(ChannelSetup.waiting_for_channel_id)
async def process_channel_id(message: Message, state: FSMContext, bot: Bot):
    channel_id = None
    title = "Новый канал"

    if message.forward_from_chat:
        channel_id = message.forward_from_chat.id
        title = message.forward_from_chat.title
    elif message.text and message.text.startswith("-100"):
        try:
            channel_id = int(message.text)
        except ValueError:
            await message.answer("Неверный формат ID. Попробуйте переслать сообщение из канала.")
            return
    else:
        await message.answer("Не могу распознать канал. Пожалуйста, перешлите мне сообщение из него.")
        return

    if channel_id:
        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
            if member.status != ChatMemberStatus.ADMINISTRATOR:
                await message.answer("❌ Ошибка: я не являюсь администратором в этом канале. Сначала дайте мне права.")
                return
        except Exception as e:
            await message.answer(f"❌ Не удалось проверить статус в канале. Убедитесь, что ID верный и я там есть.\n_{e}_")
            return
        
        from utils.db_api import add_channel
        is_added = await add_channel(message.from_user.id, channel_id, title)
        
        if is_added:
            await message.answer(f"✅ Канал «{title}» успешно добавлен!")
        else:
            await message.answer("Этот канал уже был добавлен ранее.")
        
        await state.clear()
