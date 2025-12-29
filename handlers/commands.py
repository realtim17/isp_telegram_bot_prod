"""
Основные команды бота
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from utils.keyboards import get_main_keyboard


def clear_all_conversations(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Полностью очистить все данные бесед и состояний во всем боте.
    Используем для /stop, чтобы гарантированно сбросить любые активные процессы.
    """
    try:
        # Чистим только данные текущего чата/пользователя, не затрагивая остальных
        context.user_data.clear()
        context.chat_data.clear()
        if hasattr(context, "application") and context.application:
            if hasattr(context.application, "conversation_data"):
                context.application.conversation_data.pop(context.chat.id, None)
    except Exception:
        # Предпочитаем не падать на вспомогательной очистке
        context.user_data.clear()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start"""
    user = update.effective_user
    welcome_text = f"""
👋 Добро пожаловать, {user.first_name}!

Это бот для автоматизации отчетности по подключению новых абонентов.

🔹 Основные функции:
• Создание отчетов о подключении с фотографиями по категориям
• Выбор исполнителей из списка
• Автоматический расчет метража на каждого исполнителя
• Формирование сводных отчетов в Excel

📋 Доступные команды:
/new - Создать новый отчет
/report - Получить сводный отчет
/manage_employees - Управление сотрудниками (только для админов)
/cancel - Отменить текущую операцию
/help - Справка

Выберите действие на клавиатуре ниже:
"""
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /help"""
    help_text = """
📚 <b>Справка по использованию бота</b>

<b>Создание отчета о подключении:</b>
1. Нажмите "📝 Новое подключение" или /new
2. Выберите тип подключения
3. Последовательно загрузите фотографии по категориям:
   • 📍 Маршрут линии (обязательно)
   • 🔌 ОРК/Коммутатор (обязательно)
   • 🏠 Место входа в помещение (обязательно)
   • 📦 Внутренняя укладка (опционально)
   • 📡 WiFi роутер (обязательно)
   • ⚡ Замер скорости (опционально)
   • 🔑 Доступ на роутер (опционально)
4. Заполните данные о подключении
5. Выберите исполнителей
6. Подтвердите создание

<b>Получение сводного отчета:</b>
1. Нажмите "📊 Сводный отчет" или /report
2. Выберите сотрудника
3. Выберите период
4. Получите Excel-файл

<b>Управление сотрудниками:</b>
(только для администраторов)
1. Нажмите "👥 Управление сотрудниками"
2. Добавьте или удалите сотрудников

<b>Логика расчета метража:</b>
Метраж делится поровну между всеми исполнителями.
Например: 100м ВОЛС на 2 исполнителей = по 50м каждому

❓ Если возникли вопросы - обратитесь к администратору @tim_real
"""
    await update.message.reply_text(help_text, parse_mode='HTML')


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущей операции"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Операция отменена.",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END


async def cancel_and_start_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущего процесса - новое действие запустится автоматически через entry_points"""
    context.user_data.clear()
    await update.message.reply_text(
        "⚠️ Предыдущее действие отменено.",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Принудительная остановка любых активных действий"""
    clear_all_conversations(context)
    target = update.effective_message
    if target:
        await target.reply_text(
            "⏹️ Все активные действия остановлены.",
            reply_markup=get_main_keyboard()
        )
    return ConversationHandler.END
