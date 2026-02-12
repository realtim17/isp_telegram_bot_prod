"""
Модуль для работы с базой данных SQLite
Использует паттерн Repository для разделения ответственности
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

from database.repositories.employee_repository import EmployeeRepository
from database.repositories.material_repository import MaterialRepository
from database.repositories.router_repository import RouterRepository
from database.repositories.connection_repository import ConnectionRepository

logger = logging.getLogger(__name__)


class Database:
    """
    Класс для работы с базой данных
    Использует композицию репозиториев для разделения ответственности
    """
    
    def __init__(self, db_path: str = "isp_bot.db"):
        """Инициализация подключения к БД и репозиториев"""
        self.db_path = db_path
        
        # Инициализация репозиториев
        self.employees_repo = EmployeeRepository(db_path)
        self.materials_repo = MaterialRepository(db_path)
        self.routers_repo = RouterRepository(db_path)
        self.connections_repo = ConnectionRepository(db_path)
        
        # Создаем таблицы
        self.create_tables()
    
    def get_connection(self) -> sqlite3.Connection:
        """Получить подключение к БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_tables(self):
        """Создать таблицы БД"""
        conn = self.get_connection()
<<<<<<< Updated upstream
        cursor = conn.cursor()
        
        # Таблица сотрудников
=======
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY
                )
            """)
            cursor.execute("SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations")
            current_version = cursor.fetchone()[0] or 0
            
            migrations = [
                self._migration_v1,
                self._migration_v2,
                self._migration_v3,
                self._migration_v4,
                self._migration_v5,
                self._migration_v6,
                self._migration_v7,
                self._migration_v8,
                self._migration_v9,
                self._migration_v10,
            ]
            
            if current_version >= len(migrations):
                logger.info("Миграции не требуются, текущая версия схемы: %s", current_version)
                return
            
            conn.execute("BEGIN")
            for idx, migration in enumerate(migrations, start=1):
                if idx > current_version:
                    migration(cursor)
                    cursor.execute("INSERT INTO schema_migrations (version) VALUES (?)", (idx,))
                    logger.info("Применена миграция %s", idx)
            conn.commit()
            logger.info("Схема обновлена до версии %s", len(migrations))
        except Exception as exc:
            conn.rollback()
            logger.error("Ошибка при применении миграций: %s", exc)
            raise
        finally:
            conn.close()

    def _migration_v1(self, cursor: sqlite3.Cursor) -> None:
        """Базовая схема + все текущие поля"""
        # Сотрудники
>>>>>>> Stashed changes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL UNIQUE,
                fiber_balance REAL DEFAULT 0,
                twisted_pair_balance REAL DEFAULT 0,
                twisted_pair_external_balance REAL DEFAULT 0,
                twisted_pair_internal_balance REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Добавляем поля балансов в существующую таблицу (если их нет)
        try:
            cursor.execute("ALTER TABLE employees ADD COLUMN fiber_balance REAL DEFAULT 0")
            logger.info("Добавлено поле fiber_balance в таблицу employees")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE employees ADD COLUMN twisted_pair_balance REAL DEFAULT 0")
            logger.info("Добавлено поле twisted_pair_balance в таблицу employees")
        except sqlite3.OperationalError:
            pass
<<<<<<< Updated upstream
        
        # Таблица подключений
=======
        try:
            cursor.execute("ALTER TABLE employees ADD COLUMN twisted_pair_external_balance REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE employees ADD COLUMN twisted_pair_internal_balance REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        # Подключения
>>>>>>> Stashed changes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_type TEXT NOT NULL DEFAULT 'mkd',
                address TEXT NOT NULL,
                router_model TEXT NOT NULL,
<<<<<<< Updated upstream
                port TEXT NOT NULL,
                fiber_meters REAL NOT NULL,
                twisted_pair_meters REAL NOT NULL,
=======
                snr_box_model TEXT NOT NULL DEFAULT '-',
                snr_box_quantity INTEGER NOT NULL DEFAULT 0,
                comment TEXT DEFAULT '',
                bitrix_task_url TEXT NOT NULL DEFAULT '-',
                account_number TEXT NOT NULL DEFAULT '',
                port TEXT NOT NULL,
                fiber_meters REAL NOT NULL,
                twisted_pair_meters REAL NOT NULL,
                twisted_pair_external_meters REAL NOT NULL DEFAULT 0,
                twisted_pair_internal_meters REAL NOT NULL DEFAULT 0,
                hooks_quantity REAL NOT NULL DEFAULT 0,
                ork_quantity REAL NOT NULL DEFAULT 0,
                mufta_quantity REAL NOT NULL DEFAULT 0,
                onu_model TEXT NOT NULL DEFAULT '-',
                onu_quantity INTEGER NOT NULL DEFAULT 0,
                media_converter_model TEXT NOT NULL DEFAULT '-',
                media_converter_quantity INTEGER NOT NULL DEFAULT 0,
>>>>>>> Stashed changes
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER NOT NULL
            )
        """)
