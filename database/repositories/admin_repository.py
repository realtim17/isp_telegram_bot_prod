"""
Репозиторий для хранения администраторов бота.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Optional

from database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class AdminRepository(BaseRepository):
    """Список администраторов бота."""

    def get_all(self) -> List[Dict]:
        return (
            self.execute_query(
                """
                SELECT user_id, title, created_at, created_by
                FROM bot_admins
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
                INSERT OR REPLACE INTO bot_admins (user_id, title, created_by)
                VALUES (?, ?, ?)
                """,
                (user_id, title or "", created_by),
            )
            logger.info("Добавлен администратор %s", user_id)
            return True
        except Exception as exc:
            logger.error("Ошибка при добавлении администратора: %s", exc)
            return False

    def remove(self, user_id: int) -> bool:
        try:
            self.execute_query(
                "DELETE FROM bot_admins WHERE user_id = ?",
                (user_id,),
            )
            logger.info("Удален администратор %s", user_id)
            return True
        except Exception as exc:
            logger.error("Ошибка при удалении администратора: %s", exc)
            return False
