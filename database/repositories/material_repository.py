"""
Репозиторий для работы с материалами сотрудников
"""
from typing import List, Dict, Optional
from datetime import datetime
import logging

from database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class MaterialRepository(BaseRepository):
    """Репозиторий для управления материалами (ВОЛС и витая пара)"""

    @staticmethod
    def _resolve_twisted_values(
        twisted_pair_meters: float = 0,
        twisted_pair_external_meters: float = 0,
        twisted_pair_internal_meters: float = 0,
    ) -> tuple[float, float]:
        """Привести данные витой пары к внешней/внутренней компонентам."""
        ext = float(twisted_pair_external_meters or 0)
        intr = float(twisted_pair_internal_meters or 0)
        total = float(twisted_pair_meters or 0)
        if ext == 0 and intr == 0 and total != 0:
            ext = round(total / 2, 2)
            intr = round(total - ext, 2)
        return ext, intr
    
    def add_material(
        self, 
        employee_id: int, 
        fiber_meters: float = 0, 
        twisted_pair_meters: float = 0,
<<<<<<< Updated upstream
        created_by: Optional[int] = None
    ) -> bool:
        """Добавить материалы на баланс сотрудника"""
=======
        twisted_pair_external_meters: float = 0,
        twisted_pair_internal_meters: float = 0,
        created_by: Optional[int] = None,
        comment: str = "",
        connection: Optional[sqlite3.Connection] = None
    ) -> bool:
        """Добавить материалы на баланс сотрудника"""
        own_connection = connection is None
        conn = connection or self.get_connection()
        cursor = conn.cursor()
        twisted_external, twisted_internal = self._resolve_twisted_values(
            twisted_pair_meters,
            twisted_pair_external_meters,
            twisted_pair_internal_meters,
        )
        twisted_total = twisted_external + twisted_internal
        
