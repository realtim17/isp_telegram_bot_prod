# Руководство по модулям ISP Telegram Bot

## Оглавление
1. [Основные модули](#основные-модули)
2. [Handlers (Обработчики)](#handlers-обработчики)
3. [Database (База данных)](#database-база-данных)
4. [Utils (Утилиты)](#utils-утилиты)
5. [Взаимосвязи модулей](#взаимосвязи-модулей)

---

## Основные модули

### bot.py
**Назначение:** Точка входа приложения

**Ответственность:**
- Инициализация Telegram Application
- Регистрация обработчиков (handlers)
- Создание ConversationHandler для диалогов
- Запуск бота

**Ключевые компоненты:**
```python
def main():
    application = Application.builder().token(TOKEN).build()
    
    # Регистрация обработчиков
    application.add_handler(connection_conv)
    application.add_handler(report_conv)
    application.add_handler(employee_conv)
    
    # Запуск
    application.run_polling()
```

**Зависимости:**
- `handlers.connection` - обработка подключений
- `handlers.reports` - генерация отчетов
- `handlers.employees` - управление сотрудниками
- `handlers.commands` - базовые команды
- `config` - конфигурация

---

### config.py
**Назначение:** Централизованная конфигурация

**Содержит:**
1. **Константы состояний** для ConversationHandler
2. **Типы подключений** (МКД, ЧС, Юр/Гос)
3. **Telegram токен** из .env
4. **ID администраторов**
5. **ID канала** для отчетов
6. **Настройки логирования**

**Пример использования:**
```python
from config import SELECT_CONNECTION_TYPE, CONNECTION_TYPES, is_admin

# Проверка админ-прав
if is_admin(user_id):
    # ...
    
# Получение названия типа
type_name = CONNECTION_TYPES.get('mkd')  # 'МКД'
```

**Важно:** Не хранит чувствительные данные - только ссылки на .env

---

## Handlers (Обработчики)

### handlers/commands.py
**Назначение:** Базовые команды бота

**Функции:**
- `start_command()` - /start, приветствие
- `help_command()` - /help, справка
- `cancel_command()` - /cancel, отмена операции
- `cancel_and_start_new()` - переход между разделами

**Особенности:**
- Показывает главную клавиатуру
- Очищает контекст при отмене
- Логирует действия пользователя

---

### handlers/connection/

**Назначение:** Модуль создания подключений

#### Структура:
```
handlers/connection/
├── __init__.py           # Экспорт build_connection_conversation
├── conversation.py       # ConversationHandler
├── steps.py              # Обработчики шагов
├── validation.py         # Проверка материалов/роутеров
├── confirmation.py       # Подтверждение данных
└── constants.py          # Константы и тексты
```

#### conversation.py
**Ответственность:** Создание ConversationHandler

**Структура диалога:**
1. SELECT_CONNECTION_TYPE - выбор типа (МКД/ЧС/Юр)
2. UPLOAD_PHOTOS - загрузка фото
3. ENTER_ADDRESS - ввод адреса
4. SELECT_ROUTER - выбор роутера
5. ENTER_ROUTER_QUANTITY - количество роутеров
6. ROUTER_ACCESS - доступ на роутер
7. ENTER_PORT - номер порта
8. ENTER_FIBER - метраж ВОЛС
9. ENTER_TWISTED - метраж витой пары
10. CONTRACT_SIGNED - подписание договора
11. SELECT_EMPLOYEES - выбор исполнителей
12. SELECT_MATERIAL_PAYER - кто платит за материалы
13. SELECT_ROUTER_PAYER - кто платит за роутер
14. CONFIRM - подтверждение

**Пример:**
```python
connection_conv = ConversationHandler(
    entry_points=[
        MessageHandler(
            filters.Regex('^📝 Новое подключение$'), 
            new_connection_start
        )
    ],
    states={
        SELECT_CONNECTION_TYPE: [
            CallbackQueryHandler(select_connection_type, pattern='^conn_type_')
        ],
        # ... другие состояния
    },
    fallbacks=[CommandHandler('cancel', cancel_command)]
)
```

#### steps.py
**Ответственность:** Обработчики шагов создания подключения

**Функции:**
- `new_connection_start()` - начало, выбор типа
- `select_connection_type()` - сохранение типа
- `upload_photos()` - загрузка фотографий
- `ask_address()` - запрос адреса
- `enter_address()` - сохранение адреса
- `select_router()` - выбор роутера
- `enter_router_quantity()` - количество роутеров
- `router_access_handler()` - доступ на роутер
- `enter_port()` - ввод порта
- `enter_fiber()` - метраж ВОЛС
- `enter_twisted()` - метраж витой пары
- `contract_signed()` - подписание договора

**Паттерн обработки:**
```python
async def enter_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text.strip()
    
    # Валидация
    if Validator.is_cancel_command(address):
        return await cancel_connection(update, context)
    
    # Сохранение
    context.user_data['connection_data']['address'] = address
    
    # Переход к следующему шагу
    await update.message.reply_text(...)
    return NEXT_STATE
```

#### validation.py
**Ответственность:** Проверка наличия материалов и роутеров

**Функции:**
- `check_materials_and_proceed()` - проверка материалов
- `select_material_payer()` - выбор плательщика материалов
- `check_routers_and_proceed()` - проверка роутеров
- `select_router_payer()` - выбор плательщика роутера

**Логика:**
1. Получить требуемые материалы/роутеры
2. Проверить балансы всех исполнителей
3. Если ни у кого нет → блокировка
4. Если у одного → автоматический выбор
5. Если у нескольких → выбор пользователя

**Пример:**
```python
async def check_materials_and_proceed(update, context, db):
    data = context.user_data['connection_data']
    employees = context.user_data['selected_employees']
    
    # Проверка балансов
    employees_with_enough = []
    for emp_id in employees:
        if has_enough_materials(emp_id, data):
            employees_with_enough.append(emp_id)
    
    # Логика выбора
    if len(employees_with_enough) == 0:
        return await show_error(...)
    elif len(employees_with_enough) == 1:
        return await auto_select(...)
    else:
        return await show_selection(...)
```

#### confirmation.py
**Ответственность:** Подтверждение и сохранение

**Функции:**
- `show_confirmation()` - показ данных для подтверждения
- `confirm_connection()` - сохранение в БД и отправка отчета

**Использует:**
- `MessageBuilder` для форматирования
- `Database` для сохранения
- `send_connection_report()` для отправки

#### constants.py
**Содержит:**
- MAX_PHOTOS = 10
- REQUIRED_PHOTO_CATEGORIES
- Текстовые шаблоны сообщений

---

### handlers/employees/
**Назначение:** Управление сотрудниками, доступом и ТМЦ

**Функционал:**
1. **Управление сотрудниками**
   - Координатор: `EmployeeFlow` (`flow.py`)
   - Добавление/удаление сотрудников: `mutations.py`
   - Список сотрудников: `listing.py`

2. **Управление материалами и оборудованием**
   - Материалы: `materials.py`
   - Роутеры: `routers.py`
   - SNR/ONU/Media/SFP: `snr_boxes.py`, `onu.py`, `media_converters.py`, `sfp_modules.py`

3. **Администрирование и доступ**
   - Управление доступом: `access_control.py`
   - Управление администраторами: `admin_control.py`
   - Пошаговая выдача ТМЦ: `tmc_flow.py`

**Зависимости:**
- `Database` для CRUD операций
- `utils.validators` для валидации
- `utils.keyboards` для клавиатур

---

### handlers/reports.py
**Назначение:** Генерация отчетов

**Функции:**
- `report_start()` - выбор сотрудника
- `report_select_period()` - выбор периода
- `report_generate()` - генерация Excel

**Периоды:**
- Последние 7 дней
- Последние 30 дней
- Последние 90 дней
- Все время

**Использует:**
- `ReportGenerator` для Excel
- `Database` для получения данных

---

## Database (База данных)

### database/db_manager.py
**Назначение:** Главный класс Database (фасад)

**Методы:**
```python
class Database:
    # Инициализация
    def __init__(self, db_path="isp_bot.db")
    def create_tables()
    
    # Сотрудники
    def add_employee(full_name)
    def get_all_employees()
    def get_employee_by_id(id)
    def delete_employee(id)
    
    # Материалы
    def add_material_to_employee(emp_id, fiber, twisted)
    def deduct_material_from_employee(emp_id, fiber, twisted)
    def get_employee_balance(emp_id)
    
    # Роутеры
    def add_router_to_employee(emp_id, router_name, quantity)
    def deduct_router_from_employee(emp_id, router_name, quantity)
    def get_employee_routers(emp_id)
    def get_router_quantity(emp_id, router_name)
    def get_all_router_names()
    
    # Подключения
    def create_connection(...)
    def get_connection_by_id(id)
    
    # Отчеты
    def get_employee_report(emp_id, days)
    def get_employee_movements(emp_id, start_date, end_date)
    
    # Логирование
    def log_material_movement(...)
```

**Особенности:**
- Row factory для dict-like результатов
- Автоматическое логирование операций
- Транзакционность операций

---

### database/base_repository.py
**Назначение:** Базовый класс для репозиториев

**Методы:**
```python
class BaseRepository:
    def get_connection() -> sqlite3.Connection
    def execute_query(query, params, fetch_one, fetch_all)
```

**Преимущества:**
- DRY (Don't Repeat Yourself)
- Единая обработка ошибок
- Упрощенный SQL

---

### database/repositories/

**Структура:** Репозитории по сущностям

#### employee_repository.py
```python
class EmployeeRepository(BaseRepository):
    def create(full_name) -> Optional[int]
    def get_all() -> List[Dict]
    def get_by_id(id) -> Optional[Dict]
    def delete(id) -> bool
    def update_balance(id, fiber, twisted) -> bool
```

#### connection_repository.py
```python
class ConnectionRepository(BaseRepository):
    def create(...) -> Optional[int]
    def get_by_id(id) -> Optional[Dict]
    def get_by_employee(emp_id, days) -> List[Dict]
    def get_all() -> List[Dict]
```

#### material_repository.py
```python
class MaterialRepository(BaseRepository):
    def add_material(emp_id, fiber, twisted) -> bool
    def deduct_material(emp_id, fiber, twisted) -> bool
    def get_balance(emp_id) -> Tuple[float, float]
    def get_movements(emp_id, start, end) -> List[Dict]
    def log_movement(...) -> bool
```

#### router_repository.py
```python
class RouterRepository(BaseRepository):
    def add_router(emp_id, name, quantity) -> bool
    def deduct_router(emp_id, name, quantity) -> bool
    def get_routers(emp_id) -> List[Dict]
    def get_quantity(emp_id, name) -> int
    def get_all_names() -> List[str]
```

**Паттерн:** Repository Pattern
- Инкапсуляция логики доступа к данным
- Легкость тестирования (mock repositories)
- Независимость от конкретной БД

---

## Utils (Утилиты)

### utils/validators.py
**Назначение:** Валидация данных

**Класс Validator:**
```python
class Validator:
    @staticmethod
    def validate_number(text, min_value, allow_zero) 
        -> Tuple[bool, Optional[float], str]
    
    @staticmethod
    def validate_integer(text, min_value) 
        -> Tuple[bool, Optional[int], str]
    
    @staticmethod
    def validate_text(text, min_length, max_length) 
        -> Tuple[bool, str]
    
    @staticmethod
    def is_cancel_command(text) -> bool
    
    @staticmethod
    def is_skip_value(value) -> bool
```

**Использование:**
```python
from utils.validators import Validator

valid, value, error = Validator.validate_number(text, min_value=0)
if not valid:
    await update.message.reply_text(error)
    return SAME_STATE

# Продолжить обработку
context.user_data['fiber'] = value
```

---

### utils/formatters.py
**Назначение:** Форматирование текстов

**Класс TextFormatter:**
```python
class TextFormatter:
    @staticmethod
    def format_connection_type(conn_type) -> str
    
    @staticmethod
    def format_router_info(model, quantity) -> str
    
    @staticmethod
    def format_port(port) -> str
    
    @staticmethod
    def format_contract_status(signed) -> bool
    
    @staticmethod
    def format_date(dt) -> str
    
    @staticmethod
    def format_employee_list(names, prefix) -> str
```

**Класс MessageBuilder:**
```python
class MessageBuilder:
    @staticmethod
    def build_step_header(step, total, title) -> str
    
    @staticmethod
    def build_confirmation_message(...) -> str
```

**Использование:**
```python
from utils.formatters import TextFormatter, MessageBuilder

# Форматирование
router_info = TextFormatter.format_router_info("TP-Link", 2)
# "TP-Link (2 шт.)"

# Построение сообщения
message = MessageBuilder.build_confirmation_message(...)
await update.message.reply_text(message)
```

---

### utils/keyboards.py
**Назначение:** Фабрики клавиатур

**Функции:**
```python
def get_main_keyboard() -> ReplyKeyboardMarkup
    # Главная клавиатура с кнопками меню
```

**Особенности:**
- Переиспользуемые клавиатуры
- Удобство добавления новых кнопок

---

### utils/helpers.py
**Назначение:** Вспомогательные функции

**Функции:**
```python
async def send_connection_report(message, connection_id, data, photos, employees, db)
    # Отправка отчета с фотографиями

def _format_report_text(connection_id, data, employee_names) -> str
    # Форматирование текста отчета

def _create_media_group(photos, caption) -> List[InputMediaPhoto]
    # Создание медиа-группы
```

**Использует:**
- `TextFormatter` для форматирования
- `REPORTS_CHANNEL_ID` для отправки в канал

---

## Взаимосвязи модулей

### Диаграмма зависимостей

```
                    bot.py
                      │
        ┌─────────────┼─────────────┐
        │             │             │
    handlers/    handlers/    handlers/
   connection   employees     reports
        │             │             │
        └─────────────┴─────────────┘
                      │
            ┌─────────┴─────────┐
            │                   │
         utils/            database/
   (validators,         (db_manager,
    formatters,          repositories)
    keyboards,
    helpers)
            │                   │
            └─────────┬─────────┘
                      │
               report_generator.py
```

### Потоки вызовов

#### Создание подключения
```
User → bot.py → handlers/connection/conversation.py
                        ↓
                handlers/connection/steps.py
                        ↓
                utils/validators.py (валидация)
                        ↓
                handlers/connection/validation.py (проверка)
                        ↓
                database/db_manager.py
                        ↓
                database/repositories/* (CRUD)
                        ↓
                handlers/connection/confirmation.py
                        ↓
                utils/helpers.py (отправка отчета)
```

#### Управление материалами
```
User → bot.py → handlers/employees/flow.py
                        ↓
                utils/validators.py
                        ↓
                database/db_manager.py
                        ↓
                database/repositories/material_repository.py
                        ↓
                (logging) database/repositories/material_repository.py
```

### Принципы взаимодействия

1. **Слои не пропускаются**
   - Handlers → Utils/Database (✓)
   - Handlers → Repositories (✗)

2. **Dependency Injection**
   - Database передается как параметр
   - Упрощает тестирование

3. **Разделение ответственности**
   - Handlers - UI логика
   - Utils - бизнес-логика
   - Database - доступ к данным

4. **Переиспользование кода**
   - Validators используются всеми handlers
   - Formatters используются для отчетов и сообщений

---

## Лучшие практики

### При добавлении нового функционала

1. **Определите слой**
   - UI логика → handlers/
   - Валидация → utils/validators.py
   - Форматирование → utils/formatters.py
   - Доступ к данным → database/repositories/

2. **Используйте существующие компоненты**
   - Не создавайте дублирующий код
   - Расширяйте существующие классы

3. **Следуйте паттернам**
   - ConversationHandler для диалогов
   - Repository для БД
   - Validator для валидации

4. **Документируйте**
   - Docstrings для всех функций
   - Комментарии для сложной логики

### При рефакторинге

1. **Выделяйте общий код**
2. **Создавайте вспомогательные функции**
3. **Разбивайте большие файлы**
4. **Пишите тесты**

---

## Заключение

Модульная архитектура проекта обеспечивает:
- ✅ Легкость поддержки
- ✅ Упрощенное тестирование
- ✅ Переиспользование кода
- ✅ Понятную структуру
- ✅ Масштабируемость

Следование этому руководству поможет поддерживать высокое качество кода и упростит дальнейшую разработку.

