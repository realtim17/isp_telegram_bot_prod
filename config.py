"""
Конфигурация бота и константы
"""
import os
import logging
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Константы состояний для ConversationHandler
# Создание подключения
SELECT_CONNECTION_TYPE = 0
UPLOAD_PHOTOS = 1
ENTER_ADDRESS = 2
SELECT_ROUTER = 3
ENTER_ROUTER_QUANTITY_CONNECTION = 4
ROUTER_ACCESS = 5
ENTER_PORT = 6
ENTER_FIBER = 7
ENTER_TWISTED = 8
CONTRACT_SIGNED = 9
TELEGRAM_BOT_CONFIRM = 10
SELECT_EMPLOYEES = 11
SELECT_MATERIAL_PAYER = 12
SELECT_ROUTER_PAYER = 13
CONFIRM = 14

# Управление сотрудниками
MANAGE_ACTION = 15
ADD_EMPLOYEE_NAME = 16
CONFIRM_ADD_EMPLOYEE = 17
DELETE_EMPLOYEE_SELECT = 18
CONFIRM_DELETE_EMPLOYEE = 19
SELECT_EMPLOYEE_FOR_MATERIAL = 20
SELECT_MATERIAL_ACTION = 21
ENTER_FIBER_AMOUNT = 22
ENTER_TWISTED_AMOUNT = 23
CONFIRM_MATERIAL_OPERATION = 24
SELECT_EMPLOYEE_FOR_ROUTER = 25
SELECT_ROUTER_ACTION = 26
ENTER_ROUTER_NAME = 27
ENTER_ROUTER_QUANTITY = 28
CONFIRM_ROUTER_OPERATION = 29

# Отчеты
SELECT_REPORT_EMPLOYEE = 30
SELECT_REPORT_PERIOD = 31
ENTER_REPORT_CUSTOM_START = 32
ENTER_REPORT_CUSTOM_END = 33
SELECT_EMPLOYEE_FOR_SNR = 34
SELECT_SNR_ACTION = 35
ENTER_SNR_NAME = 36
ENTER_SNR_QUANTITY = 37
CONFIRM_SNR_OPERATION = 38
SELECT_SNR_BOX = 39
SELECT_SNR_PAYER = 40
MANAGE_ACCESS = 41
ENTER_ACCESS_ID = 42
MANAGE_ADMINS = 43
ENTER_ADMIN_ID = 44
SELECT_EMPLOYEE_FOR_ONU = 45
SELECT_ONU_ACTION = 46
ENTER_ONU_NAME = 47
ENTER_ONU_QUANTITY = 48
CONFIRM_ONU_OPERATION = 49
SELECT_EMPLOYEE_FOR_MEDIA = 50
SELECT_MEDIA_ACTION = 51
ENTER_MEDIA_NAME = 52
ENTER_MEDIA_QUANTITY = 53
CONFIRM_MEDIA_OPERATION = 54

# Типы подключений
CONNECTION_TYPES = {
    'mkd': 'МКД',
    'chs': 'ЧС',
    'legal': 'Юр / Гос'
}


# Токен бота
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Загрузка ID администраторов (суперадминов)
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_USER_IDS', '').split(',') if id.strip()]

# Список пользователей с доступом к боту
ALLOWED_USER_IDS = {
    int(user_id.strip()) for user_id in os.getenv('ALLOWED_USER_IDS', '').split(',') if user_id.strip()
}

ACCESS_DENIED_MESSAGE = (
    os.getenv(
        'ACCESS_DENIED_MESSAGE',
        '⛔ Доступ к боту ограничен. Обратитесь к администратору.'
    ).strip()
    or '⛔ Доступ к боту ограничен. Обратитесь к администратору.'
)

# ID канала для отправки отчетов (опционально)
REPORTS_CHANNEL_ID = os.getenv('REPORTS_CHANNEL_ID', '').strip()
if REPORTS_CHANNEL_ID:
    try:
        REPORTS_CHANNEL_ID = int(REPORTS_CHANNEL_ID)
        logger.info(f"Канал для отчетов настроен: {REPORTS_CHANNEL_ID}")
    except ValueError:
        REPORTS_CHANNEL_ID = None
        logger.warning("REPORTS_CHANNEL_ID имеет неверный формат")
else:
    REPORTS_CHANNEL_ID = None


def is_admin(user_id: int) -> bool:
    """Legacy: проверка только по ADMIN_USER_IDS из .env"""
    return user_id in ADMIN_IDS
