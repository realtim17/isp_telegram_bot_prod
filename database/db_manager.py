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
        cursor = conn.cursor()
        
        # Таблица сотрудников
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL UNIQUE,
                fiber_balance REAL DEFAULT 0,
                twisted_pair_balance REAL DEFAULT 0,
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
        
        # Таблица подключений
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_type TEXT NOT NULL DEFAULT 'mkd',
                address TEXT NOT NULL,
                router_model TEXT NOT NULL,
                port TEXT NOT NULL,
                fiber_meters REAL NOT NULL,
                twisted_pair_meters REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER NOT NULL
            )
        """)
        
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
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_material_movement_employee_created
            ON material_movement_log (employee_id, created_at)
        """)
        
        conn.commit()
        conn.close()
        logger.info("Таблицы БД созданы успешно")
    
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
        material_payer_id: Optional[int] = None,
        router_quantity: int = 1,
        contract_signed: bool = False,
        router_access: bool = False,
        telegram_bot_connected: bool = False
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
                (connection_type, address, router_model, port, fiber_meters, twisted_pair_meters, created_by, router_quantity, contract_signed, router_access, telegram_bot_connected)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                connection_type, address, router_model, port,
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
                COUNT(DISTINCT ce_all.employee_id) as employee_count
            FROM connections c
            JOIN connection_employees ce_target 
                ON ce_target.connection_id = c.id AND ce_target.employee_id = ?
            JOIN connection_employees ce_all 
                ON ce_all.connection_id = c.id
            WHERE 1=1
            {date_condition}
            GROUP BY c.id
            ORDER BY c.created_at DESC
        """
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        connection_ids = [row['id'] for row in rows]
        employees_map: Dict[int, List[str]] = {}
        
        if connection_ids:
            placeholders = ",".join("?" for _ in connection_ids)
            cursor.execute(f"""
                SELECT ce.connection_id, e.full_name
                FROM connection_employees ce
                JOIN employees e ON e.id = ce.employee_id
                WHERE ce.connection_id IN ({placeholders})
                ORDER BY ce.connection_id, e.full_name
            """, connection_ids)
            
            for emp_row in cursor.fetchall():
                employees_map.setdefault(emp_row['connection_id'], []).append(emp_row['full_name'])
        
        connections = []
        total_fiber = 0.0
        total_twisted = 0.0
        
        for row in rows:
            conn_dict = dict(row)
            emp_count = max(conn_dict['employee_count'], 1)
            
            conn_dict['employee_fiber_meters'] = round(conn_dict['fiber_meters'] / emp_count, 2)
            conn_dict['employee_twisted_pair_meters'] = round(conn_dict['twisted_pair_meters'] / emp_count, 2)
            conn_dict['all_employees'] = employees_map.get(conn_dict['id'], [])
            
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
