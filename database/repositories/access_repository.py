"""
Репозиторий управления доступом к боту
"""
from __future__ import annotations

from typing import List, Dict, Optional
import logging

from database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class AccessRepository(BaseRepository):
    """Работа с таблицей bot_access"""

    def get_all(self) -> List[Dict]:
        """Возвращает список пользователей с доступом"""
        return self.execute_query(
            """
            SELECT user_id, title, created_at, created_by
            FROM bot_access
            ORDER BY created_at DESC
            """,
            fetch_all=True,
        ) or []

    def add(self, user_id: int, title: Optional[str] = None, created_by: Optional[int] = None) -> bool:
        """Добавить пользователя в whitelist"""
        query = """
            INSERT INTO bot_access (user_id, title, created_by)
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
            logger.error("Ошибка при добавлении доступа: %s", exc)
            return False
        finally:
            if conn:
                conn.close()

    def remove(self, user_id: int) -> bool:
        """Удалить пользователя из whitelist"""
        query = "DELETE FROM bot_access WHERE user_id = ?"
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
            logger.error("Ошибка при удалении доступа: %s", exc)
            return False
        finally:
            if conn:
                conn.close()
