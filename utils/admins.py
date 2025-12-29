"""
Менеджер администраторов бота
"""
from __future__ import annotations

from threading import RLock
from typing import Iterable, List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AdminManager:
    """Объединяет базовый список админов и записи из БД"""

    def __init__(self, db, base_admin_ids: Optional[Iterable[int]] = None) -> None:
        self.db = db
        self.base_ids = set(base_admin_ids or [])
        self._lock = RLock()
        self._db_entries: List[Dict] = []
        self._db_ids = set()
        self.refresh()

    def refresh(self) -> None:
        entries = self.db.get_bot_admins()
        with self._lock:
            self._db_entries = entries or []
            self._db_ids = {entry["user_id"] for entry in self._db_entries}
        logger.info("Обновлен список администраторов: %s пользователей", len(self._db_ids) + len(self.base_ids))

    def is_admin(self, user_id: int) -> bool:
        with self._lock:
            return user_id in self.base_ids or user_id in self._db_ids

    def list_entries(self) -> List[Dict]:
        with self._lock:
            base_ids = sorted(self.base_ids)
            db_entries = list(self._db_entries)
        entries: List[Dict] = []
        for user_id in base_ids:
            entries.append({
                "user_id": user_id,
                "title": "Суперадмин (.env)",
                "created_at": None,
                "created_by": None,
                "source": "env",
                "removable": False,
            })
        for entry in db_entries:
            enriched = dict(entry)
            enriched["source"] = "db"
            enriched["removable"] = True
            entries.append(enriched)
        return entries

    def add_admin(self, user_id: int, title: Optional[str], created_by: Optional[int]) -> (bool, Optional[str]):
        with self._lock:
            if user_id in self.base_ids or user_id in self._db_ids:
                return False, "Этот ID уже является администратором."
        success = self.db.add_bot_admin(user_id, title, created_by)
        if success:
            self.refresh()
            return True, None
        return False, "Не удалось сохранить администратора. Проверьте логи."

    def remove_admin(self, user_id: int) -> (bool, Optional[str]):
        with self._lock:
            if user_id in self.base_ids:
                return False, "Нельзя удалить суперадминистратора из .env."
            if user_id not in self._db_ids:
                return False, "ID не найден среди администраторов."
        success = self.db.remove_bot_admin(user_id)
        if success:
            self.refresh()
            return True, None
        return False, "Не удалось удалить администратора. Проверьте логи."