<<<<<<< Updated upstream
        
        # Добавляем поле connection_type в существующую таблицу (если его нет)
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN connection_type TEXT NOT NULL DEFAULT 'mkd'")
            logger.info("Добавлено поле connection_type в таблицу connections")
        except sqlite3.OperationalError:
            # Поле уже существует
            pass
        
        # Добавляем поле router_quantity в существующую таблицу (если его нет)
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN router_quantity INTEGER DEFAULT 1")
            logger.info("Добавлено поле router_quantity в таблицу connections")
        except sqlite3.OperationalError:
            # Поле уже существует
            pass
        
        # Добавляем поле contract_signed в существующую таблицу (если его нет)
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN contract_signed INTEGER DEFAULT 0")
            logger.info("Добавлено поле contract_signed в таблицу connections")
        except sqlite3.OperationalError:
            # Поле уже существует
            pass
        
        # Добавляем поле router_access в существующую таблицу (если его нет)
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN router_access INTEGER DEFAULT 0")
            logger.info("Добавлено поле router_access в таблицу connections")
        except sqlite3.OperationalError:
            # Поле уже существует
            pass
        
        # Добавляем поле telegram_bot_connected в существующую таблицу (если его нет)
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN telegram_bot_connected INTEGER DEFAULT 0")
            logger.info("Добавлено поле telegram_bot_connected в таблицу connections")
        except sqlite3.OperationalError:
            # Поле уже существует
            pass
        
        # Таблица связи подключений и сотрудников (многие ко многим)
=======
        for stmt in (
            "ALTER TABLE connections ADD COLUMN connection_type TEXT NOT NULL DEFAULT 'mkd'",
            "ALTER TABLE connections ADD COLUMN snr_box_quantity INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE connections ADD COLUMN router_quantity INTEGER DEFAULT 1",
            "ALTER TABLE connections ADD COLUMN snr_box_model TEXT NOT NULL DEFAULT '-'",
            "ALTER TABLE connections ADD COLUMN comment TEXT DEFAULT ''",
            "ALTER TABLE connections ADD COLUMN bitrix_task_url TEXT NOT NULL DEFAULT '-'",
            "ALTER TABLE connections ADD COLUMN account_number TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE connections ADD COLUMN contract_signed INTEGER DEFAULT 0",
            "ALTER TABLE connections ADD COLUMN router_access INTEGER DEFAULT 0",
            "ALTER TABLE connections ADD COLUMN telegram_bot_connected INTEGER DEFAULT 0",
            "ALTER TABLE connections ADD COLUMN twisted_pair_external_meters REAL NOT NULL DEFAULT 0",
            "ALTER TABLE connections ADD COLUMN twisted_pair_internal_meters REAL NOT NULL DEFAULT 0",
            "ALTER TABLE connections ADD COLUMN hooks_quantity REAL NOT NULL DEFAULT 0",
            "ALTER TABLE connections ADD COLUMN ork_quantity REAL NOT NULL DEFAULT 0",
            "ALTER TABLE connections ADD COLUMN mufta_quantity REAL NOT NULL DEFAULT 0",
            "ALTER TABLE connections ADD COLUMN onu_model TEXT NOT NULL DEFAULT '-'",
            "ALTER TABLE connections ADD COLUMN onu_quantity INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE connections ADD COLUMN media_converter_model TEXT NOT NULL DEFAULT '-'",
            "ALTER TABLE connections ADD COLUMN media_converter_quantity INTEGER NOT NULL DEFAULT 0",
        ):
            try:
                cursor.execute(stmt)
            except sqlite3.OperationalError:
                pass

