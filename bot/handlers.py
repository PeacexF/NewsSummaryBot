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
from database.models import Post, User
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

router = Router()

class ChannelForm(StatesGroup):
    waiting_for_username = State()

class SettingsForm(StatesGroup):
    waiting_for_gemini_key = State()

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

def get_settings_keyboard(has_key: bool) -> InlineKeyboardMarkup:
    buttons = []
    
    if has_key:
        buttons.append([InlineKeyboardButton(text="🔄 Изменить API Ключ", callback_data="set_key_gemini")])
        buttons.append([InlineKeyboardButton(text="🗑 Удалить API Ключ", callback_data="delete_key_gemini")])
    else:
        buttons.append([InlineKeyboardButton(text="🔑 Добавить API Ключ", callback_data="set_key_gemini")])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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

    async with AsyncSessionLocal() as session:
        repo = BotRepository(session)
        user_key = await repo.get_user_api_key(message.from_user.id)

    if not user_key:
        await message.answer(
            "⚠️ *Вы не привязали свой API-ключ Gemini!*\n\n"
            "Пожалуйста, перейдите в раздел `⚙️ Настройки` и добавьте свой личный ключ. "
            "Это безопасно, бесплатно и сделает вас независимым от лимитов сервера.",
            parse_mode="Markdown"
        )
        return
    
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
            "За последние 24 часа в твоих каналах не появилось новых постов, либо ты уже собрал все актуальные сводки.",
            parse_mode="Markdown"
        )
        return


    user_res = await session.execute(select(User).options(joinedload(User.channels)).where(User.id == message.from_user.id))
    user = user_res.unique().scalar_one_or_none()
    channel_ids = [ch.id for ch in user.channels] if user else []

    time_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
    posts_stmt = (
        select(Post)
        .options(joinedload(Post.channel))
        .where(Post.channel_id.in_(channel_ids))
        .where(Post.fetched_at >= time_threshold)
        .order_by(Post.published_at.asc())
    )
    posts_res = await session.execute(posts_stmt)
    all_posts = posts_res.unique().scalars().all()
    from process.filter import NewsFilter
    filtered_posts = NewsFilter(similarity_threshold=0.6, shingle_size=2).filter_duplicates(all_posts)

    ai_summary_text = await summary_service.generate_ai_summary(filtered_posts, user_key)

    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M")
    document_file = BufferedInputFile(
        file_buffer.getvalue(), 
        filename=f"sources_{current_date}.txt"
    )

    await status_message.delete()

    if ai_summary_text:
        await message.answer(
            text=f"✨*ИИ-СВОДКА*✨\n\n{ai_summary_text}",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            text="⚠️ *Ошибка ИИ:* Не удалось сгенерировать сводку через ваш API-ключ. Проверьте его валидность в настройках.",
            parse_mode="Markdown"
        )

    await message.answer_document(
        document=document_file,
        caption="📋 *Файл первоисточников*\nЗдесь собраны полные тексты всех уникальных постов, на которых базировался ИИ.",
        parse_mode="Markdown"
    )


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message, state: FSMContext):
    await state.clear()
    
    async with AsyncSessionLocal() as session:
        repo = BotRepository(session)
        api_key = await repo.get_user_api_key(message.from_user.id)
        
    if api_key:
        visible_len = 4
        masked_key = f"`{api_key[:visible_len]}...{api_key[-visible_len:]}`"
        status_text = f"🟢 *Привязан твой личный ключ:* {masked_key}"
        has_key = True
    else:
        status_text = "🟡 *Используется глобальный ключ сервера* (действуют общие лимиты)."
        has_key = False

    settings_text = (
        "⚙️ *Настройки системы*\n\n"
        f"{status_text}\n\n"
        "Вы можете привязать собственный API-ключ Gemini. Он будет зашифрован "
        "и использован исключительно для обработки ваших личных запросов, делая работу абсолютно независимой."
    )
    
    await message.answer(
        text=settings_text, 
        parse_mode="Markdown", 
        reply_markup=get_settings_keyboard(has_key)
    )

@router.callback_query(F.data == "set_key_gemini")
async def process_set_key_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(SettingsForm.waiting_for_gemini_key)
    
    await callback.message.answer(
        "🔑 *Отправь мне свой API-ключ Gemini.*\n\n"
        "Получить бесплатный ключ можно в Google AI Studio.\n"
        "Строка ключа обычно начинается с `AIzaSy...`\n\n"
        "Для отмены отправь любую команду из главного меню.",
        parse_mode="Markdown"
    )


@router.message(SettingsForm.waiting_for_gemini_key)
async def process_gemini_key_input(message: Message, state: FSMContext):
    raw_key = message.text.strip()
    
    if raw_key in ["📋 Мои каналы", "➕ Добавить канал", "🔍 Собрать сводку сейчас", "⚙️ Настройки", "ℹ️ Информация"]:
        await state.clear()
        await message.answer("Ввод API-ключа отменен.")
        return

    if not raw_key.startswith("AIzaSy") or len(raw_key) < 20:
        await message.answer(
            "❌ *Непохоже на валидный ключ Gemini.*\n"
            "Ключ от Google AI Studio должен начинаться с `AIzaSy` и быть достаточно длинным. "
            "Попробуй скопировать заново или нажми кнопку меню для отмены.",
            parse_mode="Markdown"
        )
        return

    async with AsyncSessionLocal() as session:
        repo = BotRepository(session)
        success = await repo.update_user_api_key(message.from_user.id, raw_key)
        
    if success:
        await message.answer("*Ваш API-ключ успешно зашифрован и сохранен!* Теперь бот будет использовать его.", parse_mode="Markdown")
        await state.clear()
    else:
        await message.answer("Произошла ошибка при сохранении ключа. Попробуйте позже.")
        await state.clear()


@router.callback_query(F.data == "delete_key_gemini")
async def process_delete_key_callback(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        repo = BotRepository(session)
        success = await repo.delete_user_api_key(callback.from_user.id)
        
    if success:
        await callback.answer("Ключ успешно удален", show_alert=True)
        settings_text = (
            "⚙️ *Настройки системы*\n\n"
            "*API Ключ успешно удален.*\n"
            "*Используется глобальный ключ сервера* (действуют общие лимиты)."
        )
        await callback.message.edit_text(
            text=settings_text,
            parse_mode="Markdown",
            reply_markup=get_settings_keyboard(has_key=False)
        )
    else:
        await callback.answer("Ошибка: у вас не было привязанного ключа", show_alert=True)

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
        "Поддержать создателя: [Cryptobot_USDT](https://t.me/send?start=IV3YZQmgcBKf) "
    )
    await message.answer(info_text, parse_mode="Markdown")

@router.message()
async def echo_unhandled(message: Message, state: FSMContext):
    await message.answer("неразпознал твое сообщение / комманду :(")