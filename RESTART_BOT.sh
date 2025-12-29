#!/bin/bash
# Скрипт для перезапуска бота после обновления

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║              🔄 ПЕРЕЗАПУСК БОТА                            ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Переход в директорию скрипта
cd "$(dirname "$0")"

# Остановка всех процессов бота
BOT_PIDS=$(pgrep -f "python.*bot.py")
if [ ! -z "$BOT_PIDS" ]; then
    echo "⏹️  Остановка всех процессов бота..."
    echo "$BOT_PIDS" | xargs kill
    sleep 2
    # Проверка, что все процессы остановлены
    REMAINING=$(pgrep -f "python.*bot.py")
    if [ ! -z "$REMAINING" ]; then
        echo "⚠️  Принудительная остановка процессов..."
        echo "$REMAINING" | xargs kill -9
        sleep 1
    fi
    echo "✅ Все процессы бота остановлены"
else
    echo "ℹ️  Бот не запущен"
fi

echo ""
echo "🚀 Запуск обновленного бота..."
echo ""

# Активация виртуального окружения и запуск бота
source venv/bin/activate
nohup python bot.py > bot.log 2>&1 &
NEW_PID=$!

sleep 2

if ps -p $NEW_PID > /dev/null; then
    echo "✅ Бот успешно запущен (PID: $NEW_PID)"
    echo ""
    echo "📋 Логи в реальном времени:"
    echo "   tail -f bot.log"
    echo ""
    echo "🛑 Остановить бота:"
    echo "   kill $NEW_PID"
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║     ✨ БОТ ОБНОВЛЕН И РАБОТАЕТ! ✨                         ║"
    echo "║                                                            ║"
    echo "║     Теперь после создания отчета бот отправляет:           ║"
    echo "║     • Все фотографии альбомом                              ║"
    echo "║     • Красиво отформатированный отчет                      ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
else
    echo "❌ Ошибка запуска бота"
    echo "Проверьте логи: cat bot.log"
fi