>>>>>>> Stashed changes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connection_employees (
                connection_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                PRIMARY KEY (connection_id, employee_id),
                FOREIGN KEY (connection_id) REFERENCES connections(id) ON DELETE CASCADE,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            )
        """)
        
        # Таблица фотографий подключений
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connection_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_id INTEGER NOT NULL,
                photo_file_id TEXT NOT NULL,
                photo_category TEXT NOT NULL DEFAULT 'other',
                photo_order INTEGER NOT NULL,
                FOREIGN KEY (connection_id) REFERENCES connections(id) ON DELETE CASCADE
            )
        """)
        
        # Добавляем поле photo_category в существующую таблицу (если его нет)
        try:
            cursor.execute("ALTER TABLE connection_photos ADD COLUMN photo_category TEXT NOT NULL DEFAULT 'other'")
            logger.info("Добавлено поле photo_category в таблицу connection_photos")
        except sqlite3.OperationalError:
            # Поле уже существует
            pass
        
        # Таблица роутеров сотрудников
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_routers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                router_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            )
        """)
        
        # Таблица логов движения материалов и роутеров
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS material_movement_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                operation_type TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_name TEXT,
                quantity REAL NOT NULL,
                balance_after REAL,
                connection_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (connection_id) REFERENCES connections(id) ON DELETE SET NULL
            )
        """)
<<<<<<< Updated upstream
        
        conn.commit()
        conn.close()
        logger.info("Таблицы БД созданы успешно")
=======

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_access (
                user_id INTEGER PRIMARY KEY,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_admins (
                user_id INTEGER PRIMARY KEY,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_material_movement_employee_created
            ON material_movement_log (employee_id, created_at)
        """)

    def _migration_v2(self, cursor: sqlite3.Cursor) -> None:
        """Индекс для ускорения выборок по connection_id в логе материалов"""
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_material_movement_connection
            ON material_movement_log (connection_id)
        """)
    
    def _migration_v3(self, cursor: sqlite3.Cursor) -> None:
        """Комментарий по подключению"""
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN comment TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

    def _migration_v4(self, cursor: sqlite3.Cursor) -> None:
        """Комментарий в логе движения материалов"""
        try:
            cursor.execute("ALTER TABLE material_movement_log ADD COLUMN comment TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

    def _migration_v5(self, cursor: sqlite3.Cursor) -> None:
        """Хранение выданного оборудования в connections"""
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN snr_box_quantity INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN onu_model TEXT NOT NULL DEFAULT '-'")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN onu_quantity INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN media_converter_model TEXT NOT NULL DEFAULT '-'")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN media_converter_quantity INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass

    def _migration_v6(self, cursor: sqlite3.Cursor) -> None:
        """Хранение SFP модулей сотрудников"""
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS employee_sfp_modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                module_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            )
            """
        )

    def _migration_v7(self, cursor: sqlite3.Cursor) -> None:
        """Сохранение выданных SFP модулей в подключениях"""
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN sfp_module_model TEXT NOT NULL DEFAULT '-'")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN sfp_module_quantity INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass

    def _migration_v8(self, cursor: sqlite3.Cursor) -> None:
        """Добавление полей для учета магистральных линий."""
        for stmt in (
            "ALTER TABLE connections ADD COLUMN hooks_quantity REAL NOT NULL DEFAULT 0",
            "ALTER TABLE connections ADD COLUMN ork_quantity REAL NOT NULL DEFAULT 0",
            "ALTER TABLE connections ADD COLUMN mufta_quantity REAL NOT NULL DEFAULT 0",
        ):
            try:
                cursor.execute(stmt)
            except sqlite3.OperationalError:
                pass

    def _migration_v9(self, cursor: sqlite3.Cursor) -> None:
        """Разделение витой пары на внешнюю и внутреннюю."""
        for stmt in (
            "ALTER TABLE employees ADD COLUMN twisted_pair_external_balance REAL DEFAULT 0",
            "ALTER TABLE employees ADD COLUMN twisted_pair_internal_balance REAL DEFAULT 0",
            "ALTER TABLE connections ADD COLUMN twisted_pair_external_meters REAL NOT NULL DEFAULT 0",
            "ALTER TABLE connections ADD COLUMN twisted_pair_internal_meters REAL NOT NULL DEFAULT 0",
        ):
            try:
                cursor.execute(stmt)
            except sqlite3.OperationalError:
                pass

        # Исторические данные распределяем поровну, только если новые поля ещё пустые.
        cursor.execute(
            """
            UPDATE employees
            SET twisted_pair_external_balance = ROUND(COALESCE(twisted_pair_balance, 0) / 2.0, 2),
                twisted_pair_internal_balance = COALESCE(twisted_pair_balance, 0) - ROUND(COALESCE(twisted_pair_balance, 0) / 2.0, 2)
            WHERE COALESCE(twisted_pair_balance, 0) > 0
              AND COALESCE(twisted_pair_external_balance, 0) = 0
              AND COALESCE(twisted_pair_internal_balance, 0) = 0
            """
        )
        cursor.execute(
            """
            UPDATE connections
            SET twisted_pair_external_meters = ROUND(COALESCE(twisted_pair_meters, 0) / 2.0, 2),
                twisted_pair_internal_meters = COALESCE(twisted_pair_meters, 0) - ROUND(COALESCE(twisted_pair_meters, 0) / 2.0, 2)
            WHERE COALESCE(twisted_pair_meters, 0) > 0
              AND COALESCE(twisted_pair_external_meters, 0) = 0
              AND COALESCE(twisted_pair_internal_meters, 0) = 0
            """
        )

    def _migration_v10(self, cursor: sqlite3.Cursor) -> None:
        """Поля подключения: Bitrix24 и лицевой счет."""
        for stmt in (
            "ALTER TABLE connections ADD COLUMN bitrix_task_url TEXT NOT NULL DEFAULT '-'",
            "ALTER TABLE connections ADD COLUMN account_number TEXT NOT NULL DEFAULT ''",
        ):
            try:
                cursor.execute(stmt)
            except sqlite3.OperationalError:
                pass
>>>>>>> Stashed changes
    
    # ==================== ЛОГИРОВАНИЕ ДВИЖЕНИЙ ====================
    
    def log_material_movement(self, employee_id: int, operation_type: str, item_type: str,
                             item_name: str, quantity: float, balance_after: float,
                             connection_id: Optional[int] = None, created_by: Optional[int] = None) -> bool:
        """Записать движение материала/роутера в лог
        
        Args:
            employee_id: ID сотрудника
            operation_type: 'add' или 'deduct'
            item_type: 'fiber', 'twisted_pair', 'router'
            item_name: Название (для роутера) или тип материала
            quantity: Количество
            balance_after: Остаток после операции
            connection_id: ID подключения (если списание при подключении)
            created_by: ID пользователя, выполнившего операцию
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO material_movement_log 
                (employee_id, operation_type, item_type, item_name, quantity, 
                 balance_after, connection_id, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (employee_id, operation_type, item_type, item_name, quantity,
                  balance_after, connection_id, created_by))
            conn.commit()
            conn.close()
            logger.info(f"Logged movement: {operation_type} {quantity} {item_type} for employee {employee_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при логировании движения: {e}")
            return False
    
    # ==================== СОТРУДНИКИ ====================
    
    # ==================== СОТРУДНИКИ (делегирование EmployeeRepository) ====================
    
    def add_employee(self, full_name: str) -> Optional[int]:
        """Добавить нового сотрудника"""
        employee_id = self.employees_repo.create(full_name)
        if employee_id:
            logger.info(f"Добавлен сотрудник: {full_name} (ID: {employee_id})")
        return employee_id
    
    def get_all_employees(self) -> List[Dict]:
        """Получить список всех сотрудников"""
        return self.employees_repo.get_all()
    
    def get_employee_by_id(self, employee_id: int) -> Optional[Dict]:
        """Получить сотрудника по ID"""
        return self.employees_repo.get_by_id(employee_id)
    
    def delete_employee(self, employee_id: int) -> bool:
        """Удалить сотрудника"""
        return self.employees_repo.delete(employee_id)
    
    # ==================== МАТЕРИАЛЫ (делегирование MaterialRepository) ====================
    
