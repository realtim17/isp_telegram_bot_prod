"""
Репозиторий для учета SFP модулей у сотрудников.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Optional

from database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class SFPModuleRepository(BaseRepository):
    """Работа с таблицей employee_sfp_modules."""

    def add_module(
        self,
        employee_id: int,
        module_name: str,
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
                FROM employee_sfp_modules
                WHERE employee_id = ? AND module_name = ?
                """,
                (employee_id, module_name),
            )
            existing = cursor.fetchone()
            if existing:
                new_quantity = existing["quantity"] + quantity
                cursor.execute(
                    "UPDATE employee_sfp_modules SET quantity = ? WHERE id = ?",
                    (new_quantity, existing["id"]),
                )
            else:
                new_quantity = quantity
                cursor.execute(
                    """
                    INSERT INTO employee_sfp_modules (employee_id, module_name, quantity)
                    VALUES (?, ?, ?)
                    """,
                    (employee_id, module_name, quantity),
                )
            conn.commit()
            conn.close()

            from database.repositories.material_repository import MaterialRepository

            MaterialRepository(self.db_path).log_movement(
                employee_id,
                "add",
                "sfp_module",
                module_name,
                quantity,
                new_quantity,
                None,
                created_by,
            )
            return True
        except Exception as exc:
            logger.error("Ошибка при добавлении SFP модуля: %s", exc)
            return False

    def deduct_module(
        self,
        employee_id: int,
        module_name: str,
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
                FROM employee_sfp_modules
                WHERE employee_id = ? AND module_name = ?
                """,
                (employee_id, module_name),
            )
            existing = cursor.fetchone()
            if not existing or existing["quantity"] < quantity:
                conn.close()
                logger.warning("Недостаточно SFP модулей '%s' у сотрудника %s", module_name, employee_id)
                return False

            new_quantity = existing["quantity"] - quantity
            if new_quantity == 0:
                cursor.execute("DELETE FROM employee_sfp_modules WHERE id = ?", (existing["id"],))
            else:
                cursor.execute(
                    "UPDATE employee_sfp_modules SET quantity = ? WHERE id = ?",
                    (new_quantity, existing["id"]),
                )
            conn.commit()
            conn.close()

            from database.repositories.material_repository import MaterialRepository

            MaterialRepository(self.db_path).log_movement(
                employee_id,
                "deduct",
                "sfp_module",
                module_name,
                quantity,
                new_quantity,
                connection_id,
                created_by,
            )
            return True
        except Exception as exc:
            logger.error("Ошибка при списании SFP модуля: %s", exc)
            return False

    def get_modules(self, employee_id: int) -> List[Dict]:
        return (
            self.execute_query(
                """
                SELECT id, module_name, quantity, created_at
                FROM employee_sfp_modules
                WHERE employee_id = ?
                ORDER BY module_name
                """,
                (employee_id,),
                fetch_all=True,
            )
            or []
        )

    def get_quantity(self, employee_id: int, module_name: str) -> int:
        result = self.execute_query(
            """
            SELECT quantity
            FROM employee_sfp_modules
            WHERE employee_id = ? AND module_name = ?
            """,
            (employee_id, module_name),
            fetch_one=True,
        )
        return result["quantity"] if result else 0

    def get_all_names(self) -> List[str]:
        rows = self.execute_query(
            """
            SELECT DISTINCT module_name
            FROM employee_sfp_modules
            WHERE quantity > 0
            ORDER BY module_name
            """,
            fetch_all=True,
        ) or []
        return [row["module_name"] for row in rows]
