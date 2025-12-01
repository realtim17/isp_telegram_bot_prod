# handlers/employees/onu.py — учет ONU у сотрудников

- Назначение: ConversationHandler для выдачи/списания ONU сотрудникам через inline-кнопки.
- Поток: `_show_onu_employee_list` → `select_employee_for_onu` сохраняет `selected_employee_id` и показывает остаток; `select_onu_action` ветвится на add/deduct (возврат к списку через `onu_back_to_list`).
- Ввод: `enter_onu_name` (кнопки или ручной ввод, ≥2 символов), `enter_onu_quantity` (валидация целого >0), данные складываются в `context.user_data`.
- Подтверждение: `confirm_onu_operation` строит summary, по confirm вызывает `db.add_onu_to_employee` или `db.deduct_onu_from_employee` через `run_in_thread`, затем очищает `context.user_data` и завершает диалог.
- UI: inline-клавиатуры, отмена `manage_cancel`, возврат назад, HTML-разметка сообщений.
- Данные/зависимости: состояния из `config` (`SELECT_EMPLOYEE_FOR_ONU`, `ENTER_ONU_NAME` и т.д.), работа с БД через методы `get_employee_onu`, `get_employee_by_id`, `get_onu_quantity`.
- Замечания: отрицательные остатки контролируются на уровне репозитория/БД (здесь нет явной проверки); нет логирования операций; при списании используется текущий список ONU (возможны гонки при параллельных изменениях).
