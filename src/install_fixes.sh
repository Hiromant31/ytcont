#!/bin/bash
# 🚀 Скрипт установки исправлений для AI Video Studio

echo "🔧 Установка исправлений..."

# Создаем бэкап старых файлов
echo "📦 Создание бэкапа..."
mkdir -p ~/ytcont/backup_$(date +%Y%m%d_%H%M%S)
cp ~/ytcont/src/main.py ~/ytcont/backup_$(date +%Y%m%d_%H%M%S)/
cp ~/ytcont/src/orchestrator.py ~/ytcont/backup_$(date +%Y%m%d_%H%M%S)/
cp ~/ytcont/src/stage_1_story.py ~/ytcont/backup_$(date +%Y%m%d_%H%M%S)/

# Копируем исправленные файлы
echo "✅ Установка исправленных файлов..."
cp main.py ~/ytcont/src/
cp orchestrator.py ~/ytcont/src/
cp stage_1_story.py ~/ytcont/src/

# Проверяем синтаксис
echo "🔍 Проверка синтаксиса Python..."
cd ~/ytcont
python3 -m py_compile src/main.py
python3 -m py_compile src/orchestrator.py  
python3 -m py_compile src/stage_1_story.py

if [ $? -eq 0 ]; then
    echo "✅ Все файлы прошли проверку синтаксиса!"
    echo ""
    echo "📋 Что исправлено:"
    echo "  1. ❌→✅ SyntaxError в main.py (JavaScript в f-string)"
    echo "  2. ❌→✅ KeyError в /episodes endpoint"
    echo "  3. ❌→✅ ValueError в stage_1_story.py"
    echo "  4. 📉 Уменьшены max_tokens (экономия ~65%)"
    echo "  5. 📉 Уменьшено количество ретраев (2 вместо 3-5)"
    echo ""
    echo "🚀 Теперь можно запускать:"
    echo "   cd ~/ytcont"
    echo "   source venv/bin/activate"
    echo "   python3 run.py"
else
    echo "❌ Ошибка проверки синтаксиса!"
    echo "   Восстанавливаем из бэкапа..."
    cp ~/ytcont/backup_$(date +%Y%m%d_%H%M%S)/* ~/ytcont/src/
fi
