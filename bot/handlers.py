from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


router = Router()

def get_main_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [
            KeyboardButton(text="📋 Мои каналы"),
            KeyboardButton(text="➕ Добавить канал")
        ],
        [
            KeyboardButton(text="📝 Собрать сводку сейчас")
        ],
        [
            KeyboardButton(text="⚙️ Настройки"), # API keys later and other settings
            KeyboardButton(text="ℹ️ Информация")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


@router.message(CommandStart())
async def cmd_start(message: Message):    
    welcome_text = (
        f"👋 *Привет {message.from_user.first_name}, Я - NewsSummary Bot*\n\n"
        "Я умею собирать посты из Telegram-каналов, "
        "очищать их от мусора, удалять дубликаты и рерайты, "
        "а затем формировать удобные отчеты.\n\n"
        "Используй меню ниже для управления своими подписками 👇"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())


@router.message(F.text == "📋 Мои каналы")
async def show_channels(message: Message):
    test_channels = ["durov", "rbc_news", "cybers"]
    
    if not test_channels:
        await message.answer("😢 У тебя пока нет добавленных каналов для мониторинга.\n"
                             "Добавь их чтобы мне было что собирать для тебя")
        return

    await message.answer("🗂 *Твой список каналов:*\n"
                         "Выбери канал, который хочешь удалить:",
                         parse_mode="Markdown")

    for channel in test_channels:
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Удалить канал", callback_data=f"delete_ch:{channel}")]
        ])
        await message.answer(f"📢 @{channel}", reply_markup=inline_kb)


@router.message(F.text == "➕ Добавить канал")
async def request_add_channel(message: Message):
    await message.answer(
        "📝 **Отправь мне юзернейм канала**\n\n"
        "Например, если канал доступен по ссылке `t.me/durov`, то отправь мне просто `durov` или `@durov`.",
        parse_mode="Markdown"
    )


@router.message(F.text == "📝 Собрать сводку сейчас")
async def manual_summary_trigger(message: Message):
    await message.answer(
        "⏳ *Запускаю сбор новостей и фильрацию...*\n\n"
        "Беру данные с RSSHub, проверяю базу данных и запускаю все процессы для работы с данными.\n"
        "Это займет менее 30 секунд.",
        parse_mode="Markdown"
        )
    
    await message.answer("🛠 *Здесь будет отправка готового .txt файла source*", parse_mode="Markdown")


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
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