>>>>>>> Stashed changes
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE employees 
                SET fiber_balance = fiber_balance + ?,
                    twisted_pair_balance = twisted_pair_balance + ?,
                    twisted_pair_external_balance = twisted_pair_external_balance + ?,
                    twisted_pair_internal_balance = twisted_pair_internal_balance + ?
                WHERE id = ?
            """, (fiber_meters, twisted_total, twisted_external, twisted_internal, employee_id))
            
            updated = cursor.rowcount > 0
            
<<<<<<< Updated upstream
            if updated:
                # Получаем новый баланс
                cursor.execute("""
                    SELECT fiber_balance, twisted_pair_balance 
                    FROM employees WHERE id = ?
                """, (employee_id,))
                row = cursor.fetchone()
                new_fiber = row[0] if row else 0
                new_twisted = row[1] if row else 0
                
                conn.commit()
=======
            cursor.execute("""
                SELECT fiber_balance, twisted_pair_balance,
                       twisted_pair_external_balance, twisted_pair_internal_balance
                FROM employees WHERE id = ?
            """, (employee_id,))
            row = cursor.fetchone()
            new_fiber = row['fiber_balance'] if row else 0
            new_twisted_external = row['twisted_pair_external_balance'] if row else 0
            new_twisted_internal = row['twisted_pair_internal_balance'] if row else 0
            
            if fiber_meters > 0:
                if not self.log_movement(
                    employee_id, 'add', 'fiber', 'ВОЛС',
                    fiber_meters, new_fiber, None, created_by,
                    comment=comment,
                    cursor=cursor
                ):
                    raise RuntimeError("Не удалось записать движение по ВОЛС")
            if twisted_external > 0:
                if not self.log_movement(
                    employee_id, 'add', 'twisted_pair_external', 'Внешняя витая пара',
                    twisted_external, new_twisted_external, None, created_by,
                    comment=comment,
                    cursor=cursor
                ):
                    raise RuntimeError("Не удалось записать движение по внешней витой паре")
            if twisted_internal > 0:
                if not self.log_movement(
                    employee_id, 'add', 'twisted_pair_internal', 'Внутренняя витая пара',
                    twisted_internal, new_twisted_internal, None, created_by,
                    comment=comment,
                    cursor=cursor
                ):
                    raise RuntimeError("Не удалось записать движение по внутренней витой паре")
            
            if own_connection:
                conn.commit()
            
            logger.info(
                "Добавлено материалов сотруднику ID %s: ВОЛС +%sм, Внешняя ВП +%sм, Внутренняя ВП +%sм",
                employee_id, fiber_meters, twisted_external, twisted_internal
            )
            return True
        except Exception as exc:
            if own_connection:
                conn.rollback()
            logger.error(f"Ошибка при добавлении материалов: {exc}")
            return False
        finally:
            if own_connection:
>>>>>>> Stashed changes
                conn.close()
                
                # Логируем операции
                if fiber_meters > 0:
                    self.log_movement(employee_id, 'add', 'fiber', 'ВОЛС', 
                                    fiber_meters, new_fiber, None, created_by)
                if twisted_pair_meters > 0:
                    self.log_movement(employee_id, 'add', 'twisted_pair', 'Витая пара',
                                    twisted_pair_meters, new_twisted, None, created_by)
                
                logger.info(f"Добавлено материалов сотруднику ID {employee_id}: "
                          f"ВОЛС +{fiber_meters}м, Витая пара +{twisted_pair_meters}м")
            else:
                conn.close()
            
            return updated
        except Exception as e:
            logger.error(f"Ошибка при добавлении материалов: {e}")
            return False
    
    def deduct_material(
        self,
        employee_id: int,
        fiber_meters: float = 0,
        twisted_pair_meters: float = 0,
        twisted_pair_external_meters: float = 0,
        twisted_pair_internal_meters: float = 0,
        connection_id: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> bool:
        """Списать материалы с баланса сотрудника"""
<<<<<<< Updated upstream
=======
        own_connection = connection is None
        conn = connection or self.get_connection()
        cursor = conn.cursor()
        twisted_external, twisted_internal = self._resolve_twisted_values(
            twisted_pair_meters,
            twisted_pair_external_meters,
            twisted_pair_internal_meters,
        )
        twisted_total = twisted_external + twisted_internal
        
>>>>>>> Stashed changes
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Проверяем текущий баланс
            cursor.execute("""
                SELECT fiber_balance, twisted_pair_balance,
                       twisted_pair_external_balance, twisted_pair_internal_balance
                FROM employees 
                WHERE id = ?
            """, (employee_id,))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"Сотрудник ID {employee_id} не найден")
                conn.close()
                return False
            
<<<<<<< Updated upstream
            current_fiber = row[0] or 0
            current_twisted = row[1] or 0
=======
            current_fiber = row['fiber_balance'] or 0
            current_twisted = row['twisted_pair_balance'] or 0
            current_twisted_external = row['twisted_pair_external_balance'] or 0
            current_twisted_internal = row['twisted_pair_internal_balance'] or 0
>>>>>>> Stashed changes
            
            # Проверяем достаточность средств
            if current_fiber < fiber_meters:
                logger.warning(f"Недостаточно ВОЛС у сотрудника ID {employee_id}")
                conn.close()
                return False
            
<<<<<<< Updated upstream
            if current_twisted < twisted_pair_meters:
                logger.warning(f"Недостаточно витой пары у сотрудника ID {employee_id}")
                conn.close()
=======
            if current_twisted < twisted_total:
                logger.warning("Недостаточно витой пары (общий баланс) у сотрудника ID %s", employee_id)
                return False

            if current_twisted_external < twisted_external:
                logger.warning("Недостаточно внешней витой пары у сотрудника ID %s", employee_id)
                return False

            if current_twisted_internal < twisted_internal:
                logger.warning("Недостаточно внутренней витой пары у сотрудника ID %s", employee_id)
>>>>>>> Stashed changes
                return False
            
            # Списываем материалы
            cursor.execute("""
                UPDATE employees 
                SET fiber_balance = fiber_balance - ?,
                    twisted_pair_balance = twisted_pair_balance - ?,
                    twisted_pair_external_balance = twisted_pair_external_balance - ?,
                    twisted_pair_internal_balance = twisted_pair_internal_balance - ?
                WHERE id = ?
            """, (fiber_meters, twisted_total, twisted_external, twisted_internal, employee_id))
            
            updated = cursor.rowcount > 0
            
<<<<<<< Updated upstream
            if updated:
                new_fiber = current_fiber - fiber_meters
                new_twisted = current_twisted - twisted_pair_meters
                
                conn.commit()
=======
            new_fiber = current_fiber - fiber_meters
            new_twisted_external = current_twisted_external - twisted_external
            new_twisted_internal = current_twisted_internal - twisted_internal
            
            if fiber_meters > 0:
                if not self.log_movement(
                    employee_id, 'deduct', 'fiber', 'ВОЛС',
                    fiber_meters, new_fiber, connection_id, created_by,
                    comment=comment,
                    cursor=cursor
                ):
                    raise RuntimeError("Не удалось зафиксировать списание ВОЛС")
            if twisted_external > 0:
                if not self.log_movement(
                    employee_id, 'deduct', 'twisted_pair_external', 'Внешняя витая пара',
                    twisted_external, new_twisted_external, connection_id, created_by,
                    comment=comment,
                    cursor=cursor
                ):
                    raise RuntimeError("Не удалось зафиксировать списание внешней витой пары")
            if twisted_internal > 0:
                if not self.log_movement(
                    employee_id, 'deduct', 'twisted_pair_internal', 'Внутренняя витая пара',
                    twisted_internal, new_twisted_internal, connection_id, created_by,
                    comment=comment,
                    cursor=cursor
                ):
                    raise RuntimeError("Не удалось зафиксировать списание внутренней витой пары")
            
            if own_connection:
                conn.commit()
            
            logger.info(
                "Списано материалов у сотрудника ID %s: ВОЛС -%sм, Внешняя ВП -%sм, Внутренняя ВП -%sм",
                employee_id, fiber_meters, twisted_external, twisted_internal
            )
            return True
        except Exception as exc:
            if own_connection:
                conn.rollback()
            logger.error(f"Ошибка при списании материалов: {exc}")
            return False
        finally:
            if own_connection:
>>>>>>> Stashed changes
                conn.close()
                
                # Логируем операции
                if fiber_meters > 0:
                    self.log_movement(employee_id, 'deduct', 'fiber', 'ВОЛС',
                                    fiber_meters, new_fiber, connection_id, created_by)
                if twisted_pair_meters > 0:
                    self.log_movement(employee_id, 'deduct', 'twisted_pair', 'Витая пара',
                                    twisted_pair_meters, new_twisted, connection_id, created_by)
                
                logger.info(f"Списано материалов у сотрудника ID {employee_id}: "
                          f"ВОЛС -{fiber_meters}м, Витая пара -{twisted_pair_meters}м")
            else:
                conn.close()
            
            return updated
        except Exception as e:
            logger.error(f"Ошибка при списании материалов: {e}")
            return False
    
    def log_movement(
        self,
        employee_id: int,
        operation_type: str,
        item_type: str,
        item_name: str,
        quantity: float,
        balance_after: float,
        connection_id: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> bool:
        """Записать движение материала в лог"""
        try:
            self.execute_query("""
                INSERT INTO material_movement_log 
                (employee_id, operation_type, item_type, item_name, quantity, 
                 balance_after, connection_id, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (employee_id, operation_type, item_type, item_name, quantity,
                  balance_after, connection_id, created_by))
            
            logger.info(f"Logged movement: {operation_type} {quantity} {item_type} for employee {employee_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при логировании движения: {e}")
            return False
    
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
        except Exception as e:
            logger.error(f"Ошибка при получении движений: {e}")
            return []

