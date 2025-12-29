"""
Репозиторий для работы с SNR оптическими боксами сотрудников
"""
from __future__ import annotations

import logging
from typing import List, Dict, Optional

from database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class SNRBoxRepository(BaseRepository):
    """Учет оптических боксов на сотрудниках."""

    def add_box(
        self,
        employee_id: int,
        box_name: str,
        quantity: int,
        created_by: Optional[int] = None,
        comment: str = ""
    ) -> bool:
        """Добавить боксы на баланс сотрудника."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, quantity
                FROM employee_snr_boxes
                WHERE employee_id = ? AND box_name = ?
                """,
                (employee_id, box_name),
            )
            existing = cursor.fetchone()

            if existing:
                new_quantity = existing["quantity"] + quantity
                cursor.execute(
                    "UPDATE employee_snr_boxes SET quantity = ? WHERE id = ?",
                    (new_quantity, existing["id"]),
                )
            else:
                new_quantity = quantity
                cursor.execute(
                    """
                    INSERT INTO employee_snr_boxes (employee_id, box_name, quantity)
                    VALUES (?, ?, ?)
                    """,
                    (employee_id, box_name, quantity),
                )

            conn.commit()
            conn.close()

            from database.repositories.material_repository import MaterialRepository

            MaterialRepository(self.db_path).log_movement(
                employee_id,
                "add",
                "snr_box",
                box_name,
                quantity,
                new_quantity,
                None,
                created_by,
            )
            logger.info("Добавлено %s боксов '%s' сотруднику %s", quantity, box_name, employee_id)
            return True
        except Exception as exc:
            logger.error("Ошибка при добавлении SNR бокса: %s", exc)
            return False

    def deduct_box(
        self,
        employee_id: int,
        box_name: str,
        quantity: int = 1,
        connection_id: Optional[int] = None,
        created_by: Optional[int] = None,
        comment: str = ""
    ) -> bool:
        """Списать боксы с сотрудника."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, quantity
                FROM employee_snr_boxes
                WHERE employee_id = ? AND box_name = ?
                """,
                (employee_id, box_name),
            )
            existing = cursor.fetchone()
            if not existing or existing["quantity"] < quantity:
                conn.close()
                logger.warning("Недостаточно боксов '%s' у сотрудника %s", box_name, employee_id)
                return False

            new_quantity = existing["quantity"] - quantity
            if new_quantity == 0:
                cursor.execute("DELETE FROM employee_snr_boxes WHERE id = ?", (existing["id"],))
            else:
                cursor.execute(
                    "UPDATE employee_snr_boxes SET quantity = ? WHERE id = ?",
                    (new_quantity, existing["id"]),
                )

            conn.commit()
            conn.close()

            from database.repositories.material_repository import MaterialRepository

            MaterialRepository(self.db_path).log_movement(
                employee_id,
                "deduct",
                "snr_box",
                box_name,
                quantity,
                new_quantity,
                connection_id,
                created_by,
            )
            logger.info("Списано %s боксов '%s' у сотрудника %s", quantity, box_name, employee_id)
            return True
        except Exception as exc:
            logger.error("Ошибка при списании SNR бокса: %s", exc)
            return False

    def get_boxes(self, employee_id: int) -> List[Dict]:
        """Получить текущие боксы сотрудника."""
        return (
            self.execute_query(
                """
                SELECT id, box_name, quantity, created_at
                FROM employee_snr_boxes
                WHERE employee_id = ?
                ORDER BY box_name
                """,
                (employee_id,),
                fetch_all=True,
            )
            or []
        )

    def get_quantity(self, employee_id: int, box_name: str) -> int:
        """Получить количество конкретного бокса."""
        result = self.execute_query(
            """
            SELECT quantity
            FROM employee_snr_boxes
            WHERE employee_id = ? AND box_name = ?
            """,
            (employee_id, box_name),
            fetch_one=True,
        )
        return result["quantity"] if result else 0

    def get_all_names(self) -> List[str]:
        """Список всех моделей боксов с остатком."""
        rows = self.execute_query(
            """
            SELECT DISTINCT box_name
            FROM employee_snr_boxes
            WHERE quantity > 0
            ORDER BY box_name
            """,
            fetch_all=True,
        ) or []
        return [row["box_name"] for row in rows]
