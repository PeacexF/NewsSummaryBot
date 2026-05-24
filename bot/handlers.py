# Handlers for the bot
# Has FSM state and is connected to the DB
# Will make an ENG version in the future


from __future__ import annotations

from datetime import datetime
from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile

from database.database import AsyncSessionLocal
from database.bot_repo import BotRepository
from bot.services import SummaryService


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
            KeyboardButton(text="🔍 Собрать сводку сейчас")     # To start the collection immediately
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

    await message.answer(
        "📝 **Отправь мне юзернейм канала**\n\n"
        "Например, если канал доступен по ссылке `t.me/durov`, то отправь мне просто `durov` или `@durov`.",
        parse_mode="Markdown"
    )

@router.message(ChannelForm.waiting_for_username)
async def process_channel_username(message: Message, state: FSMContext):
    username_input = message.text.strip()
    
    if username_input in ["📋 Мои каналы", "➕ Добавить канал", "🔍 Собрать сводку сейчас", "⚙️ Настройки"]:
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

@router.message(F.text == "🔍 Собрать сводку сейчас")
async def manual_summary_trigger(message: Message, state: FSMContext):
    # Does a full data cycle to display a summary
    await state.clear()

    status_message = await message.answer(
        "⏳ *Запускаю сбор новостей и фильрацию...*\n\n"
        "Беру данные с RSSHub, проверяю базу данных и запускаю все процессы для работы с данными.\n"
        "Это займет менее 20 секунд.",  # realistically less than 10 or even 5 seconds, but okay, python is slow right? right?
        parse_mode="Markdown"
        )

    async with AsyncSessionLocal() as session:
        summary_service = SummaryService(session)
        
        file_buffer = await summary_service.generate_user_txt_summary(message.from_user.id)
    
    if not file_buffer:
        await status_message.delete()
        await message.answer(
            "📭 *Твоя лента пуста!*\n\n"
            "За последние 24 часа в твоих каналах не появилось новых постов, "
            "либо ты уже собрал все актуальные сводки.",
            parse_mode="Markdown"
        )
        return

    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M")
    document_file = BufferedInputFile(
        file_buffer.getvalue(), 
        filename=f"sources_{current_date}.txt"
    )

    await status_message.delete()
    await message.answer_document(
        document=document_file,
        caption="📋 *Твоя сводка первоисточников готова!*\n\nВ файле собраны все свежие посты из каналов на твоем мониторинге",  parse_mode="Markdown"
    )


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
        "Функции и другая информация о боте доступна по [ссылке на документацию](https://github.com/PeacexF/NewsSummaryBot/tree/main/Documentation)\n"
        "Также есть гайд на получение бесплатных API ключей на [гитхабе](https://github.com/PeacexF/NewsSummaryBot/tree/main/Documentation/Manuals) и в телеграм [статье]()\n"
        "Поддержать создателя:"
    )
    await message.answer(info_text, parse_mode="Markdown")

@router.message()
async def echo_unhandled(message: Message, state: FSMContext):
    await message.answer("неразпознал твое сообщение / комманду :(")