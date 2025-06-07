import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackContext,
    JobQueue
)
import tempfile
import requests
from telegram import ReplyKeyboardRemove
import random
from datetime import datetime, timedelta
import csv
import io
import os
import requests
from io import BytesIO
from pathlib import Path
import time
import telegram
import traceback

# Настройка логгирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы для состояний
CHOOSING, TYPING_WISH, TYPING_SOUL, HOLIDAY_NAME, HOLIDAY_STYLE = range(5)
ADMIN_ID = int(os.getenv('1291710833', 1291710833))  # Замените на реальный ID

# Пути к изображениям
BASE_DIR = Path(__file__).parent
IMAGE_DIR = BASE_DIR / "images"

# Проверка существования папки с изображениями
if not IMAGE_DIR.exists():
    IMAGE_DIR.mkdir()
    logger.info(f"Создана папка для изображений: {IMAGE_DIR}")

# Сопоставление команд с файлами изображений
IMAGE_MAPPING = {
    "adventure_time": "images.jpeg",
    "something_new": "Soos.jpeg",
    "breakfast": "What.jpg",
    "snacks_drink": "cat.jpeg",
    "snacks_food": "Screenshot_1.png",
    "snacks_order": "Screenshot_2.png",
    "spells_menu": "Screenshot_3.png",
    "shock": "123.jpeg",
    "games": "3f2f47274f1001136417a49ae8bcc861.jpg",
    "custom_wish": "Screenshot_5.png",
    "flirt": "676474b166a2e356a4e29586d73d6d79.jpg",
    "secret": "MV5BMTQ3MTg3MzY4OV5BMl5BanBnXkFtZTgwNTI4MzM1NzE@._V1_FMjpg_UX1000_.jpg",
    "about": "35fdde57ed2e6dd72bd1e6adca6fc501.jpg",
    "settings": "Screenshot_4.png",
}

# Кэш для изображений
image_cache = {}

# Загрузка изображений в кэш (синхронная)
def load_images_to_cache():
    """Загружает все изображения в кэш при старте"""
    logger.info("Загрузка изображений в кэш...")
    for key, filename in IMAGE_MAPPING.items():
        image_path = IMAGE_DIR / filename
        if image_path.exists():
            try:
                with open(image_path, 'rb') as f:
                    # Создаем BytesIO и сохраняем в кэше
                    bio = BytesIO(f.read())
                    bio.seek(0)  # Сбрасываем позицию
                    image_cache[key] = bio
                    logger.info(f"✅ Изображение загружено в кэш: {filename}")
            except Exception as e:
                logger.error(f"Ошибка загрузки {filename}: {e}")
                image_cache[key] = None
        else:
            logger.warning(f"⚠️ Файл не найден: {image_path}")
            image_cache[key] = None

# Данные для ответов
RESPONSES = {
    'adventure': "Который час? Время приключений! Уже в эти выходные готовься к неожиданным поворотам. 🎒✨",
    'something_new': "Будь готова испытать что-то новое!",
    'breakfast': "Ожидай сюрприз-завтрак совсем скоро!",
    'snacks': {
        'drink': "Жди, я уже в пути",
        'food': "Жди, я уже в пути",
        'order': "Напиши, что бы ты хотела — будет исполнено!"
    },
    'spells': {
        1: "Сегодня ты можешь найти сюрприз в самом неожиданном месте… даже в чайнике. Не шути с магией!",
        2: "Кто-то уже шлёт тебе невидимые обнимашки. Почувствуй тепло — это магия работает.",
        3: "Возможно, сегодня ты получишь что-то сладкое… или просто поцелуй с привкусом карамели.",
        4: "Проверяй свои сообщения… Возможно, там уже летит волшебная весточка с любовью.",
        5: "Если вдруг грустно — не бойся. Вселенная уже шлёт тебе плюшевое настроение.",
        6: "В этот день ты заслуживаешь мягкости, уюта и немного волшебных моментов.",
        7: "Твоё главное заклинание активировано. Осталось только улыбнуться и ждать чуда.",
        8: "Тсс… это заклинание срабатывает, когда его никто не ждёт. Осторожно, может произойти волшебство."
    },
    'shock': lambda: f"{random.randint(1, 100)}",
    'games': "Раздел в разработке. Скоро здесь появится что-то интересное!",
    'flirt': "Готовься к весёлым и романтическим заданиям. Легкий флирт включён!",
    'secret': "Ты активировала квест. Жди первую инструкцию...",
    'soul': "Сегодня вечером поговорим по душам. Напиши тему, которая тебя волнует",
    'about': "Я — твой персональный романтический помощник, созданный для счастья 💘И, кстати... я — небольшой, но особенный подарок на нашу годовщину 🎁❤️",
    'settings': "Раздел пока в разработке. Обновления скоро, пока ждем"
}