<<<<<<< Updated upstream
    def add_material_to_employee(self, employee_id: int, fiber_meters: float = 0, 
                                 twisted_pair_meters: float = 0, created_by: Optional[int] = None) -> bool:
        """Добавить материалы на баланс сотрудника"""
        return self.materials_repo.add_material(employee_id, fiber_meters, twisted_pair_meters, created_by)
    
    def deduct_material_from_employee(self, employee_id: int, fiber_meters: float = 0,
                                      twisted_pair_meters: float = 0, 
                                      connection_id: Optional[int] = None,
                                      created_by: Optional[int] = None) -> bool:
        """Списать материалы с баланса сотрудника"""
        return self.materials_repo.deduct_material(employee_id, fiber_meters, twisted_pair_meters, connection_id, created_by)
=======
    def add_material_to_employee(
        self,
        employee_id: int,
        fiber_meters: float = 0,
        twisted_pair_meters: float = 0,
        created_by: Optional[int] = None,
        comment: str = "",
        twisted_pair_external_meters: float = 0,
        twisted_pair_internal_meters: float = 0,
    ) -> bool:
        """Добавить материалы на баланс сотрудника"""
        return self.materials_repo.add_material(
            employee_id=employee_id,
            fiber_meters=fiber_meters,
            twisted_pair_meters=twisted_pair_meters,
            twisted_pair_external_meters=twisted_pair_external_meters,
            twisted_pair_internal_meters=twisted_pair_internal_meters,
            created_by=created_by,
            comment=comment,
        )
    
    def deduct_material_from_employee(
        self,
        employee_id: int,
        fiber_meters: float = 0,
        twisted_pair_meters: float = 0,
        connection_id: Optional[int] = None,
        created_by: Optional[int] = None,
        comment: str = "",
        twisted_pair_external_meters: float = 0,
        twisted_pair_internal_meters: float = 0,
    ) -> bool:
        """Списать материалы с баланса сотрудника"""
        return self.materials_repo.deduct_material(
            employee_id=employee_id,
            fiber_meters=fiber_meters,
            twisted_pair_meters=twisted_pair_meters,
            twisted_pair_external_meters=twisted_pair_external_meters,
            twisted_pair_internal_meters=twisted_pair_internal_meters,
            connection_id=connection_id,
            created_by=created_by,
            comment=comment,
        )
