#!/bin/bash
# Скрипт для перезапуска бота после обновления

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║              🔄 ПЕРЕЗАПУСК БОТА                            ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Поиск процесса бота
BOT_PID=$(pgrep -f "python.*bot.py")

<<<<<<< Updated upstream
if [ ! -z "$BOT_PID" ]; then
    echo "⏹️  Остановка бота (PID: $BOT_PID)..."
    kill $BOT_PID
=======
VENV_DIR=".venv311"

# Остановка всех процессов бота
BOT_PIDS=$(pgrep -f "python.*bot.py")
if [ ! -z "$BOT_PIDS" ]; then
    echo "⏹️  Остановка всех процессов бота..."
    echo "$BOT_PIDS" | xargs kill
>>>>>>> Stashed changes
    sleep 2
    echo "✅ Бот остановлен"
else
    echo "ℹ️  Бот не запущен"
fi

echo ""
echo "🚀 Запуск обновленного бота..."
echo ""

<<<<<<< Updated upstream
# Запуск бота в фоне
nohup python3 bot.py > bot.log 2>&1 &
=======
# Активация виртуального окружения и запуск бота
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "❌ Виртуальное окружение $VENV_DIR не найдено"
    echo "   Запустите ./run.sh для первичной инициализации"
    exit 1
fi

source "$VENV_DIR/bin/activate"
nohup python bot.py > bot.log 2>&1 &
>>>>>>> Stashed changes
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
