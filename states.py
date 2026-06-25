from aiogram.fsm.state import StatesGroup, State

class ChannelSetup(StatesGroup):
    waiting_for_channel_id = State()

class PostCreation(StatesGroup):
    waiting_for_content = State()
    choosing_channels = State()
    setting_time = State()
    waiting_for_custom_time = State()
    setting_autodelete = State()

class TemplateState(StatesGroup):
    waiting_for_name = State()
    waiting_for_content = State()