>>>>>>> Stashed changes
    
    def get_employee_balance(self, employee_id: int) -> Optional[Tuple[float, float]]:
        """Получить баланс материалов сотрудника (ВОЛС, Витая пара)"""
        return self.employees_repo.get_balance(employee_id)
    
    # ==================== РОУТЕРЫ (делегирование RouterRepository) ====================
    
    def add_router_to_employee(self, employee_id: int, router_name: str, quantity: int,
                              created_by: Optional[int] = None) -> bool:
        """Добавить роутеры сотруднику"""
        return self.routers_repo.add_router(employee_id, router_name, quantity, created_by)
    
    def deduct_router_from_employee(self, employee_id: int, router_name: str, quantity: int = 1,
                                    connection_id: Optional[int] = None,
                                    created_by: Optional[int] = None) -> bool:
        """Списать роутер у сотрудника"""
        return self.routers_repo.deduct_router(employee_id, router_name, quantity, connection_id, created_by)
    
    def get_employee_routers(self, employee_id: int) -> List[Dict]:
        """Получить список роутеров сотрудника"""
        return self.routers_repo.get_routers(employee_id)
    
    def get_router_quantity(self, employee_id: int, router_name: str) -> int:
        """Получить количество конкретного роутера у сотрудника"""
        return self.routers_repo.get_quantity(employee_id, router_name)
    
    def get_all_router_names(self) -> List[str]:
        """Получить список всех уникальных названий роутеров"""
        return self.routers_repo.get_all_names()
    
    def get_employee_movements(self, employee_id: int, start_date: datetime, 
                              end_date: datetime) -> List[Dict]:
        """Получить все движения материалов и роутеров сотрудника за период"""
        return self.materials_repo.get_movements(employee_id, start_date, end_date)
    
    # ==================== ПОДКЛЮЧЕНИЯ ====================
    
    def create_connection(
        self,
        connection_type: str,
        address: str,
        router_model: str,
        port: str,
        fiber_meters: float,
        twisted_pair_meters: float,
        employee_ids: List[int],
        photo_file_ids: List[str],
        created_by: int,
<<<<<<< Updated upstream
=======
        fiber_payer_id: Optional[int] = None,
        twisted_payer_id: Optional[int] = None,
        twisted_pair_external_meters: float = 0,
        twisted_pair_internal_meters: float = 0,
        twisted_external_payer_id: Optional[int] = None,
        twisted_internal_payer_id: Optional[int] = None,
        hooks_quantity: float = 0,
        ork_quantity: float = 0,
        mufta_quantity: float = 0,
>>>>>>> Stashed changes
        material_payer_id: Optional[int] = None,
        router_quantity: int = 1,
        contract_signed: bool = False,
        router_access: bool = False,
<<<<<<< Updated upstream
        telegram_bot_connected: bool = False
=======
        telegram_bot_connected: bool = False,
        router_payer_id: Optional[int] = None,
        snr_box_payer_id: Optional[int] = None,
        snr_box_quantity: int = 0,
        onu_model: str = '-',
        onu_quantity: int = 0,
        onu_payer_id: Optional[int] = None,
        media_converter_model: str = '-',
        media_converter_quantity: int = 0,
        media_payer_id: Optional[int] = None,
        sfp_module_model: str = '-',
        sfp_module_quantity: int = 0,
        sfp_payer_id: Optional[int] = None,
        bitrix_task_url: str = "-",
        account_number: str = "",
        comment: str = "",
>>>>>>> Stashed changes
    ) -> Optional[int]:
        """Создать новое подключение и списать материалы с указанного сотрудника
        
        Args:
            material_payer_id: ID сотрудника, с которого списывать материалы.
                              Если None, материалы списываются поровну со всех.
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
<<<<<<< Updated upstream
            
            # Создаем запись подключения
            cursor.execute("""
                INSERT INTO connections 
                (connection_type, address, router_model, port, fiber_meters, twisted_pair_meters, created_by, router_quantity, contract_signed, router_access, telegram_bot_connected)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (connection_type, address, router_model, port, fiber_meters, twisted_pair_meters, created_by, router_quantity, 1 if contract_signed else 0, 1 if router_access else 0, 1 if telegram_bot_connected else 0))
            
