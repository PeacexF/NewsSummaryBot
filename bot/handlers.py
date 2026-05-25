# Handlers for the bot
# Has FSM state and is connected to the DB
# Will make an ENG version in the future


from __future__ import annotations

from datetime import datetime
from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile, LinkPreviewOptions

from database.database import AsyncSessionLocal
from database.bot_repo import BotRepository
from bot.services import SummaryService
from database.models import Post, User
from process.filter import NewsFilter
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
            KeyboardButton(text="⚙️ Настройки"),                # Settings
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

def get_cancel_adding_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Завершить добавление", callback_data="stop_adding_channels")]
        ]
    )

def build_channels_keyboard(channels: list) -> InlineKeyboardMarkup:
    keyboard_buttons = []
    row = []
    
    for channel in channels:
        btn = InlineKeyboardButton(
            text=f"@{channel.username}", 
            callback_data=f"del_ch:{channel.id}"
        )
        row.append(btn)
        
        if len(row) == 2:
            keyboard_buttons.append(row)
            row = []
            
    if row:
        keyboard_buttons.append(row)
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

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
async def show_user_channels(message: Message, state: FSMContext):
    await state.clear()

    async with AsyncSessionLocal() as session:
        repo = BotRepository(session)
        user_channels = await repo.get_user_channels(message.from_user.id)

    if not user_channels:
        await message.answer(
            "📭 *Ваш список каналов пуст.*\n\n"
            "Используйте кнопку `➕ Добавить канал`, чтобы настроить свою ленту.",
            parse_mode="Markdown"
        )
        return

    reply_markup = build_channels_keyboard(user_channels)
    
    await message.answer(
        "📋 **Ваш список каналов**\n\n"
        "Нажмите на название канала ниже, чтобы удалить его из своей ленты:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

@router.callback_query(F.data.startswith("del_ch:"))
async def process_delete_channel(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        repo = BotRepository(session)
        
        success, channel_username = await repo.remove_channel_from_user(user_id, channel_id)
        
        updated_channels = await repo.get_user_channels(user_id)

    if not success:
        await callback.answer("Ошибка: Канал не найден или уже удален.", show_alert=True)
        return

    await callback.answer(f"Удалено: @{channel_username}")

    if not updated_channels:
        await callback.message.edit_text(
            "📭 *Вы удалили все каналы из подписок.*\n\n"
            "Ваш список теперь пуст.",
            parse_mode="Markdown",
            reply_markup=None
        )
        return

    new_markup = build_channels_keyboard(updated_channels)
    
    try:
        await callback.message.edit_reply_markup(reply_markup=new_markup)
    except Exception:
        pass

@router.message(F.text == "➕ Добавить канал")
async def start_add_channel(message: Message, state: FSMContext):
    await state.set_state(ChannelForm.waiting_for_username)
    await message.answer(
        "📝 **Режим добавления каналов**\n\n"
        "Отправляй мне юзернеймы каналов по одному (например, `durov` или ссылку `https://t.me/rbc_news`).\n\n"
        "Когда закончишь, нажми кнопку ниже 👇",
        parse_mode="Markdown",
        reply_markup=get_cancel_adding_keyboard()
    )

@router.message(ChannelForm.waiting_for_username)
async def process_channel_input(message: Message, state: FSMContext):
    raw_input = message.text.strip()

    if raw_input in ["📋 Мои каналы", "➕ Добавить канал", "🔍 Собрать сводку сейчас", "⚙️ Настройки", "ℹ️ Информация"]:
        await state.clear()
        await message.answer("Добавление каналов завершено.", reply_markup=get_main_keyboard())
        return

    username = raw_input.split("/")[-1].replace("@", "").strip()

    if not username:
        await message.answer("❌ Ссылка или юзернейм пустые. Попробуй еще раз.")
        return

    async with AsyncSessionLocal() as session:
        repo = BotRepository(session)
        success = await repo.add_channel_to_user(message.from_user.id, username)

    if success:
        await message.answer(
            f"✅ Канал **@{username}** успешно добавлен к твоим подпискам!\n\n"
            "Жду следующий канал или нажмите кнопку завершения 👇",
            parse_mode="Markdown",
            reply_markup=get_cancel_adding_keyboard()
        )
    else:
        await message.answer(
            f"ℹ️ Канал **@{username}** уже есть в твоем списке подписок.\n\n"
            "Можешь отправить другой канал:",
            parse_mode="Markdown",
            reply_markup=get_cancel_adding_keyboard()
        )

@router.callback_query(F.data == "stop_adding_channels")
async def cb_stop_adding_channels(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == ChannelForm.waiting_for_username:
        await state.clear()
        await callback.answer("Готово!")
        await callback.message.answer(
            "📥 **Добавление каналов успешно завершено!**\n"
            "Теперь вы можете обновить сводку или проверить список подписок.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await callback.answer("Эта сессия добавления уже неактивна.")

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
        "Беру данные с RSSHub, проверяю базу данных и запускаю все процессы для работы с данными и отправляю в ИИ.\n"
        "Это займет достаточно много времени, можешь пока отойти.",
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

    filtered_posts = NewsFilter(similarity_threshold=0.6, shingle_size=2).filter_duplicates(all_posts)

    async with AsyncSessionLocal() as session_for_ai:
        summary_service = SummaryService(session_for_ai)
        ai_summary_text = await summary_service.generate_ai_summary(filtered_posts, user_key)

    current_date = datetime.now().strftime("%Y-%m-%d_%H-%M")
    document_file = BufferedInputFile(
        file_buffer.getvalue(), 
        filename=f"sources_{current_date}.txt"
    )

    await status_message.delete()

    if ai_summary_text:
        await message.answer(
            text=f"{ai_summary_text}",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            text="⚠️ *Ошибка ИИ:* Не удалось сгенерировать сводку через ваш API-ключ. Проверьте его валидность в настройках.",
            parse_mode="Markdown"
        )

    await message.answer_document(
        document=document_file,
        caption="*Файл первоисточников*",
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
        "Также есть гайд на получение бесплатных API ключей на [гитхабе](https://github.com/PeacexF/NewsSummaryBot/tree/main/Documentation/Manuals) и в телеграм [статье](https://telegra.ph/Manual-polucheniya-API-klyucha-ot-Gemini-05-25)\n"
        "Поддержать создателя: [Cryptobot_USDT](https://t.me/send?start=IV3YZQmgcBKf) "
    )
    await message.answer(info_text, parse_mode="Markdown", link_preview_options=LinkPreviewOptions(is_disabled=True)
)

@router.message()
async def echo_unhandled(message: Message, state: FSMContext):
    await message.answer("не разпознал твое сообщение / комманду :(\nпопробуй перезапустить через `/start` и используй клавиатуру", parse_mode="Markdown")