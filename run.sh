#!/bin/bash

# Скрипт запуска бота для интернет-провайдера

echo "🚀 Запуск бота..."

# Переход в директорию со скриптом
cd "$(dirname "$0")"

VENV_DIR=".venv311"
PYTHON_BIN="python3.11"

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "❌ Ошибка: файл .env не найден"
    echo "📝 Создайте файл .env на основе .env.example"
    exit 1
fi

# Проверка версии существующего окружения
if [ -x "$VENV_DIR/bin/python" ]; then
    if ! "$VENV_DIR/bin/python" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)'; then
        echo "❌ $VENV_DIR создан не на Python 3.11"
        echo "   Удалите $VENV_DIR и запустите скрипт снова"
        exit 1
    fi
fi

# Проверка наличия виртуального окружения
if [ ! -d "$VENV_DIR" ]; then
    echo "⚠️  Виртуальное окружение не найдено"
    echo "📦 Создание виртуального окружения..."

    if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
        echo "❌ Не найден $PYTHON_BIN"
        echo "   Установите Python 3.11 и повторите запуск"
        exit 1
    fi

    "$PYTHON_BIN" -m venv "$VENV_DIR"
    
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка при создании виртуального окружения"
        exit 1
    fi
fi

# Активация виртуального окружения
echo "🔧 Активация виртуального окружения..."
source "$VENV_DIR/bin/activate"

# Проверка и установка зависимостей
echo "📦 Проверка зависимостей..."
pip install -q -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Ошибка при установке зависимостей"
    exit 1
fi

# Проверка, не запущен ли уже бот
if pgrep -f "python.*bot.py" > /dev/null; then
    echo "⚠️  Бот уже запущен"
    echo "🔍 PID: $(pgrep -f 'python.*bot.py')"
    read -p "❓ Перезапустить бота? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "⏹️  Остановка бота..."
        pkill -f "python.*bot.py"
        sleep 2
    else
        echo "❌ Запуск отменен"
        exit 0
    fi
fi

# Запуск бота
echo "✅ Запуск бота..."
nohup python bot.py > bot.log 2>&1 &

# Получение PID
BOT_PID=$!

# Небольшая пауза для проверки запуска
sleep 2

# Проверка, что бот запустился
if ps -p $BOT_PID > /dev/null 2>&1; then
    echo "✅ Бот успешно запущен!"
    echo "🔢 PID: $BOT_PID"
    echo "📋 Логи: tail -f bot.log"
    echo ""
    echo "Для остановки: pkill -f 'python.*bot.py'"
else
    echo "❌ Ошибка запуска бота"
    echo "📋 Проверьте логи: cat bot.log"
    exit 1
fi
