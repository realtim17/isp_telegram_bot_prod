"""
Менеджер управления доступом к боту
"""
from __future__ import annotations

from threading import RLock
from typing import Iterable, List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AccessManager:
    """Инкапсулирует список разрешенных пользователей"""

    def __init__(self, db, base_ids: Optional[Iterable[int]] = None) -> None:
        self.db = db
        self.base_ids = set(base_ids or [])
        self._lock = RLock()
        self._db_entries: List[Dict] = []
        self._db_ids = set()
        self.refresh()

    def refresh(self) -> None:
        """Перечитать записи из БД"""
        entries = self.db.get_allowed_users()
        with self._lock:
            self._db_entries = entries or []
            self._db_ids = {entry["user_id"] for entry in self._db_entries}
        logger.info("Обновлен список доступа: %s записей", len(self._db_ids))

    def is_allowed(self, user_id: int) -> bool:
        """Проверить наличие доступа"""
        with self._lock:
            return user_id in self.base_ids or user_id in self._db_ids

    def list_entries(self) -> List[Dict]:
        """Получить список всех записей (системных и пользовательских)"""
        entries: List[Dict] = []
        with self._lock:
            base_ids = sorted(self.base_ids)
            db_entries = list(self._db_entries)
        for user_id in base_ids:
            entries.append({
                "user_id": user_id,
                "title": "Системный доступ (.env)",
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

    def add_user(self, user_id: int, title: Optional[str], created_by: Optional[int]) -> (bool, Optional[str]):
        """Добавить нового пользователя в whitelist"""
        with self._lock:
            if user_id in self.base_ids or user_id in self._db_ids:
                return False, "Этот ID уже имеет доступ."
        success = self.db.add_allowed_user(user_id, title, created_by)
        if success:
            self.refresh()
            return True, None
        return False, "Не удалось сохранить ID. Проверьте логи."

    def remove_user(self, user_id: int) -> (bool, Optional[str]):
        """Удалить пользователя из whitelist"""
        with self._lock:
            if user_id in self.base_ids:
                return False, "Этот ID прописан в .env и не может быть удален."
            if user_id not in self._db_ids:
                return False, "ID не найден в списке."
        success = self.db.remove_allowed_user(user_id)
        if success:
            self.refresh()
            return True, None
        return False, "Не удалось удалить ID. Проверьте логи."
