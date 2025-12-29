# Логи и мониторинг

## Основной лог
- Приложение пишет stdout/stderr в `bot.log` (см. `RESTART_BOT.sh`).
- Для ручного просмотра используйте `tail -f bot.log`.

## Ротация logrotate
1. Конфиг расположен в `ops/logrotate.conf`.
2. Параметры:
   - ротация **ежедневно** (`daily`);
   - хранится **7** архивов (`rotate 7`);
   - сжатие `compress`/`delaycompress`;
   - `copytruncate` безопасно обрезает файл без остановки бота;
   - пустые/отсутствующие логи пропускаются.
3. Запуск:
   ```bash
   sudo logrotate -s /var/lib/logrotate/logrotate.isp_bot.state ops/logrotate.conf
   ```
   Добавьте аналогичную команду в cron (например, `/etc/cron.d/isp_bot`) для автоматической ротации.

## Рекомендации по мониторингу
- Настройте уведомления на строки уровня ERROR (tail + grep или интеграция с Telegram/e-mail).
- Добавьте heartbeat (например, периодический `logger.info("heartbeat")`) и скрипт, который проверяет свежесть `bot.log`.
- Если бот работает под systemd (`isp_bot.service`), следите за статусом через `systemctl status isp_bot` и смотрите журнал `journalctl -u isp_bot`.
