"""
Telegram-бот для интернет-провайдера
Автоматизация отчетности по подключению новых абонентов
"""
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    TypeHandler,
    ApplicationHandlerStop,
    filters
)

# Импорт конфигурации
from config import (
    TELEGRAM_BOT_TOKEN,
    SELECT_REPORT_EMPLOYEE, SELECT_REPORT_PERIOD,
    ENTER_REPORT_CUSTOM_START, ENTER_REPORT_CUSTOM_END,
    logger,
    ALLOWED_USER_IDS,
    ADMIN_IDS,
)

# Импорт базы данных
from database import Database

# Импорт обработчиков команд
from handlers.commands import (
    start_command,
    help_command,
    cancel_command,
    cancel_and_start_new
)

# Импорт клавиатуры
from utils.keyboards import get_main_keyboard, set_main_keyboard_admin_mode
from utils.helpers import ensure_user_authorized
from utils.access import AccessManager
from utils.admins import AdminManager

# Импорт ConversationHandler для подключений
from handlers.connection import build_connection_conversation

# Импорт EmployeeFlow
from handlers.employees import EmployeeFlow

# Импорт обработчиков отчетов
from handlers.reports import (
    report_start,
    report_select_period,
    report_generate,
    report_enter_custom_start,
    report_enter_custom_end
)

# Инициализация БД
db = Database()
connection_conv = build_connection_conversation(db)
access_manager = AccessManager(db, ALLOWED_USER_IDS)
admin_manager = AdminManager(db, ADMIN_IDS)
employee_flow = EmployeeFlow(db, access_manager, admin_manager)


def main():
    """Запуск бота"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не найден в .env файле!")
        return
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Фильтр для ввода данных (исключает кнопки главного меню)
    text_input_filter = (
        filters.TEXT & 
        ~filters.COMMAND & 
        ~filters.Regex('^(📝 Новое подключение|📊 Сводный отчет|👥 Управление сотрудниками|ℹ️ Помощь)$')
    )
    
    # Фильтр для кнопок главного меню
    menu_buttons_filter = filters.Regex('^(📝 Новое подключение|📊 Сводный отчет|👥 Управление сотрудниками|📦 Материалы и оборудование|ℹ️ Помощь)$')
    
    # Обертки для передачи db в обработчики отчетов и сотрудников
    async def report_start_wrapper(update, context):
        return await report_start(update, context, db)
    
    async def report_select_period_wrapper(update, context):
        return await report_select_period(update, context, db)
    
    async def report_generate_wrapper(update, context):
        return await report_generate(update, context, db)
    
    async def report_custom_end_wrapper(update, context):
        return await report_enter_custom_end(update, context, db)
    
    # Обработчик отчетов
    report_conv = ConversationHandler(
        entry_points=[
            CommandHandler('report', report_start_wrapper),
            MessageHandler(filters.Regex('^📊 Сводный отчет$'), report_start_wrapper)
        ],
        states={
            SELECT_REPORT_EMPLOYEE: [CallbackQueryHandler(report_select_period_wrapper, pattern='^(rep_emp_|rep_all|report_cancel)')],
            SELECT_REPORT_PERIOD: [CallbackQueryHandler(report_generate_wrapper, pattern='^(period_|period_cancel)')],
            ENTER_REPORT_CUSTOM_START: [MessageHandler(text_input_filter, report_enter_custom_start)],
            ENTER_REPORT_CUSTOM_END: [MessageHandler(text_input_filter, report_custom_end_wrapper)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_command),
            MessageHandler(menu_buttons_filter, cancel_and_start_new)
        ]
    )
    
    employee_conv = employee_flow.build_conversation(
        text_input_filter,
        fallbacks=[
            CommandHandler('cancel', cancel_command),
            MessageHandler(menu_buttons_filter, cancel_and_start_new)
        ]
    )
    
    # Глобальный guard доступа
    async def authorization_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        # Фиксируем флаг администратора для дальнейших вызовов get_main_keyboard
        is_admin = admin_manager.is_admin(user.id) if user else False
        set_main_keyboard_admin_mode(is_admin)

        if await ensure_user_authorized(update, access_manager):
            return
        raise ApplicationHandlerStop
    
    application.add_handler(TypeHandler(Update, authorization_guard), group=-1)
    
    # Добавляем обработчики
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(connection_conv)
    application.add_handler(report_conv)
    application.add_handler(employee_conv)
    application.add_handler(MessageHandler(filters.Regex('^📋 Список сотрудников МОЛ$'), employee_flow.show_employees_list))
    application.add_handler(MessageHandler(filters.Regex('^ℹ️ Помощь$'), help_command))
    
    # Fallback для неизвестных команд
    async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Неизвестная команда. Используйте кнопки меню или /help для справки.",
            reply_markup=get_main_keyboard()
        )
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~menu_buttons_filter,
        unknown_command
    ))
    
    # Запускаем бота
    logger.info("🚀 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