# Главное меню
MAIN_KEYBOARD = [
    ["😱 Удиви меня", "➕ Время для вкусняшек"],
    ["📜 Секретные заклинания", "🎲 Шок-контент"],
    ["🎮 Мини-игры", "🪄 Добавить свое пожелание"],
    ["🎉 Праздничные режимы", "💃 Флирт-режим"],
    ["💌 Секретный уровень", "🧠 Для души"],
    ["⚙️ О нас / Помощь"]
]

# Меню "Удиви меня"
SURPRISE_KEYBOARD = [
    ["Adventure Time", "Что-то новенькое"],
    ["🔙 Назад"]
]

# Меню вкусняшек
SNACKS_KEYBOARD = [
    ["🍳 Хочу завтрак в постель"],
    ["🎁 Принести что-нибудь"],
    ["🔙 Назад"]
]

# Подменю для "Принести что-нибудь"
SNACKS_SUB_KEYBOARD = [
    ["🍹 Попить", "🍔 Покушать"],
    ["📝 Заказать что-нибудь"],
    ["🔙 Назад"]
]

# Меню секретных заклинаний
SPELLS_KEYBOARD = [
    ["1. Биббиди-Боббиди-Бу"],
    ["2. Амурус Инвизиум 💘"],
    ["3. Сладус Конфетус 🍬"],
    ["4. Лавиус Максимус 💌"],
    ["5. Флаффи Утешиум 🧸"],
    ["6. Кис-кис Сим-Салабим 😽"],
    ["7. Ультима Кудесия 🔮"],
    ["8. Заклинание #16 — Нельзя называть вслух 🕯️"],
    ["🔙 Назад"]
]

# Меню "О нас"
ABOUT_KEYBOARD = [
    ["🤖 Инфо о боте"],
    ["🛠️ Настройки"],
    ["⚙️ Админский режим"],
    ["🔙 Назад"]
]

# Админское меню
ADMIN_KEYBOARD = [
    ["👁️ Логи активности", "📬 Уведомления"],
    ["🛎️ Напоминания", "📥 Экспорт пожеланий"],
    ["🔙 Назад"]
]

# База данных (временная)
users_wishes = {}
activity_log = []
user_requests = []
notification_enabled = True
last_surprise_date = {}


