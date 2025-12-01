"""
ConversationHandler для создания подключений
Интегрирует все модули обработки подключений
"""
from telegram.ext import ConversationHandler, MessageHandler, CallbackQueryHandler, filters

from config import (
    SELECT_CONNECTION_TYPE, UPLOAD_PHOTOS, ENTER_ADDRESS, SELECT_ROUTER,
    ENTER_ROUTER_QUANTITY_CONNECTION, ROUTER_ACCESS, ENTER_PORT, ENTER_FIBER,
    ENTER_TWISTED, CONTRACT_SIGNED, TELEGRAM_BOT_CONFIRM, SELECT_EMPLOYEES, 
    SELECT_MATERIAL_PAYER, SELECT_ROUTER_PAYER, SELECT_SNR_BOX, SELECT_SNR_PAYER, CONFIRM,
    SELECT_ONU_ACTION, ENTER_ONU_QUANTITY, SELECT_MEDIA_ACTION, ENTER_MEDIA_QUANTITY,
    ENTER_COMMENT, ENTER_SNR_QUANTITY_CONNECTION
)

# Импорт обработчиков шагов
from handlers.connection.steps import (
    new_connection_start,
    select_connection_type,
    upload_photos,
    ask_address,
    enter_address,
    select_router,
    enter_router_quantity_connection,
    router_access_handler,
    enter_port,
    enter_fiber,
    enter_twisted,
    contract_signed,
    telegram_bot_confirm,
    select_snr_box,
    enter_snr_quantity_connection,
    select_onu_connection,
    enter_onu_quantity_connection,
    select_media_connection,
    enter_media_quantity_connection,
    enter_comment,
)

# Импорт обработчиков выбора исполнителей
from handlers.connection.employees import (
    select_employee_toggle
)

# Импорт обработчиков валидации
from handlers.connection.validation import (
    select_material_payer,
    select_router_payer,
    select_snr_payer
)

# Импорт обработчиков подтверждения
from handlers.connection.confirmation import (
    confirm_connection
)

# Импорт обработчиков отмены
from handlers.connection.cancellation import (
    cancel_connection,
    cancel_by_menu,
    cancel_by_command
)

def build_connection_conversation(db) -> ConversationHandler:
    """Построить ConversationHandler с внедренным экземпляром БД"""
    
    async def enter_address_wrapper(update, context):
        return await enter_address(update, context, db)
    
    async def telegram_bot_confirm_wrapper(update, context):
        return await telegram_bot_confirm(update, context, db)
    
    async def select_snr_box_wrapper(update, context):
        return await select_snr_box(update, context, db)

    async def enter_snr_quantity_wrapper(update, context):
        return await enter_snr_quantity_connection(update, context, db)

    async def enter_twisted_wrapper(update, context):
        return await enter_twisted(update, context, db)
    
    async def select_onu_wrapper(update, context):
        return await select_onu_connection(update, context, db)
    
    async def enter_onu_quantity_wrapper(update, context):
        return await enter_onu_quantity_connection(update, context, db)
    
    async def select_media_wrapper(update, context):
        return await select_media_connection(update, context, db)
    
    async def enter_media_quantity_wrapper(update, context):
        return await enter_media_quantity_connection(update, context, db)
    
    async def enter_comment_wrapper(update, context):
        return await enter_comment(update, context, db)
    
    async def select_employee_toggle_wrapper(update, context):
        return await select_employee_toggle(update, context, db)
    
    async def select_material_payer_wrapper(update, context):
        return await select_material_payer(update, context, db)
    
    async def select_router_payer_wrapper(update, context):
        return await select_router_payer(update, context, db)
    
    async def select_snr_payer_wrapper(update, context):
        return await select_snr_payer(update, context, db)
    
    async def confirm_connection_wrapper(update, context):
        return await confirm_connection(update, context, db)
    
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^📝 Новое подключение$'), new_connection_start),
            CallbackQueryHandler(new_connection_start, pattern='^start_new_connection$')
        ],
        states={
            SELECT_CONNECTION_TYPE: [
                CallbackQueryHandler(select_connection_type, pattern='^conn_type_'),
                CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
            ],
            UPLOAD_PHOTOS: [
                MessageHandler(filters.PHOTO, upload_photos),
                CallbackQueryHandler(ask_address, pattern='^continue_from_photos$'),
                CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
            ],
            ENTER_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_address_wrapper)
            ],
            SELECT_ROUTER: [
                CallbackQueryHandler(select_router, pattern='^(select_router_|router_skip)'),
                CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
            ],
            ENTER_ROUTER_QUANTITY_CONNECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_router_quantity_connection)
            ],
            ROUTER_ACCESS: [
                CallbackQueryHandler(router_access_handler, pattern='^(router_access_confirmed|router_access_skipped|cancel_connection)$')
            ],
            ENTER_PORT: [
                CallbackQueryHandler(enter_port, pattern='^port_skip$'),
                CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_port)
            ],
            ENTER_FIBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_fiber)
            ],
            ENTER_TWISTED: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_twisted_wrapper)
            ],
            CONTRACT_SIGNED: [
                CallbackQueryHandler(contract_signed, pattern='^(contract_confirmed|contract_skipped|cancel_connection)$')
            ],
            TELEGRAM_BOT_CONFIRM: [
                CallbackQueryHandler(telegram_bot_confirm_wrapper, pattern='^(telegram_bot_confirmed|telegram_bot_skipped|cancel_connection)$')
            ],
            SELECT_SNR_BOX: [
                CallbackQueryHandler(select_snr_box_wrapper, pattern='^(snr_box_.*|snr_skip|cancel_connection)$')
            ],
            ENTER_SNR_QUANTITY_CONNECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_snr_quantity_wrapper),
                CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
            ],
            SELECT_ONU_ACTION: [
                CallbackQueryHandler(select_onu_wrapper, pattern='^(conn_onu_.*|conn_onu_skip)$'),
                CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
            ],
            ENTER_ONU_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_onu_quantity_wrapper),
                CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
            ],
            SELECT_MEDIA_ACTION: [
                CallbackQueryHandler(select_media_wrapper, pattern='^(conn_media_.*|conn_media_skip)$'),
                CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
            ],
            ENTER_MEDIA_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_media_quantity_wrapper),
                CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
            ],
            ENTER_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_comment_wrapper)
            ],
            SELECT_EMPLOYEES: [
                CallbackQueryHandler(select_employee_toggle_wrapper, pattern='^(emp_.*|employees_done)$'),
                CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
            ],
            SELECT_MATERIAL_PAYER: [
                CallbackQueryHandler(select_material_payer_wrapper, pattern='^payer_'),
                CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
            ],
            SELECT_ROUTER_PAYER: [
                CallbackQueryHandler(select_router_payer_wrapper, pattern='^router_payer_'),
                CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
            ],
            SELECT_SNR_PAYER: [
                CallbackQueryHandler(select_snr_payer_wrapper, pattern='^snr_payer_'),
                CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
            ],
            CONFIRM: [
                CallbackQueryHandler(confirm_connection_wrapper, pattern='^confirm_')
            ]
        },
        fallbacks=[
            MessageHandler(
                filters.Regex('^(📝 Новое подключение|📊 Сводный отчет|👥 Управление сотрудниками|ℹ️ Помощь)$'),
                cancel_by_menu
            ),
            MessageHandler(filters.COMMAND, cancel_by_command)
        ],
        name='connection_conversation',
        persistent=False
    )
