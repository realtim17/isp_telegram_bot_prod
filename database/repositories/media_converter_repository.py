"""
Репозиторий для управления медиаконверторами сотрудников
"""
from __future__ import annotations

import logging
import sqlite3
from typing import List, Dict, Optional

from database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class MediaConverterRepository(BaseRepository):
    """Работа с таблицей employee_media_converters"""

    def add_converter(self, employee_id: int, device_name: str, quantity: int,
                      created_by: Optional[int] = None, connection: Optional[sqlite3.Connection] = None) -> bool:
        conn = connection or self.get_connection()
        own_connection = connection is None
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, quantity FROM employee_media_converters
                WHERE employee_id = ? AND device_name = ?
                """,
                (employee_id, device_name),
            )
            existing = cursor.fetchone()

            if existing:
                new_quantity = existing["quantity"] + quantity
                cursor.execute(
                    "UPDATE employee_media_converters SET quantity = ? WHERE id = ?",
                    (new_quantity, existing["id"]),
                )
            else:
                new_quantity = quantity
                cursor.execute(
                    "INSERT INTO employee_media_converters (employee_id, device_name, quantity) VALUES (?, ?, ?)",
                    (employee_id, device_name, quantity),
                )

            from database.repositories.material_repository import MaterialRepository
            material_repo = MaterialRepository(self.db_path)
            if not material_repo.log_movement(
                employee_id,
                "add",
                "media_converter",
                device_name,
                quantity,
                new_quantity,
                None,
                created_by,
                cursor=cursor,
            ):
                raise RuntimeError("Не удалось записать лог движения медиаконверторов")

            if own_connection:
                conn.commit()
            return True
        except Exception as exc:
            if own_connection:
                conn.rollback()
            logger.error("Ошибка при добавлении медиаконверторов: %s", exc)
            return False
        finally:
            if own_connection:
                conn.close()

    def deduct_converter(
        self,
        employee_id: int,
        device_name: str,
        quantity: int = 1,
        connection_id: Optional[int] = None,
        created_by: Optional[int] = None,
        connection: Optional[sqlite3.Connection] = None,
    ) -> bool:
        conn = connection or self.get_connection()
        own_connection = connection is None
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, quantity FROM employee_media_converters
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
                cursor.execute("DELETE FROM employee_media_converters WHERE id = ?", (existing["id"],))
            else:
                cursor.execute(
                    "UPDATE employee_media_converters SET quantity = ? WHERE id = ?",
                    (new_quantity, existing["id"]),
                )

            from database.repositories.material_repository import MaterialRepository
            material_repo = MaterialRepository(self.db_path)
            if not material_repo.log_movement(
                employee_id,
                "deduct",
                "media_converter",
                device_name,
                quantity,
                new_quantity,
                connection_id,
                created_by,
                cursor=cursor,
            ):
                raise RuntimeError("Не удалось записать лог движения медиаконверторов")

            if own_connection:
                conn.commit()
            return True
        except Exception as exc:
            if own_connection:
                conn.rollback()
            logger.error("Ошибка при списании медиаконверторов: %s", exc)
            return False
        finally:
            if own_connection:
                conn.close()

    def get_converters(self, employee_id: int) -> List[Dict]:
        return (
            self.execute_query(
                """
                SELECT id, device_name, quantity, created_at
                FROM employee_media_converters
                WHERE employee_id = ?
                ORDER BY device_name
                """,
                (employee_id,),
                fetch_all=True,
            )
            or []
        )

    def get_quantity(self, employee_id: int, device_name: str) -> int:
        result = self.execute_query(
            """
            SELECT quantity FROM employee_media_converters
            WHERE employee_id = ? AND device_name = ?
            """,
            (employee_id, device_name),
            fetch_one=True,
        )
        return result["quantity"] if result else 0

    def get_all_names(self) -> List[str]:
        results = self.execute_query(
            """
            SELECT DISTINCT device_name
            FROM employee_media_converters
            WHERE quantity > 0
            ORDER BY device_name
            """,
            fetch_all=True,
        ) or []
        return [row["device_name"] for row in results]
