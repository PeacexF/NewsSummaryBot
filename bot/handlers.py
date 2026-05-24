# Handlers for the bot
# Has FSM state and is connected to the DB
# Will make an ENG version in the future


from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from database.database import AsyncSessionLocal
from database.bot_repo import BotRepository
from log.log import logger # Need to debug state, temporary here


router = Router()

class ChannelForm(StatesGroup):
    waiting_for_username = State()

def get_main_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [
            KeyboardButton(text="📋 Мои каналы"),               # List of user's channels
            KeyboardButton(text="➕ Добавить канал")            # Adding a channel to a list of 'monitored' channels
        ],
        [
            KeyboardButton(text="📝 Собрать сводку сейчас")     # To start the collection immediately
        ],
        [
            KeyboardButton(text="⚙️ Настройки"),                # API keys later and other settings
            KeyboardButton(text="ℹ️ Информация")                # Information about the project
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()     # Clearing state
    async with AsyncSessionLocal() as session:
        repo = BotRepository(session)
        # Adding a user to the database
        await repo.get_or_create_user(message.from_user.id, message.from_user.username)
        
    welcome_text = (
        f"👋 *Привет {message.from_user.first_name}, Я - NewsSummary Bot*\n\n"
        "Я умею собирать посты из Telegram-каналов, "
        "очищать их от мусора, удалять дубликаты и рерайты, "
        "а затем формировать удобные отчеты.\n\n"
        "Используй меню ниже для управления своими подписками 👇"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

@router.message(F.text == "📋 Мои каналы")
async def show_channels(message: Message, state: FSMContext):
    await state.clear()
    async with AsyncSessionLocal() as session:
        repo = BotRepository(session)
        # Getting the user's channels to display them
        user_channels = await repo.get_user_channels(message.from_user.id)
    
    if not user_channels:
        await message.answer("😢 У тебя пока нет добавленных каналов для мониторинга, используй кнопку `Добавить канал`", parse_mode="Markdown")
        return

    await message.answer("🗂 *Твои каналы на мониторинге:*\nНажми кнопку под каналом, если хочешь удалить его из своей ленты:", parse_mode="Markdown")

    for channel in user_channels:
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[  # I will remake the display method, i think it's quite verbose rn
            [InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_ch:{channel.username}")]
        ])
        await message.answer(f"📢 *@{channel.username}*", reply_markup=inline_kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("delete_ch:"))
async def process_delete_channel(callback: CallbackQuery):
    channel_username = callback.data.split(":", 1)[-1]
    
    async with AsyncSessionLocal() as session:
        repo = BotRepository(session)
        success = await repo.remove_channel_from_user(callback.from_user.id, channel_username)
        
    if success:
        await callback.answer(f"Канал удален: {channel_username}")
        await callback.message.delete()
    else:
        await callback.answer("Ошибка: не удалось удалить канал", show_alert=True)

@router.message(F.text == "➕ Добавить канал")
async def request_add_channel(message: Message, state: FSMContext):
    await state.set_state(ChannelForm.waiting_for_username)

    current_state = await state.get_state()
    logger.info(f"FSM | User {message.from_user.id} set state to: {current_state}")

    await message.answer(
        "📝 **Отправь мне юзернейм канала**\n\n"
        "Например, если канал доступен по ссылке `t.me/durov`, то отправь мне просто `durov` или `@durov`.",
        parse_mode="Markdown"
    )

@router.message(ChannelForm.waiting_for_username)
async def process_channel_username(message: Message, state: FSMContext):
    username_input = message.text.strip()
    logger.info(f"FSM | Catching username input {username_input} from user {message.from_user.id}")
    
    if username_input in ["📋 Мои каналы", "➕ Добавить канал", "🚀 Собрать сводку сейчас", "⚙️ Настройки"]:
        await state.clear()
        await message.answer("Добавление канала отменено")
        return
    
    async with AsyncSessionLocal() as session:
        repo = BotRepository(session)
        success = await repo.add_channel_to_user(message.from_user.id, username_input)
        
    if success:
        clean_name = username_input.replace("@", "").replace("https://", "").split("/")[-1]
        await message.answer(f"✅ *@{clean_name}* успешно добавлен в твой список", parse_mode="Markdown")
        await state.clear()     # Exiting state
    else:
        await message.answer("Этот канал уже есть в твоем списке. Попробуй другой")

@router.message(F.text == "📝 Собрать сводку сейчас")
async def manual_summary_trigger(message: Message):
    # Absolutely useless currently and isn't doing anything
    # It's just sending a message rn 
    await message.answer(
        "⏳ *Запускаю сбор новостей и фильрацию...*\n\n"
        "Беру данные с RSSHub, проверяю базу данных и запускаю все процессы для работы с данными.\n"
        "Это займет менее 30 секунд.",
        parse_mode="Markdown"
        )
    
    await message.answer("🛠 *Здесь будет отправка готового .txt файла source*", parse_mode="Markdown")


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
    # Settings display
    # need to add buttons for actual good and comfortable UI
    settings_text = (
        "⚙️ *Настройки системы*\n\n"
        "🤖 *Текущая LLM:* Gemini 1.5 Flash (Default)\n"
        "🔑 *API Ключ:* Используется глобальный ключ сервера.\n\n"
        "ℹ️ _В следующих обновлениях сюда будет добавлен раздел для привязки твоего личного API-ключа, "
        "чтобы сделать использование бота полностью бесплатным и независимым от лимитов сервера и смена языка_"
    )
    await message.answer(settings_text, parse_mode="Markdown")

@router.message(F.text == "ℹ️ Информация")
async def show_info(message: Message):
    # Info and useful manuals
    # Link to the repo & documentation
    info_text = (
        "Данный проект разрабатывается с целью создания удобного интерфейса для чтения новостей\n\n"
        "*Статус:* Проект находится на этапе разработки\n\n"
        "Открытый исходный код можно посмотреть по [ссылке на репозиторий](https://github.com/PeacexF/NewsSummaryBot)\n\n"
        "*Политика*: *BYOK*. Вы приносите свой ключ от LLM(нейронки), который позже используете только вы и только для своих запросов. Ключи зашифрованы и находятся на защищенном сервере\n\n"
        "Список поддерживаемых Нейросетей:\n"
        "> Gemini etc...\n\n"
        "Функции и другая информация о боте доступна по [ссылке на документацию]()\n"
        "Также есть [гайд]() на получение бесплатных API ключей\n"
        "Поддержать создателя:"
    )
    await message.answer(info_text, parse_mode="Markdown")

@router.message()
async def echo_unhandled(message: Message, state: FSMContext):
    current_state = await state.get_state()
    logger.warning(f"FSM | Unhandled message, Text: {message.text} Current User State: {current_state}")
    await message.answer("неразпознал твое сообщение / комманду. Или ты отправил ссылку на канал в неправильном формате")