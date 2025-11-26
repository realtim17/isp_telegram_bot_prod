"""
Модуль для работы с базой данных SQLite
Использует паттерн Repository для разделения ответственности
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

from database.repositories.employee_repository import EmployeeRepository
from database.repositories.material_repository import MaterialRepository
from database.repositories.router_repository import RouterRepository
from database.repositories.snr_box_repository import SNRBoxRepository
from database.repositories.connection_repository import ConnectionRepository
from database.repositories.access_repository import AccessRepository
from database.repositories.admin_repository import AdminRepository
from database.repositories.onu_repository import ONURepository
from database.repositories.media_converter_repository import MediaConverterRepository

logger = logging.getLogger(__name__)


class Database:
    """
    Класс для работы с базой данных
    Использует композицию репозиториев для разделения ответственности
    """
    
    def __init__(self, db_path: str = "isp_bot.db"):
        """Инициализация подключения к БД и репозиториев"""
        base_dir = Path(__file__).resolve().parents[1]
        db_path = Path(db_path)
        if not db_path.is_absolute():
            db_path = (base_dir / db_path).resolve()
        self.db_path = str(db_path)
        
        # Инициализация репозиториев
        self.employees_repo = EmployeeRepository(self.db_path)
        self.materials_repo = MaterialRepository(self.db_path)
        self.routers_repo = RouterRepository(self.db_path)
        self.connections_repo = ConnectionRepository(self.db_path)
        self.snr_repo = SNRBoxRepository(self.db_path)
        self.access_repo = AccessRepository(self.db_path)
        self.admin_repo = AdminRepository(self.db_path)
        self.onu_repo = ONURepository(self.db_path)
        self.media_repo = MediaConverterRepository(self.db_path)
        
        # Создаем/обновляем схему
        self.create_tables()
    
    def get_connection(self) -> sqlite3.Connection:
        """Получить подключение к БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 15000")
        return conn
    
    def create_tables(self):
        """Применить миграции схемы атомарно"""
        conn = self.get_connection()
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL UNIQUE,
                fiber_balance REAL DEFAULT 0,
                twisted_pair_balance REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        try:
            cursor.execute("ALTER TABLE employees ADD COLUMN fiber_balance REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE employees ADD COLUMN twisted_pair_balance REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_type TEXT NOT NULL DEFAULT 'mkd',
                address TEXT NOT NULL,
                router_model TEXT NOT NULL,
                snr_box_model TEXT NOT NULL DEFAULT '-',
                port TEXT NOT NULL,
                fiber_meters REAL NOT NULL,
                twisted_pair_meters REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER NOT NULL
            )
        """)
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN connection_type TEXT NOT NULL DEFAULT 'mkd'")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN router_quantity INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN snr_box_model TEXT NOT NULL DEFAULT '-'")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN contract_signed INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN router_access INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN telegram_bot_connected INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connection_employees (
                connection_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                PRIMARY KEY (connection_id, employee_id),
                FOREIGN KEY (connection_id) REFERENCES connections(id) ON DELETE CASCADE,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_connections_created_at
            ON connections (created_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_connection_employees_employee
            ON connection_employees (employee_id)
        """)

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
        try:
            cursor.execute("ALTER TABLE connection_photos ADD COLUMN photo_category TEXT NOT NULL DEFAULT 'other'")
        except sqlite3.OperationalError:
            pass

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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_snr_boxes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                box_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_onu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                device_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_media_converters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                device_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            )
        """)

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

    # ==================== ДОСТУП К БОТУ ====================

    def get_allowed_users(self) -> List[Dict]:
        """Список пользователей с доступом к боту"""
        return self.access_repo.get_all()

    def add_allowed_user(self, user_id: int, title: Optional[str] = None,
                         created_by: Optional[int] = None) -> bool:
        """Выдать доступ пользователю"""
        return self.access_repo.add(user_id, title, created_by)

    def remove_allowed_user(self, user_id: int) -> bool:
        """Отозвать доступ у пользователя"""
        return self.access_repo.remove(user_id)

    # ==================== АДМИНИСТРАТОРЫ ====================

    def get_bot_admins(self) -> List[Dict]:
        """Получить список администраторов, добавленных через бота"""
        return self.admin_repo.get_all()

    def add_bot_admin(self, user_id: int, title: Optional[str] = None,
                      created_by: Optional[int] = None) -> bool:
        """Добавить администратора"""
        return self.admin_repo.add(user_id, title, created_by)

    def remove_bot_admin(self, user_id: int) -> bool:
        """Удалить администратора"""
        return self.admin_repo.remove(user_id)

    # ==================== МАТЕРИАЛЫ (делегирование MaterialRepository) ====================
    
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
    
    # ==================== SNR ОПТИЧЕСКИЕ БОКСЫ ====================
    
    def add_snr_box_to_employee(self, employee_id: int, box_name: str, quantity: int,
                                created_by: Optional[int] = None) -> bool:
        return self.snr_repo.add_box(employee_id, box_name, quantity, created_by)
    
    def deduct_snr_box_from_employee(self, employee_id: int, box_name: str, quantity: int = 1,
                                     connection_id: Optional[int] = None,
                                     created_by: Optional[int] = None) -> bool:
        return self.snr_repo.deduct_box(employee_id, box_name, quantity, connection_id, created_by)
    
    def get_employee_snr_boxes(self, employee_id: int) -> List[Dict]:
        return self.snr_repo.get_boxes(employee_id)
    
    def get_snr_box_quantity(self, employee_id: int, box_name: str) -> int:
        return self.snr_repo.get_quantity(employee_id, box_name)
    
    def get_all_snr_box_names(self) -> List[str]:
        return self.snr_repo.get_all_names()

    # ==================== ONU ====================
    def add_onu_to_employee(self, employee_id: int, device_name: str, quantity: int,
                            created_by: Optional[int] = None) -> bool:
        return self.onu_repo.add_onu(employee_id, device_name, quantity, created_by)

    def deduct_onu_from_employee(self, employee_id: int, device_name: str, quantity: int = 1,
                                 connection_id: Optional[int] = None,
                                 created_by: Optional[int] = None) -> bool:
        return self.onu_repo.deduct_onu(employee_id, device_name, quantity, connection_id, created_by)

    def get_employee_onu(self, employee_id: int) -> List[Dict]:
        return self.onu_repo.get_onu(employee_id)

    def get_onu_quantity(self, employee_id: int, device_name: str) -> int:
        return self.onu_repo.get_quantity(employee_id, device_name)

    def get_all_onu_names(self) -> List[str]:
        return self.onu_repo.get_all_names()

    # ==================== Медиаконверторы ====================
    def add_media_converter_to_employee(self, employee_id: int, device_name: str, quantity: int,
                                        created_by: Optional[int] = None) -> bool:
        return self.media_repo.add_converter(employee_id, device_name, quantity, created_by)

    def deduct_media_converter_from_employee(self, employee_id: int, device_name: str, quantity: int = 1,
                                             connection_id: Optional[int] = None,
                                             created_by: Optional[int] = None) -> bool:
        return self.media_repo.deduct_converter(employee_id, device_name, quantity, connection_id, created_by)

    def get_employee_media_converters(self, employee_id: int) -> List[Dict]:
        return self.media_repo.get_converters(employee_id)

    def get_media_converter_quantity(self, employee_id: int, device_name: str) -> int:
        return self.media_repo.get_quantity(employee_id, device_name)

    def get_all_media_converter_names(self) -> List[str]:
        return self.media_repo.get_all_names()
    
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
        snr_box_model: str,
        port: str,
        fiber_meters: float,
        twisted_pair_meters: float,
        employee_ids: List[int],
        photo_file_ids: List[str],
        created_by: int,
        material_payer_id: Optional[int] = None,
        router_quantity: int = 1,
        contract_signed: bool = False,
        router_access: bool = False,
        telegram_bot_connected: bool = False,
        router_payer_id: Optional[int] = None,
        snr_box_payer_id: Optional[int] = None,
        onu_model: str = '-',
        onu_quantity: int = 0,
        onu_payer_id: Optional[int] = None,
        media_converter_model: str = '-',
        media_converter_quantity: int = 0,
        media_payer_id: Optional[int] = None,
    ) -> Optional[int]:
        """Создать новое подключение и списать материалы с указанного сотрудника
        
        Args:
            material_payer_id: ID сотрудника, с которого списывать материалы.
            Если None, материалы списываются поровну со всех.
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO connections 
                (connection_type, address, router_model, snr_box_model, port, fiber_meters, twisted_pair_meters, created_by, router_quantity, contract_signed, router_access, telegram_bot_connected)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                connection_type, address, router_model, snr_box_model, port,
                fiber_meters, twisted_pair_meters, created_by,
                router_quantity, 1 if contract_signed else 0,
                1 if router_access else 0, 1 if telegram_bot_connected else 0
            ))
            
            connection_id = cursor.lastrowid
            
            for emp_id in employee_ids:
                cursor.execute("""
                    INSERT INTO connection_employees (connection_id, employee_id)
                    VALUES (?, ?)
                """, (connection_id, emp_id))
            
            if material_payer_id:
                success = self.materials_repo.deduct_material(
                    material_payer_id,
                    fiber_meters,
                    twisted_pair_meters,
                    connection_id,
                    created_by,
                    connection=conn
                )
                if not success:
                    raise RuntimeError(
                        f"Не удалось списать материалы с сотрудника ID {material_payer_id}"
                    )
            else:
                emp_count = len(employee_ids)
                fiber_per_emp = fiber_meters / emp_count if emp_count > 0 else 0
                twisted_per_emp = twisted_pair_meters / emp_count if emp_count > 0 else 0
                
                for emp_id in employee_ids:
                    success = self.materials_repo.deduct_material(
                        emp_id,
                        fiber_per_emp,
                        twisted_per_emp,
                        connection_id,
                        created_by,
                        connection=conn
                    )
                    if not success:
                        raise RuntimeError(
                            f"Не удалось списать материалы с сотрудника ID {emp_id}"
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
                    1,
                    connection_id,
                    created_by,
                    connection=conn,
                ):
                    raise RuntimeError(
                        f"Не удалось списать SNR бокс '{snr_box_model}' с сотрудника ID {snr_box_payer_id}"
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
            
            for idx, photo_id in enumerate(photo_file_ids):
                cursor.execute("""
                    INSERT INTO connection_photos (connection_id, photo_file_id, photo_category, photo_order)
                    VALUES (?, ?, ?, ?)
                """, (connection_id, photo_id, 'general', idx))
            
            conn.commit()
            logger.info(f"Создано подключение ID: {connection_id}, материалы списаны")
            return connection_id
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Ошибка при создании подключения: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
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
        return self.connections_repo.get_employee_report(
            employee_id=employee_id,
            days=days,
            start_date=start_date,
            end_date=end_date,
        )

    def get_global_report(
        self,
        days: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[List[Dict], Dict]:
        """Получить общий отчет по всем сотрудникам за период"""
        return self.connections_repo.get_global_report(days=days, start_date=start_date, end_date=end_date)
    
    def get_all_connections_count(self) -> int:
        """Получить общее количество подключений"""
        return self.connections_repo.get_all_count()