=======

            twisted_external = float(twisted_pair_external_meters or 0)
            twisted_internal = float(twisted_pair_internal_meters or 0)
            twisted_total = float(twisted_pair_meters or 0)
            if twisted_external == 0 and twisted_internal == 0 and twisted_total != 0:
                twisted_external = round(twisted_total / 2, 2)
                twisted_internal = round(twisted_total - twisted_external, 2)
            twisted_total = twisted_external + twisted_internal

            cursor.execute("""
                INSERT INTO connections 
                (connection_type, address, router_model, snr_box_model, snr_box_quantity, comment, bitrix_task_url, account_number, port, fiber_meters, twisted_pair_meters, twisted_pair_external_meters, twisted_pair_internal_meters, hooks_quantity, ork_quantity, mufta_quantity, created_by, router_quantity, contract_signed, router_access, telegram_bot_connected, onu_model, onu_quantity, media_converter_model, media_converter_quantity, sfp_module_model, sfp_module_quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                connection_type, address, router_model, snr_box_model, snr_box_quantity or 0, comment or "",
                bitrix_task_url or "-", str(account_number or ""),
                port, fiber_meters, twisted_total, twisted_external, twisted_internal,
                hooks_quantity or 0, ork_quantity or 0, mufta_quantity or 0, created_by,
                router_quantity, 1 if contract_signed else 0,
                1 if router_access else 0, 1 if telegram_bot_connected else 0,
                onu_model or "-", onu_quantity or 0,
                media_converter_model or "-", media_converter_quantity or 0,
                sfp_module_model or "-", sfp_module_quantity or 0,
            ))

>>>>>>> Stashed changes
            connection_id = cursor.lastrowid
            
            # Связываем всех сотрудников с подключением
            for emp_id in employee_ids:
                cursor.execute("""
                    INSERT INTO connection_employees (connection_id, employee_id)
                    VALUES (?, ?)
                """, (connection_id, emp_id))
<<<<<<< Updated upstream
=======

            default_material_payer = material_payer_id or (employee_ids[0] if employee_ids else None)
            if default_material_payer is None and (fiber_meters or twisted_total):
                raise RuntimeError("Не указан исполнитель для списания материалов.")

            fiber_owner = fiber_payer_id or default_material_payer
            twisted_external_owner = twisted_external_payer_id or twisted_payer_id or fiber_owner
            twisted_internal_owner = twisted_internal_payer_id or twisted_payer_id or twisted_external_owner

            if fiber_meters > 0 and fiber_owner is None:
                raise RuntimeError("Не выбран плательщик для списания ВОЛС.")
            if twisted_external > 0 and twisted_external_owner is None:
                raise RuntimeError("Не выбран плательщик для списания внешней витой пары.")
            if twisted_internal > 0 and twisted_internal_owner is None:
                raise RuntimeError("Не выбран плательщик для списания внутренней витой пары.")

            deductions: Dict[int, Dict[str, float]] = {}

            def _add_deduction(owner_id: Optional[int], key: str, value: float) -> None:
                if not owner_id or value <= 0:
                    return
                slot = deductions.setdefault(
                    owner_id,
                    {"fiber": 0.0, "twisted_external": 0.0, "twisted_internal": 0.0},
                )
                slot[key] += value

            _add_deduction(fiber_owner, "fiber", float(fiber_meters or 0))
            _add_deduction(twisted_external_owner, "twisted_external", twisted_external)
            _add_deduction(twisted_internal_owner, "twisted_internal", twisted_internal)

            for owner_id, amounts in deductions.items():
                if not self.materials_repo.deduct_material(
                    employee_id=owner_id,
                    fiber_meters=amounts["fiber"],
                    twisted_pair_external_meters=amounts["twisted_external"],
                    twisted_pair_internal_meters=amounts["twisted_internal"],
                    connection_id=connection_id,
                    created_by=created_by,
                    connection=conn,
                ):
                    raise RuntimeError(
                        f"Не удалось списать материалы с сотрудника ID {owner_id} "
                        f"(ВОЛС={amounts['fiber']}, Внеш. ВП={amounts['twisted_external']}, "
                        f"Внут. ВП={amounts['twisted_internal']})"
                    )

            # Списываем оборудование в рамках той же транзакции
            if router_payer_id and router_model and router_model != '-' and router_quantity > 0:
                if not self.routers_repo.deduct_router(
                    router_payer_id,
                    router_model,
                    router_quantity,
                    connection_id,
                    created_by,
                    connection=conn,
                ):
                    raise RuntimeError(
                        f"Не удалось списать роутер '{router_model}' x{router_quantity} с сотрудника ID {router_payer_id}"
                    )

            if snr_box_payer_id and snr_box_model and snr_box_model != '-':
                if not self.snr_repo.deduct_box(
                    snr_box_payer_id,
                    snr_box_model,
                    snr_box_quantity or 0,
                    connection_id,
                    created_by,
                    connection=conn,
                ):
                    raise RuntimeError(
                        f"Не удалось списать SNR бокс '{snr_box_model}' x{snr_box_quantity or 0} с сотрудника ID {snr_box_payer_id}"
                    )

            if onu_model and onu_model != '-' and onu_quantity > 0 and employee_ids:
                payer = onu_payer_id or employee_ids[0]
                if not self.onu_repo.deduct_onu(
                    payer,
                    onu_model,
                    onu_quantity,
                    connection_id,
                    created_by,
                    connection=conn,
                ):
                    raise RuntimeError(
                        f"Не удалось списать ONU '{onu_model}' x{onu_quantity} с сотрудника ID {payer}"
                    )

            if media_converter_model and media_converter_model != '-' and media_converter_quantity > 0 and employee_ids:
                payer = media_payer_id or employee_ids[0]
                if not self.media_repo.deduct_converter(
                    payer,
                    media_converter_model,
                    media_converter_quantity,
                    connection_id,
                    created_by,
                    connection=conn,
                ):
                    raise RuntimeError(
                        f"Не удалось списать медиаконвертор '{media_converter_model}' x{media_converter_quantity} с сотрудника ID {payer}"
                    )

            if sfp_module_model and sfp_module_model != '-' and sfp_module_quantity > 0 and employee_ids:
                payer = sfp_payer_id or employee_ids[0]
                if not self.sfp_repo.deduct_module(
                    payer,
                    sfp_module_model,
                    sfp_module_quantity,
                    connection_id,
                    created_by,
                    connection=conn,
                ):
                    raise RuntimeError(
                        f"Не удалось списать SFP модуль '{sfp_module_model}' x{sfp_module_quantity} с сотрудника ID {payer}"
                    )
>>>>>>> Stashed changes
            
            # Списываем материалы
            if material_payer_id:
                # Списываем весь материал с одного сотрудника
                cursor.execute("""
                    SELECT fiber_balance, twisted_pair_balance 
                    FROM employees 
                    WHERE id = ?
                """, (material_payer_id,))
                row = cursor.fetchone()
                
                if not row:
                    logger.error(f"Сотрудник ID {material_payer_id} не найден")
                    conn.close()
                    return None
                
                current_fiber = row[0] or 0
                current_twisted = row[1] or 0
                
                # Проверяем достаточность материалов
                if current_fiber < fiber_meters:
                    logger.warning(f"Недостаточно ВОЛС у сотрудника ID {material_payer_id}: "
                                 f"есть {current_fiber}м, требуется {fiber_meters}м")
                    conn.close()
                    return None
                
                if current_twisted < twisted_pair_meters:
                    logger.warning(f"Недостаточно витой пары у сотрудника ID {material_payer_id}: "
                                 f"есть {current_twisted}м, требуется {twisted_pair_meters}м")
                    conn.close()
                    return None
                
                # Сохраняем в БД перед логированием
                conn.commit()
                conn.close()
                
                # Списываем весь материал с одного сотрудника (с логированием)
                success = self.deduct_material_from_employee(
                    material_payer_id, fiber_meters, twisted_pair_meters,
                    connection_id, created_by
                )
                
                if not success:
                    logger.error(f"Не удалось списать материалы с сотрудника ID {material_payer_id}")
                    return None
                
                logger.info(f"Списано у сотрудника ID {material_payer_id}: "
                          f"ВОЛС -{fiber_meters}м, Витая пара -{twisted_pair_meters}м (полная сумма)")
                
                # Переоткрываем соединение для фото
                conn = self.get_connection()
                cursor = conn.cursor()
            else:
                # Старая логика: делим поровну между всеми
                emp_count = len(employee_ids)
                fiber_per_emp = fiber_meters / emp_count if emp_count > 0 else 0
                twisted_per_emp = twisted_pair_meters / emp_count if emp_count > 0 else 0
                
                # Сохраняем в БД перед логированием
                conn.commit()
                conn.close()
                
                for emp_id in employee_ids:
                    # Списываем с логированием
                    success = self.deduct_material_from_employee(
                        emp_id, fiber_per_emp, twisted_per_emp,
                        connection_id, created_by
                    )
                    
                    if not success:
                        logger.error(f"Не удалось списать материалы с сотрудника ID {emp_id}")
                    else:
                        logger.info(f"Списано у сотрудника ID {emp_id}: "
                                  f"ВОЛС -{fiber_per_emp}м, Витая пара -{twisted_per_emp}м")
                
                # Переоткрываем соединение для фото
                conn = self.get_connection()
                cursor = conn.cursor()
            
            # Сохраняем фотографии
            for idx, photo_id in enumerate(photo_file_ids):
                cursor.execute("""
                    INSERT INTO connection_photos (connection_id, photo_file_id, photo_category, photo_order)
                    VALUES (?, ?, ?, ?)
                """, (connection_id, photo_id, 'general', idx))
            
            conn.commit()
            conn.close()
            logger.info(f"Создано подключение ID: {connection_id}, материалы списаны")
            return connection_id
        except Exception as e:
            logger.error(f"Ошибка при создании подключения: {e}")
            return None
    
    def get_connection_by_id(self, connection_id: int) -> Optional[Dict]:
        """Получить подключение по ID"""
        return self.connections_repo.get_by_id(connection_id)
    
    # ==================== ОТЧЕТЫ ====================
    
    def get_employee_report(
        self,
        employee_id: int,
        days: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[List[Dict], Dict]:
        """
        Получить отчет по сотруднику за период
        
        Args:
            employee_id: ID сотрудника
            days: Количество дней (None = все время)
            start_date: Начало периода (приоритетнее параметра days)
            end_date: Конец периода (используется вместе со start_date)
        
        Returns:
            Tuple: (список подключений, итоговая статистика)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Формируем условие по дате
        date_condition = ""
        params = [employee_id]
        if start_date and end_date:
            date_condition = "AND c.created_at BETWEEN ? AND ?"
            params.append(start_date.strftime("%Y-%m-%d %H:%M:%S"))
            params.append(end_date.strftime("%Y-%m-%d %H:%M:%S"))
        elif start_date:
            date_condition = "AND c.created_at >= ?"
            params.append(start_date.strftime("%Y-%m-%d %H:%M:%S"))
        elif days is not None:
            date_limit = datetime.now() - timedelta(days=days)
            date_condition = "AND c.created_at >= ?"
            params.append(date_limit.strftime("%Y-%m-%d %H:%M:%S"))
        
        # Получаем подключения с участием сотрудника
        query = f"""
            SELECT 
                c.id,
                c.connection_type,
                c.address,
                c.router_model,
                c.port,
                c.fiber_meters,
                c.twisted_pair_meters,
                c.created_at,
                COUNT(DISTINCT ce.employee_id) as employee_count
            FROM connections c
            JOIN connection_employees ce ON c.id = ce.connection_id
            WHERE ce.connection_id IN (
                SELECT connection_id 
                FROM connection_employees 
                WHERE employee_id = ?
            )
            {date_condition}
            GROUP BY c.id
            ORDER BY c.created_at DESC
        """
        
        cursor.execute(query, params)
        connections = []
        
        total_fiber = 0.0
        total_twisted = 0.0
        
        for row in cursor.fetchall():
            conn_dict = dict(row)
            emp_count = conn_dict['employee_count']
            
            # Рассчитываем долю для сотрудника
            conn_dict['employee_fiber_meters'] = round(conn_dict['fiber_meters'] / emp_count, 2)
            conn_dict['employee_twisted_pair_meters'] = round(conn_dict['twisted_pair_meters'] / emp_count, 2)
            
            # Получаем список всех исполнителей для этого подключения
            cursor.execute("""
                SELECT e.full_name
                FROM employees e
                JOIN connection_employees ce ON e.id = ce.employee_id
                WHERE ce.connection_id = ?
                ORDER BY e.full_name
            """, (conn_dict['id'],))
            conn_dict['all_employees'] = [row['full_name'] for row in cursor.fetchall()]
            
            connections.append(conn_dict)
            total_fiber += conn_dict['employee_fiber_meters']
            total_twisted += conn_dict['employee_twisted_pair_meters']
        
        conn.close()
        
        stats = {
            'total_connections': len(connections),
            'total_fiber_meters': round(total_fiber, 2),
            'total_twisted_pair_meters': round(total_twisted, 2)
        }
        
        return connections, stats
    
    def get_all_connections_count(self) -> int:
        """Получить общее количество подключений"""
        return self.connections_repo.get_all_count()
