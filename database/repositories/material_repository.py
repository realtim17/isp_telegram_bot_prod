"""
Репозиторий для работы с материалами сотрудников
"""
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
import logging

from database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class MaterialRepository(BaseRepository):
    """Репозиторий для управления материалами (ВОЛС и витая пара)"""
    
    def add_material(
        self,
        employee_id: int,
        fiber_meters: float = 0,
        twisted_pair_meters: float = 0,
        created_by: Optional[int] = None,
        connection: Optional[sqlite3.Connection] = None
    ) -> bool:
        """Добавить материалы на баланс сотрудника"""
        own_connection = connection is None
        conn = connection or self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE employees 
                SET fiber_balance = fiber_balance + ?,
                    twisted_pair_balance = twisted_pair_balance + ?
                WHERE id = ?
            """, (fiber_meters, twisted_pair_meters, employee_id))
            
            if cursor.rowcount == 0:
                return False
            
            cursor.execute("""
                SELECT fiber_balance, twisted_pair_balance 
                FROM employees WHERE id = ?
            """, (employee_id,))
            row = cursor.fetchone()
            new_fiber = row['fiber_balance'] if row else 0
            new_twisted = row['twisted_pair_balance'] if row else 0
            
            if fiber_meters > 0:
                if not self.log_movement(
                    employee_id, 'add', 'fiber', 'ВОЛС',
                    fiber_meters, new_fiber, None, created_by,
                    cursor=cursor
                ):
                    raise RuntimeError("Не удалось записать движение по ВОЛС")
            if twisted_pair_meters > 0:
                if not self.log_movement(
                    employee_id, 'add', 'twisted_pair', 'Витая пара',
                    twisted_pair_meters, new_twisted, None, created_by,
                    cursor=cursor
                ):
                    raise RuntimeError("Не удалось записать движение по витой паре")
            
            if own_connection:
                conn.commit()
            
            logger.info(
                "Добавлено материалов сотруднику ID %s: ВОЛС +%sм, Витая пара +%sм",
                employee_id, fiber_meters, twisted_pair_meters
            )
            return True
        except Exception as exc:
            if own_connection:
                conn.rollback()
            logger.error(f"Ошибка при добавлении материалов: {exc}")
            return False
        finally:
            if own_connection:
                conn.close()
    
    def deduct_material(
        self,
        employee_id: int,
        fiber_meters: float = 0,
        twisted_pair_meters: float = 0,
        connection_id: Optional[int] = None,
        created_by: Optional[int] = None,
        connection: Optional[sqlite3.Connection] = None
    ) -> bool:
        """Списать материалы с баланса сотрудника"""
        own_connection = connection is None
        conn = connection or self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT fiber_balance, twisted_pair_balance 
                FROM employees 
                WHERE id = ?
            """, (employee_id,))
            row = cursor.fetchone()
            
            if not row:
                logger.warning("Сотрудник ID %s не найден", employee_id)
                return False
            
            current_fiber = row['fiber_balance'] or 0
            current_twisted = row['twisted_pair_balance'] or 0
            
            if current_fiber < fiber_meters:
                logger.warning("Недостаточно ВОЛС у сотрудника ID %s", employee_id)
                return False
            
            if current_twisted < twisted_pair_meters:
                logger.warning("Недостаточно витой пары у сотрудника ID %s", employee_id)
                return False
            
            cursor.execute("""
                UPDATE employees 
                SET fiber_balance = fiber_balance - ?,
                    twisted_pair_balance = twisted_pair_balance - ?
                WHERE id = ?
            """, (fiber_meters, twisted_pair_meters, employee_id))
            
            if cursor.rowcount == 0:
                return False
            
            new_fiber = current_fiber - fiber_meters
            new_twisted = current_twisted - twisted_pair_meters
            
            if fiber_meters > 0:
                if not self.log_movement(
                    employee_id, 'deduct', 'fiber', 'ВОЛС',
                    fiber_meters, new_fiber, connection_id, created_by,
                    cursor=cursor
                ):
                    raise RuntimeError("Не удалось зафиксировать списание ВОЛС")
            if twisted_pair_meters > 0:
                if not self.log_movement(
                    employee_id, 'deduct', 'twisted_pair', 'Витая пара',
                    twisted_pair_meters, new_twisted, connection_id, created_by,
                    cursor=cursor
                ):
                    raise RuntimeError("Не удалось зафиксировать списание витой пары")
            
            if own_connection:
                conn.commit()
            
            logger.info(
                "Списано материалов у сотрудника ID %s: ВОЛС -%sм, Витая пара -%sм",
                employee_id, fiber_meters, twisted_pair_meters
            )
            return True
        except Exception as exc:
            if own_connection:
                conn.rollback()
            logger.error(f"Ошибка при списании материалов: {exc}")
            return False
        finally:
            if own_connection:
                conn.close()
    
    def log_movement(
        self,
        employee_id: int,
        operation_type: str,
        item_type: str,
        item_name: str,
        quantity: float,
        balance_after: float,
        connection_id: Optional[int] = None,
        created_by: Optional[int] = None,
        cursor: Optional[sqlite3.Cursor] = None
    ) -> bool:
        """Записать движение материала в лог"""
        own_connection = cursor is None
        conn = None
        
        try:
            if cursor is None:
                conn = self.get_connection()
                cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO material_movement_log 
                (employee_id, operation_type, item_type, item_name, quantity, 
                 balance_after, connection_id, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                employee_id, operation_type, item_type, item_name,
                quantity, balance_after, connection_id, created_by
            ))
            
            if own_connection and conn:
                conn.commit()
            
            logger.info(
                "Logged movement: %s %s %s for employee %s",
                operation_type, quantity, item_type, employee_id
            )
            return True
        except Exception as exc:
            if own_connection and conn:
                conn.rollback()
            logger.error(f"Ошибка при логировании движения: {exc}")
            return False
        finally:
            if own_connection and conn:
                conn.close()
    
    def get_movements(
        self,
        employee_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Получить все движения материалов сотрудника за период"""
        try:
            return self.execute_query("""
                SELECT 
                    operation_type,
                    item_type,
                    item_name,
                    quantity,
                    balance_after,
                    connection_id,
                    created_at
                FROM material_movement_log
                WHERE employee_id = ? 
                  AND created_at >= ? 
                  AND created_at <= ?
                ORDER BY created_at
            """, (employee_id, start_date, end_date), fetch_all=True) or []
        except Exception as exc:
            logger.error(f"Ошибка при получении движений: {exc}")
            return []
