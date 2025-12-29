# Анализ кодовой базы ISP Telegram Bot

> **Дата анализа:** 29.12.2025  
> **Версия проекта:** текущая (post-Phase 2)

---

## Содержание

1. [Резюме](#резюме)
2. [Критические проблемы](#1-критические-проблемы)
3. [Серьёзные проблемы](#2-серьёзные-проблемы)
4. [Архитектурные недостатки](#3-архитектурные-недостатки)
5. [Технический долг](#4-технический-долг)
6. [Рекомендации по оптимизации](#5-рекомендации-по-оптимизации)
7. [Приоритизированный план действий](#6-приоритизированный-план-действий)

---

## Резюме

### Общая статистика

| Метрика | Значение |
|---------|----------|
| Всего строк кода (Python) | ~15,190 |
| Количество файлов .py | ~45 |
| Крупнейшие файлы (>500 LOC) | 7 |
| try/except блоков | ~102 |
| Bare except (антипаттерн) | 2 |
| context.user_data.clear() вызовов | 66 |

### Оценка рисков

| Категория | Уровень риска | Описание |
|-----------|---------------|----------|
| Стабильность БД | 🟡 Средний | SQLite lock при конкурентных запросах |
| Безопасность | 🟢 Низкий | Используется параметризованные запросы |
| Производительность | 🟡 Средний | Множественные DB-вызовы в цикле |
| Maintainability | 🔴 Высокий | Дублирование кода, крупные файлы |
| Масштабируемость | 🔴 Высокий | SQLite не для многопользовательского режима |

---

## 1. Критические проблемы

### 1.1 🔴 Риск блокировки SQLite при конкурентных операциях

**Файл:** `database/db_manager.py`, `database/base_repository.py`

**Проблема:**  
Каждая операция создаёт новое SQLite-подключение. При одновременных запросах от нескольких пользователей возможен `database is locked`.

```python
# Текущая реализация — каждый вызов = новое соединение
def get_connection(self) -> sqlite3.Connection:
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row
    return conn
```

**Последствия:**
- Ошибки при высокой нагрузке (3+ одновременных пользователей)
- Потеря данных при rollback
- Некорректное логирование операций

**Решение:**  
Использовать connection pool или единый connection с mutex. Либо переход на PostgreSQL.

**Приоритет:** 🔴 Критический

---

### 1.2 🔴 Отсутствие единой транзакции при создании подключения

**Файл:** `database/db_manager.py:316-411`

**Проблема:**  
Метод `create_connection` передаёт соединение в `materials_repo.deduct_material`, но не все операции выполняются в рамках одной транзакции. В случае сбоя между вставкой подключения и логированием — несогласованность данных.

```python
# Проблемный фрагмент
connection_id = cursor.lastrowid

# Вызов может использовать отдельный connection если передан неправильно
success = self.materials_repo.deduct_material(
    material_payer_id,
    ...
    connection=conn  # Передаётся, но не во всех путях
)
```

**Решение:**  
Рефакторинг `create_connection` с использованием единого курсора для всех операций.

**Приоритет:** 🔴 Критический

---

### 1.3 🔴 Некорректная обработка отсутствия ONU/Media/SFP при списании

**Файл:** `handlers/connection/confirmation.py:263-297`

**Проблема:**  
При вызове `db.create_connection` передаются параметры ONU/медиаконверторов/SFP модулей, но в `db_manager.py` нет проверки их наличия у сотрудника перед списанием. Если у сотрудника нет нужного оборудования — транзакция может не откатиться корректно.

**Решение:**  
Добавить валидацию наличия всего оборудования **до** начала транзакции.

**Приоритет:** 🔴 Критический

---

## 2. Серьёзные проблемы

### 2.1 🟠 Дублирование кода в репозиториях оборудования

**Файлы:**
- `database/repositories/onu_repository.py` (~185 LOC)
- `database/repositories/sfp_module_repository.py` (~183 LOC)
- `database/repositories/media_converter_repository.py` (~185 LOC)
- `database/repositories/router_repository.py` (~225 LOC)
- `database/repositories/snr_box_repository.py` (~225 LOC)

**Проблема:**  
Все 5 файлов содержат идентичную структуру с разными именами таблиц/полей. Суммарно ~1000 строк дублированного кода.

```python
# Одинаковая логика во всех репозиториях:
def add_device(self, employee_id, device_name, quantity, ...):
    # Upsert логика
    # Логирование движения
    
def deduct_device(self, employee_id, device_name, quantity, ...):
    # Проверка остатка
    # Вычитание
    # Логирование
```

**Решение:**  
Создать базовый класс `DeviceRepository` с параметризацией по типу устройства.

```python
class DeviceRepository(BaseRepository):
    table_name: str = "employee_devices"
    item_type: str = "device"
    
    def add(self, employee_id: int, name: str, qty: int, ...) -> bool:
        # Единая реализация
```

**Приоритет:** 🟠 Высокий

---

### 2.2 🟠 Дублирование handlers для управления оборудованием

**Файлы:**
- `handlers/employees/onu.py` (291 LOC)
- `handlers/employees/sfp_modules.py` (298 LOC)
- `handlers/employees/media_converters.py` (292 LOC)
- `handlers/employees/routers.py` (351 LOC)
- `handlers/employees/snr_boxes.py` (296 LOC)

**Проблема:**  
Логика обработки для всех типов оборудования практически идентична: выбор сотрудника → выбор действия → ввод модели → ввод количества → подтверждение.

**Решение:**  
Создать generic обработчик `DeviceFlowHandler` с конфигурацией для каждого типа устройства.

**Приоритет:** 🟠 Высокий

---

### 2.3 🟠 Bare except clauses

**Файл:** `report_generator.py:170, 675`

```python
try:
    created_at = datetime.fromisoformat(conn['created_at'])
    date_str = created_at.strftime('%d.%m.%Y %H:%M')
except:  # ❌ Bare except
    date_str = conn['created_at']
```

**Проблема:**  
Bare `except` перехватывает все исключения включая `KeyboardInterrupt`, `SystemExit`, затрудняет отладку.

**Решение:**  

```python
except (ValueError, TypeError) as e:
    logger.warning(f"Date parse error: {e}")
    date_str = str(conn.get('created_at', '-'))
```

**Приоритет:** 🟠 Средний

---

### 2.4 🟠 Отсутствие валидации ONU/Media/SFP в validation.py

**Файл:** `handlers/connection/validation.py`

**Проблема:**  
Функции `check_materials_and_proceed`, `check_routers_and_proceed`, `check_snr_boxes_and_proceed` проверяют только материалы, роутеры и SNR боксы. Проверка ONU, медиаконверторов и SFP модулей отсутствует.

**Решение:**  
Добавить функции `check_onu_and_proceed`, `check_media_and_proceed`, `check_sfp_and_proceed` с аналогичной логикой.

**Приоритет:** 🟠 Высокий

---

## 3. Архитектурные недостатки

### 3.1 🟡 Миграции через try/except ALTER TABLE

**Файл:** `database/db_manager.py:60-127`

```python
try:
    cursor.execute("ALTER TABLE employees ADD COLUMN fiber_balance REAL DEFAULT 0")
except sqlite3.OperationalError:
    pass  # Поле уже существует
```

**Проблема:**
- Миграции выполняются при каждом старте приложения
- Нет версионирования схемы
- Невозможно откатить миграцию
- Затруднена добавление сложных миграций

**Решение:**  
Реализовать систему версионных миграций:

```python
MIGRATIONS = {
    1: "CREATE TABLE employees ...",
    2: "ALTER TABLE employees ADD COLUMN fiber_balance ...",
    3: "CREATE INDEX idx_connections_created_at ...",
}

def apply_migrations(self):
    current_version = self._get_schema_version()
    for version in sorted(MIGRATIONS.keys()):
        if version > current_version:
            self._apply_migration(version, MIGRATIONS[version])
```

**Приоритет:** 🟡 Средний

---

### 3.2 🟡 Крупные файлы с нарушением Single Responsibility

| Файл | Строки | Проблема |
|------|--------|----------|
| `db_manager.py` | 836 | Смешаны миграции, CRUD, логирование |
| `tmc_flow.py` | 732 | Один файл для всего flow выдачи ТМЦ |
| `handlers/employees.py` | 760 | **Мёртвый код** — не импортируется, дублирует `handlers/employees/` |
| `report_generator.py` | 731 | Два отчёта + движения в одном классе |

**Решение:**
- Выделить миграции в `database/migrations.py`
- Разбить `tmc_flow.py` на модули по шагам
- Удалить `handlers/employees.py` (если не используется)
- Разделить `ReportGenerator` на `EmployeeReportGenerator` и `GlobalReportGenerator`

**Приоритет:** 🟡 Средний

---

### 3.3 🟡 Wrappers в conversation.py

**Файл:** `handlers/connection/conversation.py:91-161`

```python
async def contract_signed_wrapper(update, context):
    return await contract_signed(update, context, db)

async def telegram_bot_confirm_wrapper(update, context):
    return await telegram_bot_confirm(update, context, db)

# ... ещё 15 wrapper функций
```

**Проблема:**  
18 wrapper-функций для передачи `db` в обработчики. Увеличивает объём и сложность.

**Решение:**  
Использовать `functools.partial` или dependency injection через `context.bot_data`:

```python
# В bot.py
application.bot_data['db'] = db

# В обработчике
db = context.bot_data['db']
```

**Приоритет:** 🟡 Низкий

---

## 4. Технический долг

### 4.1 Отсутствие Type Hints

**Охват:** ~60% кода без type hints

```python
# Текущее состояние
def create_connection(self, connection_type, address, router_model, ...):
    
# Должно быть
def create_connection(
    self,
    connection_type: str,
    address: str,
    router_model: str,
    ...
) -> Optional[int]:
```

**Приоритет:** 🟢 Низкий (но улучшает maintainability)

---

### 4.2 Недостаточное тестирование

**Текущее состояние:**
- `test_database.py` — базовые тесты БД
- `test_material_logic.py` — тесты логики материалов

**Отсутствуют:**
- Тесты handlers
- Тесты отчётов
- Integration тесты ConversationHandler
- Тесты edge cases (отрицательные балансы, concurrent access)

**Приоритет:** 🟡 Средний

---

### 4.3 Отсутствие кэширования

**Проблема:**  
Список сотрудников, названия роутеров/ONU/SFP запрашиваются из БД при каждом шаге.

```python
# В каждом шаге:
employees = await run_in_thread(db.get_all_employees)
onu_names = await run_in_thread(db.get_all_onu_names)
```

**Решение:**  
Кэширование с инвалидацией при изменениях:

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def get_all_employees_cached(self, _cache_key: int) -> List[Dict]:
    return self.get_all_employees()
```

**Приоритет:** 🟢 Низкий

---

## 5. Рекомендации по оптимизации

### 5.1 База данных

| # | Рекомендация | Сложность | Эффект |
|---|--------------|-----------|--------|
| 1 | Connection pooling или единый connection | Средняя | 🔴 Высокий |
| 2 | Индексы на `material_movement_log(employee_id, created_at)` | Низкая | 🟡 Средний |
| 3 | Переход на PostgreSQL | Высокая | 🔴 Высокий |
| 4 | Batch операции для фотографий | Низкая | 🟢 Низкий |

### 5.2 Производительность handlers

| # | Рекомендация | Сложность | Эффект |
|---|--------------|-----------|--------|
| 1 | asyncio.gather для параллельных DB-запросов | Низкая | 🟡 Средний |
| 2 | Кэширование справочников | Средняя | 🟡 Средний |
| 3 | Сокращение числа сообщений (группировка) | Низкая | 🟢 Низкий |

### 5.3 Рефакторинг кода

| # | Рекомендация | Сложность | Эффект |
|---|--------------|-----------|--------|
| 1 | Generic DeviceRepository | Средняя | 🔴 Высокий |
| 2 | Generic DeviceFlowHandler | Высокая | 🔴 Высокий |
| 3 | Удаление legacy `handlers/employees.py` | Низкая | 🟡 Средний |
| 4 | Dependency Injection для db | Средняя | 🟡 Средний |

---

## 6. Приоритизированный план действий

### Фаза 1: Критические исправления (1-2 недели)

| Задача | Файлы | Описание | Оценка |
|--------|-------|----------|--------|
| **1.1** | `db_manager.py` | Исправить транзакционность `create_connection` | 4-6 ч |
| **1.2** | `validation.py` | Добавить проверку ONU/Media/SFP перед списанием | 2-3 ч |
| **1.3** | `base_repository.py` | Добавить retry logic для locked database | 2-4 ч |
| **1.4** | `report_generator.py` | Заменить bare except | 30 мин |

### Фаза 2: Рефакторинг репозиториев (2-3 недели)

| Задача | Файлы | Описание | Оценка |
|--------|-------|----------|--------|
| **2.1** | Новый `device_repository.py` | Создать generic репозиторий устройств | 8-12 ч |
| **2.2** | `onu/sfp/media/router/snr_repo.py` | Переписать на наследование от DeviceRepository | 4-6 ч |
| **2.3** | `db_manager.py` | Вынести миграции в отдельный модуль | 4-6 ч |
| **2.4** | Тесты | Написать тесты для нового репозитория | 4-6 ч |

### Фаза 3: Рефакторинг handlers (3-4 недели)

| Задача | Файлы | Описание | Оценка |
|--------|-------|----------|--------|
| **3.1** | Новый `device_handler.py` | Generic handler для всех типов устройств | 12-16 ч |
| **3.2** | `employees/*.py` | Переписать на использование DeviceHandler | 8-12 ч |
| **3.3** | `conversation.py` | Убрать wrappers через bot_data | 2-4 ч |
| **3.4** | Удаление | Удалить `handlers/employees.py` если не используется | 1-2 ч |

### Фаза 4: Инфраструктура и тестирование (2-3 недели)

| Задача | Описание | Оценка |
|--------|----------|--------|
| **4.1** | Настроить pre-commit hooks (black, flake8, mypy) | 2-4 ч |
| **4.2** | Добавить type hints в core модули | 8-12 ч |
| **4.3** | Написать unit тесты для handlers | 12-16 ч |
| **4.4** | Написать integration тесты | 8-12 ч |

### Фаза 5: Масштабирование (опционально, 4+ недели)

| Задача | Описание | Оценка |
|--------|----------|--------|
| **5.1** | Переход на PostgreSQL | 20-30 ч |
| **5.2** | Внедрение Alembic для миграций | 8-12 ч |
| **5.3** | Добавление Redis для кэширования | 8-12 ч |
| **5.4** | Celery для фоновых задач (отчёты) | 12-16 ч |

---

## Метрики успеха

### После Фазы 1
- ✅ Нет ошибок "database is locked" при 5+ пользователях
- ✅ Корректное списание всех типов оборудования
- ✅ Нет bare except в коде

### После Фазы 2
- ✅ Сокращение LOC в репозиториях на 600+ строк
- ✅ 100% покрытие тестами DeviceRepository
- ✅ Версионные миграции

### После Фазы 3
- ✅ Сокращение LOC в handlers на 800+ строк
- ✅ Единый интерфейс для всех устройств
- ✅ Нет wrapper-функций

### После Фазы 4
- ✅ >70% покрытие тестами
- ✅ Type hints во всех public методах
- ✅ CI/CD пайплайн с проверками

---

## Приложение: Быстрые победы (Quick Wins)

Изменения, которые можно внести немедленно с минимальным риском:

1. **Заменить bare except** в `report_generator.py` — 10 минут
2. **Добавить индекс** на `material_movement_log(connection_id)` — 5 минут
3. **Включить** `PRAGMA busy_timeout = 30000` (увеличить до 30 сек) — 5 минут
4. **Логировать** предупреждение при приближении к лимитам баланса — 30 минут

---

*Документ подготовлен на основе анализа кодовой базы версии post-Phase 2.*

