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
            KeyboardButton(text="⚙️ Настройки") # API keys later and other settings
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


@router.message(CommandStart())
async def cmd_start(message: Message):
   # await message.answer_sticker("CAACAgIAAxkBAAELEKtl8_8Wgp3N_vGo8-rX78Z5N4b9QAACLAADb7b7E7vYy0V86_g0NAQ")
    
    welcome_text = (
        "👋 **Привет! Я твой персональный NewsSummary Bot.**\n\n"
        "Я умею собирать посты из твоих любимых Telegram-каналов, "
        "очищать их от мусора, удалять дубликаты и рерайты, "
        "а затем формировать удобные отчеты.\n\n"
        "Используй меню ниже для управления своими подписками 👇"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())


@router.message(F.text == "📋 Мои каналы")
async def show_channels(message: Message):
    test_channels = ["durov", "rbc_news", "cybers"]
    
    if not test_channels:
        await message.answer("😢 У тебя пока нет добавленных каналов для мониторинга.\nДобавь их чтобы мне было что собирать для тебя")
        return

    await message.answer("🗂 **Твой список каналов:**\nВыбери канал, который хочешь удалить:", parse_mode="Markdown")

    for channel in test_channels:
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Удалить канал", callback_data=f"delete_ch:{channel}")]
        ])
        await message.answer(f"📢 @{channel}", reply_markup=inline_kb)


@router.message(F.text == "➕ Добавить канал")
async def request_add_channel(message: Message):
    await message.answer(
        "📝 **Отправь мне юзернейм канала**\n\n"
        "Например, если канал доступен по ссылке `t.me/durov`, то отправь мне просто `durov` или `@durov`."
    )


@router.message(F.text == "📝 Собрать сводку сейчас")
async def manual_summary_trigger(message: Message):
    await message.answer("⏳ **Запускаю конвейер сборщика новостей...**\n\n"
                         "Я опрашиваю RSSHub, проверяю базу данных и запускаю все процессы для работы с данными.\n"
                         "Это займет менее 30 секунд.")
    
    await message.answer("🛠 *Здесь будет отправка готового .txt файла source*", parse_mode="Markdown")


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
    settings_text = (
        "⚙️ **Настройки системы**\n\n"
        "🤖 **Текущая LLM:** Gemini 1.5 Flash (Default)\n"
        "🔑 **API Ключ:** Используется глобальный ключ сервера.\n\n"
        "ℹ️ _В следующих обновлениях сюда будет добавлен раздел для привязки твоего личного API-ключа, "
        "чтобы сделать использование бота полностью бесплатным и независимым от лимитов сервера!_"
    )
    await message.answer(settings_text, parse_mode="Markdown")