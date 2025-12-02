## Refactor summary (2025-12-02)
- Вынес шага загрузки фото в отдельный модуль `handlers/connection/photos.py` и обновил `conversation.py` для импорта.
- Удалил дублирование логики из `steps.py`, оставив ссылку на новый модуль.
- Шаг выбора исполнителей уже реализован в `handlers/connection/employees.py`, а `steps.py` просто вызывает `start_employee_selection`.
- Согласовал текст кнопки «Отмена» (используется одно значение).

## Update (2025-12-02)
- Модуль выбора исполнителей перенесён в `handlers/connection/executors.py` (ранее `handlers/connection/employees.py`).
- Обновлены импорты в `steps.py` и `conversation.py`.