async def send_image(update: Update, image_key: str, caption: str, reply_markup=None):
    try:
        if image_key not in image_cache:
            await update.message.reply_text(caption, reply_markup=reply_markup)
            return

        image_bio = image_cache.get(image_key)

        if image_bio:
            # Сбрасываем позицию потока
            image_bio.seek(0)

            # Отправляем изображение напрямую из BytesIO
            await update.message.reply_photo(
                photo=image_bio,
                caption=caption,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(caption, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Ошибка отправки изображения {image_key}: {e}")
        await update.message.reply_text(caption, reply_markup=reply_markup)


def log_activity(user_id: int, action: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{timestamp} - {user_id} - {action}"
    activity_log.append(entry)
    logger.info(entry)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Запустил бота")
    await show_main_menu(update, "Привет, солнышко! 💓\nВыбирай, чего тебе хочется:")


async def show_main_menu(update: Update, text: str):
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(
            MAIN_KEYBOARD,
            resize_keyboard=True,
            one_time_keyboard=False
        )
    )
    return ConversationHandler.END


# --- Обработчики основных команд ---
async def surprise_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Меню 'Удиви меня'")
    await update.message.reply_text(
        "Выбирай приключение:",
        reply_markup=ReplyKeyboardMarkup(SURPRISE_KEYBOARD, resize_keyboard=True)
    )


async def adventure_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Adventure Time")
    await send_image(update, "adventure_time", RESPONSES['adventure'])


async def something_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Что-то новенькое")
    await send_image(update, "something_new", RESPONSES['something_new'])


async def breakfast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Завтрак в постель")
    await send_image(update, "breakfast", RESPONSES['breakfast'])


async def snacks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Меню вкусняшек")
    await update.message.reply_text(
        "Выбирай:",
        reply_markup=ReplyKeyboardMarkup(SNACKS_KEYBOARD, resize_keyboard=True)
    )


async def bring_something_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Принести что-нибудь")
    await update.message.reply_text(
        "Что принести?",
        reply_markup=ReplyKeyboardMarkup(SNACKS_SUB_KEYBOARD, resize_keyboard=True)
    )


async def snacks_drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Попить")
    await send_image(update, "snacks_drink", RESPONSES['snacks']['drink'])
    await show_main_menu(update, "Что-нибудь еще?")


async def snacks_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Покушать")
    await send_image(update, "snacks_food", RESPONSES['snacks']['food'])
    await show_main_menu(update, "Что-нибудь еще?")


async def snacks_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Заказать что-нибудь")
    await send_image(update, "snacks_order", RESPONSES['snacks']['order'], reply_markup=ReplyKeyboardRemove())
    return TYPING_WISH


async def spells_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Меню заклинаний")
    await send_image(update, "spells_menu", "Прочитай вслух одно из заклинаний и нажми на него",
                     reply_markup=ReplyKeyboardMarkup(SPELLS_KEYBOARD, resize_keyboard=True))


async def handle_spell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    spell_text = update.message.text

    # Определяем номер заклинания
    spell_map = {
        "1. Биббиди-Боббиди-Бу": 1,
        "2. Амурус Инвизиум 💘": 2,
        "3. Сладус Конфетус 🍬": 3,
        "4. Лавиус Максимус 💌": 4,
        "5. Флаффи Утешиум 🧸": 5,
        "6. Кис-кис Сим-Салабим 😽": 6,
        "7. Ультима Кудесия 🔮": 7,
        "8. Заклинание #16 — Нельзя называть вслух 🕯️": 8
    }

    spell_num = spell_map.get(spell_text)
    if spell_num:
        log_activity(user.id, f"Заклинание #{spell_num}")
        await update.message.reply_text(RESPONSES['spells'][spell_num])
    else:
        await update.message.reply_text("Магия не сработала... Попробуй еще раз ✨")

    await spells_menu(update, context)  # Возврат в меню заклинаний


async def shock_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Шок-контент")
    number = RESPONSES['shock']()
    await send_image(update, "shock", f"Ваше число: {number}")


async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Мини-игры")
    await send_image(update, "games", RESPONSES['games'])


async def flirt_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Флирт-режим")
    await send_image(update, "flirt", RESPONSES['flirt'])


async def secret_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Секретный уровень")
    await send_image(update, "secret", RESPONSES['secret'])


async def about_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Инфо о боте")
    await send_image(update, "about", RESPONSES['about'])


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Настройки")
    await send_image(update, "settings", RESPONSES['settings'])


# --- Диалог для пользовательских пожеланий ---
async def custom_wish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Добавить пожелание")
    await send_image(update, "custom_wish", "Напиши, чего тебе хочется — и я это реализую!",
                     reply_markup=ReplyKeyboardRemove())
    return TYPING_WISH


async def save_wish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    wish_text = update.message.text
    timestamp = datetime.now()
    user_requests.append((user.id, user.first_name, wish_text, timestamp))
    log_activity(user.id, f"Пожелание: {wish_text}")

    # Отправляем уведомление админу, если включены уведомления
    if notification_enabled:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🎉 Новое пожелание от {user.first_name}!\n\n"
                     f"💬 Текст: {wish_text}\n"
                     f"🕒 Время: {timestamp.strftime('%Y-%m-%d %H:%M')}"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу: {e}")

    await update.message.reply_text("Записал! Скоро это появится в твоей жизни ✨")
    await show_main_menu(update, "Что-нибудь еще?")
    return ConversationHandler.END


# --- Диалог "По душам" ---
async def soul_talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "По душам")
    await update.message.reply_text(RESPONSES['soul'], reply_markup=ReplyKeyboardRemove())
    return TYPING_SOUL


async def save_soul_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    topic = update.message.text
    timestamp = datetime.now()
    user_requests.append((user.id, user.first_name, f"Тема по душам: {topic}", timestamp))
    log_activity(user.id, f"Тема для разговора: {topic}")
    await update.message.reply_text("Хорошо, обсудим это сегодня вечером 🌙")
    await show_main_menu(update, "Что-нибудь еще?")
    return ConversationHandler.END


# --- Праздничные режимы ---
async def holiday_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Праздничные режимы")
    await update.message.reply_text("Введите название праздника:", reply_markup=ReplyKeyboardRemove())
    return HOLIDAY_NAME


async def holiday_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['holiday_name'] = update.message.text
    keyboard = [["🎬 В стиле фильма", "🏠 Уютно"], ["😂 Шутливо"], ["🔙 Назад"]]
    await update.message.reply_text("Выберите стиль:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return HOLIDAY_STYLE


async def holiday_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    style = update.message.text
    name = context.user_data.get("holiday_name", "Без названия")
    log_activity(user.id, f"Праздник: {name}, Стиль: {style}")
    await show_main_menu(update, f"Отлично! Праздник «{name}» в стиле «{style}» записан!")
    return ConversationHandler.END


# --- Меню "О нас" ---
async def about_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_activity(user.id, "Меню 'О нас'")
    await update.message.reply_text(
        "Выберите раздел:",
        reply_markup=ReplyKeyboardMarkup(ABOUT_KEYBOARD, resize_keyboard=True)
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id == ADMIN_ID:
        log_activity(user.id, "Админ-панель")
        await update.message.reply_text(
            "Админ-панель:",
            reply_markup=ReplyKeyboardMarkup(ADMIN_KEYBOARD, resize_keyboard=True)
        )
        return CHOOSING
    await update.message.reply_text("⛔ Доступ запрещен")
    return ConversationHandler.END


# --- Админские функции ---
async def export_wishes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    log_activity(user.id, "Экспорт пожеланий")
    if not user_requests:
        await update.message.reply_text("Список пожеланий пуст")
        return

    # Создаем CSV
    csv_data = io.StringIO()
    writer = csv.writer(csv_data)

    # Заголовки
    writer.writerow(["Имя", "Пожелание", "Дата и время"])

    for username, wish, timestamp in user_requests:
        writer.writerow([
            username,
            wish,
            timestamp.strftime("%Y-%m-%d %H:%M")
        ])

    csv_data.seek(0)
    await update.message.reply_document(
        document=io.BytesIO(csv_data.getvalue().encode()),
        filename="romantic_wishes.csv",
        caption="Вот список всех пожеланий 🌟"
    )


async def show_activity_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    log_activity(user.id, "Просмотр логов")
    if not activity_log:
        await update.message.reply_text("Логи активности пусты")
        return

    # Отправляем последние 20 записей
    log_text = "📝 Последние действия:\n\n" + "\n".join(activity_log[-20:])
    await update.message.reply_text(log_text)


async def admin_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    global notification_enabled
    notification_enabled = not notification_enabled
    status = "включены" if notification_enabled else "выключены"
    log_activity(user.id, f"Уведомления: {status}")
    await update.message.reply_text(f"Уведомления о новых пожеланиях теперь {status} 🔔")


async def admin_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    log_activity(user.id, "Проверка напоминаний")

    # Проверяем, когда последний раз были сюрпризы
    reminder_text = "🎯 Статус сюрпризов:\n\n"
    now = datetime.now()

    if not last_surprise_date:
        reminder_text += "Вы еще не делали сюрпризов 😢"
    else:
        for user_id, last_date in last_surprise_date.items():
            days_passed = (now - last_date).days
            reminder_text += f"• Пользователь {user_id}: "

            if days_passed > 7:
                reminder_text += f"❌ Очень давно не было сюрприза ({days_passed} дней)"
            elif days_passed > 3:
                reminder_text += f"⚠️ Давно не было сюрприза ({days_passed} дней)"
            else:
                reminder_text += f"✅ Недавно был сюрприз ({days_passed} дней назад)"

            reminder_text += "\n"

    reminder_text += "\n💡 Совет: сделайте сюрприз сегодня!"
    await update.message.reply_text(reminder_text)


# --- Функция для кнопки "Назад" ---
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, "Главное меню 💓")
    return ConversationHandler.END


# --- Периодические напоминания ---
async def send_reminders(context: CallbackContext):
    job = context.job
    now = datetime.now()

    # Проверяем для каждого пользователя, когда был последний сюрприз
    for user_id, last_date in last_surprise_date.items():
        days_passed = (now - last_date).days

        # Отправляем напоминание, если прошло больше 3 дней
        if days_passed >= 3:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"💌 Напоминание!\n\n"
                         f"Вы давно не делали сюрприз пользователю {user_id}.\n"
                         f"Последний сюрприз был {days_passed} дней назад.\n\n"
                         f"Сделайте что-нибудь приятное сегодня! 💖"
                )
                # Обновляем дату, чтобы не спамить
                last_surprise_date[user_id] = now
            except Exception as e:
                logger.error(f"Ошибка отправки напоминания: {e}")


# --- Настройка обработчиков ---
def setup_handlers(application):
    # Главный обработчик диалогов
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            MessageHandler(filters.Regex(r"^⚙️ О нас / Помощь$"), about_menu),
            MessageHandler(filters.Regex(r"^⚙️ Админский режим$"), admin_panel),
            MessageHandler(filters.Regex(r"^📝 Заказать что-нибудь$"), snacks_order),
            MessageHandler(filters.Regex(r"^🪄 Добавить свое пожелание$"), custom_wish),
            MessageHandler(filters.Regex(r"^🎉 Праздничные режимы$"), holiday_menu),
            MessageHandler(filters.Regex(r"^🧠 Для души$"), soul_talk),
        ],
        states={
            TYPING_WISH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_wish),
                MessageHandler(filters.Regex(r"^🔙 Назад$"), back_to_main)
            ],
            TYPING_SOUL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_soul_topic),
                MessageHandler(filters.Regex(r"^🔙 Назад$"), back_to_main)
            ],
            HOLIDAY_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, holiday_name),
                MessageHandler(filters.Regex(r"^🔙 Назад$"), back_to_main)
            ],
            HOLIDAY_STYLE: [
                MessageHandler(filters.Regex(r"^(🎬 В стиле фильма|🏠 Уютно|😂 Шутливо)$"), holiday_style),
                MessageHandler(filters.Regex(r"^🔙 Назад$"), back_to_main)
            ],
            CHOOSING: [
                MessageHandler(filters.Regex(r"^📥 Экспорт пожеланий$"), export_wishes),
                MessageHandler(filters.Regex(r"^👁️ Логи активности$"), show_activity_log),
                MessageHandler(filters.Regex(r"^📬 Уведомления$"), admin_notifications),
                MessageHandler(filters.Regex(r"^🛎️ Напоминания$"), admin_reminders),
                MessageHandler(filters.Regex(r"^🔙 Назад$"), back_to_main)
            ]
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )

    # Регистрация обработчиков команд
    application.add_handler(conv_handler)

    # Обработчики кнопок главного меню
    application.add_handler(MessageHandler(filters.Regex(r"^😱 Удиви меня$"), surprise_menu))
    application.add_handler(MessageHandler(filters.Regex(r"^➕ Время для вкусняшек$"), snacks_menu))
    application.add_handler(MessageHandler(filters.Regex(r"^📜 Секретные заклинания$"), spells_menu))
    application.add_handler(MessageHandler(filters.Regex(r"^🎲 Шок-контент$"), shock_content))
    application.add_handler(MessageHandler(filters.Regex(r"^🎮 Мини-игры$"), games))
    application.add_handler(MessageHandler(filters.Regex(r"^💃 Флирт-режим$"), flirt_mode))
    application.add_handler(MessageHandler(filters.Regex(r"^💌 Секретный уровень$"), secret_level))

    # Обработчики подменю
    application.add_handler(MessageHandler(filters.Regex(r"^Adventure Time$"), adventure_time))
    application.add_handler(MessageHandler(filters.Regex(r"^Что-то новенькое$"), something_new))
    application.add_handler(MessageHandler(filters.Regex(r"^🍳 Хочу завтрак в постель$"), breakfast))
    application.add_handler(MessageHandler(filters.Regex(r"^🎁 Принести что-нибудь$"), bring_something_menu))
    application.add_handler(MessageHandler(filters.Regex(r"^🍹 Попить$"), snacks_drink))
    application.add_handler(MessageHandler(filters.Regex(r"^🍔 Покушать$"), snacks_food))

    # Обработчики заклинаний
    spell_patterns = [
        r"^1\. Биббиди-Боббиди-Бу$",
        r"^2\. Амурус Инвизиум 💘$",
        r"^3\. Сладус Конфетус 🍬$",
        r"^4\. Лавиус Максимус 💌$",
        r"^5\. Флаффи Утешиум 🧸$",
        r"^6\. Кис-кис Сим-Салабим 😽$",
        r"^7\. Ультима Кудесия 🔮$",
        r"^8\. Заклинание #16 — Нельзя называть вслух 🕯️$"
    ]
    for pattern in spell_patterns:
        application.add_handler(MessageHandler(filters.Regex(pattern), handle_spell))

    # Обработчики меню "О нас"
    application.add_handler(MessageHandler(filters.Regex(r"^🤖 Инфо о боте$"), about_bot))
    application.add_handler(MessageHandler(filters.Regex(r"^🛠️ Настройки$"), settings))

    # Навигация
    application.add_handler(MessageHandler(filters.Regex(r"^🔙 Назад$"), back_to_main))


