"""
Репозиторий для управления абонентскими терминалами (ONU) сотрудников
"""
from __future__ import annotations

import logging
import sqlite3
from typing import List, Dict, Optional

from database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ONURepository(BaseRepository):
    """Работа с таблицей employee_onu"""

    def add_onu(self, employee_id: int, device_name: str, quantity: int,
                created_by: Optional[int] = None, connection: Optional[sqlite3.Connection] = None) -> bool:
        """Добавить ONU сотруднику"""
        own_connection = connection is None
        conn = connection or self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, quantity FROM employee_onu
                WHERE employee_id = ? AND device_name = ?
                """,
                (employee_id, device_name),
            )
            existing = cursor.fetchone()

            if existing:
                new_quantity = existing["quantity"] + quantity
                cursor.execute(
                    "UPDATE employee_onu SET quantity = ? WHERE id = ?",
                    (new_quantity, existing["id"]),
                )
            else:
                new_quantity = quantity
                cursor.execute(
                    "INSERT INTO employee_onu (employee_id, device_name, quantity) VALUES (?, ?, ?)",
                    (employee_id, device_name, quantity),
                )

            from database.repositories.material_repository import MaterialRepository
            material_repo = MaterialRepository(self.db_path)
            if not material_repo.log_movement(
                employee_id,
                "add",
                "onu",
                device_name,
                quantity,
                new_quantity,
                None,
                created_by,
                cursor=cursor,
            ):
                raise RuntimeError("Не удалось записать лог движения ONU")

            if own_connection:
                conn.commit()
            return True
        except Exception as exc:
            if own_connection:
                conn.rollback()
            logger.error("Ошибка при добавлении ONU: %s", exc)
            return False
        finally:
            if own_connection:
                conn.close()

    def deduct_onu(
        self,
        employee_id: int,
        device_name: str,
        quantity: int = 1,
        connection_id: Optional[int] = None,
        created_by: Optional[int] = None,
        connection: Optional[sqlite3.Connection] = None,
    ) -> bool:
        """Списать ONU у сотрудника"""
        own_connection = connection is None
        conn = connection or self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, quantity FROM employee_onu
                WHERE employee_id = ? AND device_name = ?
                """,
                (employee_id, device_name),
            )
            existing = cursor.fetchone()
            if not existing or existing["quantity"] < quantity:
                conn.close()
                return False

            new_quantity = existing["quantity"] - quantity
            if new_quantity == 0:
                cursor.execute("DELETE FROM employee_onu WHERE id = ?", (existing["id"],))
            else:
                cursor.execute(
                    "UPDATE employee_onu SET quantity = ? WHERE id = ?",
                    (new_quantity, existing["id"]),
                )

            from database.repositories.material_repository import MaterialRepository
            material_repo = MaterialRepository(self.db_path)
            if not material_repo.log_movement(
                employee_id,
                "deduct",
                "onu",
                device_name,
                quantity,
                new_quantity,
                connection_id,
                created_by,
                cursor=cursor,
            ):
                raise RuntimeError("Не удалось записать лог движения ONU")

            if own_connection:
                conn.commit()
            return True
        except Exception as exc:
            if own_connection:
                conn.rollback()
            logger.error("Ошибка при списании ONU: %s", exc)
            return False
        finally:
            if own_connection:
                conn.close()

    def get_onu(self, employee_id: int) -> List[Dict]:
        """Получить ONU сотрудника"""
        return (
            self.execute_query(
                """
                SELECT id, device_name, quantity, created_at
                FROM employee_onu
                WHERE employee_id = ?
                ORDER BY device_name
                """,
                (employee_id,),
                fetch_all=True,
            )
            or []
        )

    def get_quantity(self, employee_id: int, device_name: str) -> int:
        """Количество ONU конкретной модели"""
        result = self.execute_query(
            """
            SELECT quantity FROM employee_onu
            WHERE employee_id = ? AND device_name = ?
            """,
            (employee_id, device_name),
            fetch_one=True,
        )
        return result["quantity"] if result else 0

    def get_all_names(self) -> List[str]:
        """Список всех моделей ONU с остатком"""
        results = self.execute_query(
            """
            SELECT DISTINCT device_name FROM employee_onu
            WHERE quantity > 0
            ORDER BY device_name
            """,
            fetch_all=True,
        ) or []
        return [row["device_name"] for row in results]
