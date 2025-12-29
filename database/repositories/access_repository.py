"""
Репозиторий для работы с таблицей bot_access.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Optional

from database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class AccessRepository(BaseRepository):
    """Список пользователей с доступом к боту."""

    def get_all(self) -> List[Dict]:
        return (
            self.execute_query(
                """
                SELECT user_id, title, created_at, created_by
                FROM bot_access
                ORDER BY created_at DESC
                """,
                fetch_all=True,
            )
            or []
        )

    def add(self, user_id: int, title: Optional[str] = None, created_by: Optional[int] = None) -> bool:
        try:
            self.execute_query(
                """
                INSERT OR REPLACE INTO bot_access (user_id, title, created_by)
                VALUES (?, ?, ?)
                """,
                (user_id, title or "", created_by),
            )
            logger.info("Добавлен доступ пользователю %s", user_id)
            return True
        except Exception as exc:
            logger.error("Ошибка при добавлении доступа: %s", exc)
            return False

    def remove(self, user_id: int) -> bool:
        try:
            self.execute_query(
                "DELETE FROM bot_access WHERE user_id = ?",
                (user_id,),
            )
            logger.info("Удален доступ пользователю %s", user_id)
            return True
        except Exception as exc:
            logger.error("Ошибка при удалении доступа: %s", exc)
            return False
