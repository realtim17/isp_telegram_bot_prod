"""
Репозиторий для учета медиаконверторов у сотрудников.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Optional

from database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class MediaConverterRepository(BaseRepository):
    """Работа с таблицей employee_media_converters."""

    def add_converter(
        self,
        employee_id: int,
        device_name: str,
        quantity: int,
        created_by: Optional[int] = None,
        comment: str = ""
    ) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, quantity
                FROM employee_media_converters
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
                    """
                    INSERT INTO employee_media_converters (employee_id, device_name, quantity)
                    VALUES (?, ?, ?)
                    """,
                    (employee_id, device_name, quantity),
                )
            conn.commit()
            conn.close()

            from database.repositories.material_repository import MaterialRepository

            MaterialRepository(self.db_path).log_movement(
                employee_id,
                "add",
                "media_converter",
                device_name,
                quantity,
                new_quantity,
                None,
                created_by,
            )
            return True
        except Exception as exc:
            logger.error("Ошибка при добавлении медиаконвертора: %s", exc)
            return False

    def deduct_converter(
        self,
        employee_id: int,
        device_name: str,
        quantity: int = 1,
        connection_id: Optional[int] = None,
        created_by: Optional[int] = None,
        comment: str = ""
    ) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, quantity
                FROM employee_media_converters
                WHERE employee_id = ? AND device_name = ?
                """,
                (employee_id, device_name),
            )
            existing = cursor.fetchone()
            if not existing or existing["quantity"] < quantity:
                conn.close()
                logger.warning("Недостаточно медиаконверторов '%s' у сотрудника %s", device_name, employee_id)
                return False

            new_quantity = existing["quantity"] - quantity
            if new_quantity == 0:
                cursor.execute("DELETE FROM employee_media_converters WHERE id = ?", (existing["id"],))
            else:
                cursor.execute(
                    "UPDATE employee_media_converters SET quantity = ? WHERE id = ?",
                    (new_quantity, existing["id"]),
                )
            conn.commit()
            conn.close()

            from database.repositories.material_repository import MaterialRepository

            MaterialRepository(self.db_path).log_movement(
                employee_id,
                "deduct",
                "media_converter",
                device_name,
                quantity,
                new_quantity,
                connection_id,
                created_by,
            )
            return True
        except Exception as exc:
            logger.error("Ошибка при списании медиаконвертора: %s", exc)
            return False

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
            SELECT quantity
            FROM employee_media_converters
            WHERE employee_id = ? AND device_name = ?
            """,
            (employee_id, device_name),
            fetch_one=True,
        )
        return result["quantity"] if result else 0

    def get_all_names(self) -> List[str]:
        rows = self.execute_query(
            """
            SELECT DISTINCT device_name
            FROM employee_media_converters
            WHERE quantity > 0
            ORDER BY device_name
            """,
            fetch_all=True,
        ) or []
        return [row["device_name"] for row in rows]
