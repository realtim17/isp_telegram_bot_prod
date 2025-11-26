"""
Репозиторий для работы с роутерами сотрудников
"""
from typing import List, Dict, Optional
import logging
import sqlite3

from database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class RouterRepository(BaseRepository):
    """Репозиторий для управления роутерами сотрудников"""
    
    def add_router(
        self,
        employee_id: int,
        router_name: str,
        quantity: int,
        created_by: Optional[int] = None,
        connection: Optional[sqlite3.Connection] = None,
    ) -> bool:
        """Добавить роутеры сотруднику"""
        own_connection = connection is None
        conn = connection or self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Проверяем, есть ли уже такой роутер у сотрудника
            cursor.execute("""
                SELECT id, quantity FROM employee_routers 
                WHERE employee_id = ? AND router_name = ?
            """, (employee_id, router_name))
            existing = cursor.fetchone()
            
            if existing:
                # Обновляем количество
                new_quantity = existing[1] + quantity
                cursor.execute("""
                    UPDATE employee_routers 
                    SET quantity = ? 
                    WHERE id = ?
                """, (new_quantity, existing[0]))
                logger.info(
                    "Обновлено количество роутеров '%s' у сотрудника ID %s: +%s (всего: %s)",
                    router_name, employee_id, quantity, new_quantity
                )
            else:
                # Добавляем новую запись
                new_quantity = quantity
                cursor.execute("""
                    INSERT INTO employee_routers (employee_id, router_name, quantity)
                    VALUES (?, ?, ?)
                """, (employee_id, router_name, quantity))
                logger.info("Добавлены роутеры '%s' сотруднику ID %s: %s шт.", router_name, employee_id, quantity)
            
            # Логируем операцию в рамках той же транзакции
            from database.repositories.material_repository import MaterialRepository
            material_repo = MaterialRepository(self.db_path)
            if not material_repo.log_movement(
                employee_id, 'add', 'router', router_name,
                quantity, new_quantity, None, created_by,
                cursor=cursor
            ):
                raise RuntimeError("Не удалось записать лог движения роутеров")
            
            if own_connection:
                conn.commit()
            return True
        except Exception as e:
            if own_connection:
                conn.rollback()
            logger.error("Ошибка при добавлении роутеров: %s", e)
            return False
        finally:
            if own_connection:
                conn.close()
    
    def deduct_router(
        self,
        employee_id: int,
        router_name: str,
        quantity: int = 1,
        connection_id: Optional[int] = None,
        created_by: Optional[int] = None,
        connection: Optional[sqlite3.Connection] = None,
    ) -> bool:
        """Списать роутер у сотрудника"""
        own_connection = connection is None
        conn = connection or self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Проверяем текущее количество
            cursor.execute("""
                SELECT id, quantity FROM employee_routers 
                WHERE employee_id = ? AND router_name = ?
            """, (employee_id, router_name))
            existing = cursor.fetchone()
            
            if not existing:
                logger.warning("Роутер '%s' не найден у сотрудника ID %s", router_name, employee_id)
                return False
            
            current_quantity = existing[1]
            if current_quantity < quantity:
                logger.warning("Недостаточно роутеров '%s' у сотрудника ID %s", router_name, employee_id)
                return False
            
            new_quantity = current_quantity - quantity
            
            if new_quantity == 0:
                # Удаляем запись
                cursor.execute("DELETE FROM employee_routers WHERE id = ?", (existing[0],))
                logger.info("Списаны все роутеры '%s' у сотрудника ID %s", router_name, employee_id)
            else:
                # Обновляем количество
                cursor.execute("""
                    UPDATE employee_routers 
                    SET quantity = ? 
                    WHERE id = ?
                """, (new_quantity, existing[0]))
                logger.info(
                    "Списан роутер '%s' у сотрудника ID %s: -%s (осталось: %s)",
                    router_name, employee_id, quantity, new_quantity
                )
            
            # Логируем операцию в той же транзакции
            from database.repositories.material_repository import MaterialRepository
            material_repo = MaterialRepository(self.db_path)
            if not material_repo.log_movement(
                employee_id, 'deduct', 'router', router_name,
                quantity, new_quantity, connection_id, created_by,
                cursor=cursor
            ):
                raise RuntimeError("Не удалось записать лог движения роутеров")
            
            if own_connection:
                conn.commit()
            return True
        except Exception as e:
            if own_connection:
                conn.rollback()
            logger.error("Ошибка при списании роутера: %s", e)
            return False
        finally:
            if own_connection:
                conn.close()
    
    def get_routers(self, employee_id: int) -> List[Dict]:
        """Получить список роутеров сотрудника"""
        try:
            return self.execute_query("""
                SELECT id, router_name, quantity, created_at
                FROM employee_routers 
                WHERE employee_id = ?
                ORDER BY router_name
            """, (employee_id,), fetch_all=True) or []
        except Exception as e:
            logger.error(f"Ошибка при получении роутеров сотрудника: {e}")
            return []
    
    def get_quantity(self, employee_id: int, router_name: str) -> int:
        """Получить количество конкретного роутера у сотрудника"""
        try:
            result = self.execute_query("""
                SELECT quantity FROM employee_routers 
                WHERE employee_id = ? AND router_name = ?
            """, (employee_id, router_name), fetch_one=True)
            
            return result['quantity'] if result else 0
        except Exception as e:
            logger.error(f"Ошибка при получении количества роутеров: {e}")
            return 0
    
    def get_all_names(self) -> List[str]:
        """Получить список всех уникальных названий роутеров, которые есть в наличии"""
        try:
            results = self.execute_query("""
                SELECT DISTINCT router_name 
                FROM employee_routers 
                WHERE quantity > 0
                ORDER BY router_name
            """, fetch_all=True) or []
            
            return [row['router_name'] for row in results]
        except Exception as e:
            logger.error(f"Ошибка при получении списка роутеров: {e}")
            return []
