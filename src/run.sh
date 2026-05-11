#!/bin/bash

echo "🎬 STUDIO - AI Video Pipeline"
echo "=============================="
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите Python 3.8+"
    exit 1
fi

echo "✅ Python найден: $(python3 --version)"
echo ""

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создаю виртуальное окружение..."
    python3 -m venv venv
fi

# Активация
source venv/bin/activate

# Установка зависимостей
if [ ! -f "venv/.installed" ]; then
    echo "📥 Установка зависимостей..."
    pip install -r requirements.txt
    touch venv/.installed
else
    echo "✅ Зависимости уже установлены"
fi

echo ""
echo "🚀 Запуск сервера..."
echo "   Откройте: http://127.0.0.1:8000"
echo "   Остановка: Ctrl+C"
echo ""

python main.py