def main():
    # Загружаем изображения в кэш (синхронно)
    load_images_to_cache()

    # Проверка существования изображений
    logger.info("Проверка изображений...")
    for key, filename in IMAGE_MAPPING.items():
        path = IMAGE_DIR / filename
        if not path.exists():
            logger.warning(f"⚠️ Изображение не найдено: {path}")
        else:
            logger.info(f"✅ Изображение найдено: {path}")

    # Запуск бота с обработкой конфликтов
    while True:
        try:
            application = ApplicationBuilder().token("8054818207:AAFq18jcwhO0h1i28mH-H2B_btNIMRyJLqQ").build()

            # Настраиваем периодические напоминания
            if application.job_queue:
                application.job_queue.run_repeating(
                    send_reminders,
                    interval=timedelta(days=1),
                    first=10
                )
            else:
                logger.warning("JobQueue не доступен. Напоминания отключены.")

            setup_handlers(application)

            logger.info("Бот запущен...")
            application.run_polling()

        except telegram.error.Conflict as e:
            logger.error(f"Конфликт: {e}")
            logger.info("Попытка перезапуска через 5 секунд...")
            time.sleep(5)

        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            logger.error(traceback.format_exc())  # Логируем полный стек вызовов
            logger.info("Перезапуск через 10 секунд...")
            time.sleep(10)


if __name__ == "__main__":
    main()