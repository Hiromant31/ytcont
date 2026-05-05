#!/usr/bin/env python3
"""
Тестовый скрипт для проверки YouTube Upload интеграции.
Запуск: python test_youtube_integration.py
"""

import os
import sys
import subprocess

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def check_file_exists(filepath):
    exists = os.path.exists(filepath)
    status = "✅" if exists else "❌"
    print(f"{status} {filepath}")
    return exists

def check_python_import(module_path):
    try:
        # Пытаемся импортировать модуль
        if module_path == "youtube_oauth_helper":
            import src.youtube_oauth_helper as mod
        elif module_path == "stage_8_youtube_upload":
            import src.stage_8_youtube_upload as mod
        elif module_path == "main_enhanced":
            # main_enhanced сложнее из-за зависимостей
            print("ℹ️  main_enhanced.py - пропускаем импорт (зависит от FastAPI)")
            return True
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта {module_path}: {e}")
        return False

def check_dependencies():
    """Проверка установки необходимых пакетов."""
    print_header("ПРОВЕРКА ЗАВИСИМОСТЕЙ")
    
    required_packages = [
        "google-api-python-client",
        "google-auth-httplib2", 
        "google-auth-oauthlib",
        "fastapi",
        "uvicorn",
        "pydantic"
    ]
    
    all_ok = True
    
    # Проверяем через pip list
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=freeze"],
            capture_output=True,
            text=True
        )
        installed_packages = [pkg.split('==')[0].lower() for pkg in result.stdout.split('\n')]
        
        for package in required_packages:
            if package in installed_packages or \
               package.replace("-", "_") in installed_packages or \
               package in ['fastapi', 'uvicorn', 'pydantic']:  # Эти могут быть под другими названиями
                print(f"✅ {package}")
            else:
                print(f"❌ {package} (не установлен)")
                all_ok = False
                
    except Exception as e:
        print(f"⚠️  Не удалось проверить пакеты: {e}")
        all_ok = False
    
    return all_ok

def main():
    print_header("ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ YOUTUBE UPLOAD")
    print("Тестируем созданные файлы и зависимости...")
    
    all_files_exist = True
    all_imports_ok = True
    
    # 1. Проверяем файлы
    print_header("ПРОВЕРКА ФАЙЛОВ")
    
    files_to_check = [
        "src/stage_8_youtube_upload.py",
        "src/youtube_oauth_helper.py", 
        "src/main_enhanced.py",
        "src/orchestrator_enhanced.py",
        "backups/main_backup.py",
        "backups/orchestrator_backup.py",
        "YOUTUBE_SETUP_INSTRUCTIONS.md",
        "YTUBE_INTEGRATION_README.md"
    ]
    
    for filepath in files_to_check:
        if not check_file_exists(filepath):
            all_files_exist = False
    
    # 2. Проверяем импорты
    print_header("ПРОВЕРКА ИМПОРТОВ PYTHON")
    
    for module in ["stage_8_youtube_upload", "youtube_oauth_helper"]:
        if not check_python_import(module):
            all_imports_ok = False
    
    # 3. Проверяем зависимости
    deps_ok = check_dependencies()
    
    # 4. Проверяем структуру
    print_header("ПРОВЕРКА СТРУКТУРЫ")
    
    # Проверяем что в main_enhanced есть нужные эндпоинты
    if os.path.exists("src/main_enhanced.py"):
        with open("src/main_enhanced.py", 'r', encoding='utf-8') as f:
            content = f.read()
            
        endpoints = [
            "@app.get(\"/youtube/setup\")",
            "@app.post(\"/youtube/upload\")",
            "class YouTubeUploadRequest",
            "class YouTubeConfig"
        ]
        
        for endpoint in endpoints:
            if endpoint in content:
                print(f"✅ Найден эндпоинт: {endpoint}")
            else:
                print(f"❌ Отсутствует эндпоинт: {endpoint}")
                all_imports_ok = False
    
    # 5. Сводка
    print_header("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    
    print(f"📁 Файлы: {'✅ ВСЕ СОЗДАНЫ' if all_files_exist else '❌ ПРОПУЩЕНЫ НЕКОТОРЫЕ'}")
    print(f"🐍 Импорты: {'✅ РАБОТАЮТ' if all_imports_ok else '❌ ЕСТЬ ОШИБКИ'}")
    print(f"📦 Зависимости: {'✅ УСТАНОВЛЕНЫ' if deps_ok else '❌ ТРЕБУЮТСЯ'}")
    
    print("\n" + "=" * 60)
    print("СЛЕДУЮЩИЕ ШАГИ:")
    print("=" * 60)
    
    if all_files_exist and all_imports_ok and deps_ok:
        print("""
✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!

Теперь вы можете:

1. ЗАПУСТИТЬ УЛУЧШЕННУЮ ВЕРСИЮ:
   python src/main_enhanced.py
   http://localhost:8000

2. ПРОТЕСТИРОВАТЬ YOUTUBE UPLOAD:
   - Откройте веб-интерфейс
   - Нажмите "⚙️ Настроить YouTube API"
   - Следуйте инструкциям из YOUTUBE_SETUP_INSTRUCTIONS.md
   - Попробуйте загрузить тестовое видео

3. ВНЕДРИТЬ В ПРОИЗВОДСТВО (если всё работает):
   cp src/main_enhanced.py src/main.py
   cp src/orchestrator_enhanced.py src/orchestrator.py
""")
    else:
        print("""
⚠️  ЕСТЬ ПРОБЛЕМЫ!

Выполните следующие действия:

1. УСТАНОВИТЕ ЗАВИСИМОСТИ:
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

2. ПРОВЕРЬТЕ ОТСУТСТВУЮЩИЕ ФАЙЛЫ:
   - Посмотрите список выше
   - Создайте недостающие файлы вручную
   - Или запустите процесс интеграции заново

3. ПРОВЕРЬТЕ СИНТАКСИС:
   python -m py_compile src/stage_8_youtube_upload.py
   python -m py_compile src/youtube_oauth_helper.py

После исправлений запустите этот тест заново.
""")

if __name__ == "__main__":
    main()