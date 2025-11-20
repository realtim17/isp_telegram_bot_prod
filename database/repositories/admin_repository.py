"""
Репозиторий управления администраторами бота
"""
from __future__ import annotations

import logging
from typing import List, Dict, Optional

from database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class AdminRepository(BaseRepository):
    """Работа с таблицей bot_admins"""

    def get_all(self) -> List[Dict]:
        """Получить список администраторов, добавленных через бота"""
        return self.execute_query(
            """
            SELECT user_id, title, created_at, created_by
            FROM bot_admins
            ORDER BY created_at DESC
            """,
            fetch_all=True,
        ) or []

    def add(self, user_id: int, title: Optional[str] = None, created_by: Optional[int] = None) -> bool:
        """Добавить администратора"""
        query = """
            INSERT INTO bot_admins (user_id, title, created_by)
            VALUES (?, ?, ?)
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (user_id, title, created_by))
            conn.commit()
            return True
        except Exception as exc:
            if conn:
                conn.rollback()
            logger.error("Ошибка при добавлении администратора: %s", exc)
            return False
        finally:
            if conn:
                conn.close()

    def remove(self, user_id: int) -> bool:
        """Удалить администратора"""
        query = "DELETE FROM bot_admins WHERE user_id = ?"
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            if conn:
                conn.rollback()
            logger.error("Ошибка при удалении администратора: %s", exc)
            return False
        finally:
            if conn:
                conn.close()
