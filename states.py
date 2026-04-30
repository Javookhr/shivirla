from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    age = State()
    name = State()
    username = State()
    password = State()
    password_confirm = State()
    gender = State()
    photo = State()


class EditProfile(StatesGroup):
    choosing = State()
    name = State()
    username = State()
    password = State()
    password_confirm = State()
    age = State()
    gender = State()
    photo = State()


class ChatState(StatesGroup):
    in_friend_chat = State()
    in_group_chat = State()
    in_couple_chat = State()
    in_lover_chat = State()


class AdminState(StatesGroup):
    channel_name = State()
    channel_username = State()
    channel_id = State()
    broadcast_content = State()
    broadcast_confirm = State()


class FindUser(StatesGroup):
    username = State()
    message_text = State()


class VoiceIntro(StatesGroup):
    recording = State()


class InterestsState(StatesGroup):
    selecting = State()
