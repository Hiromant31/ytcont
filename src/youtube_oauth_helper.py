import os
import json
import sys
from pathlib import Path


def check_youtube_setup() -> dict:
    """
    Проверка настройки YouTube API.
    
    Returns:
        Словарь с результатами проверки
    """
    results = {
        "oauth_json_exists": False,
        "oauth_json_path": "",
        "token_exists": False,
        "required_packages": [],
        "is_configured": False,
        "errors": []
    }
    
    # Проверяем существующие настройки в settings.json
    settings_path = "settings.json"
    youtube_config = {}
    if os.path.exists(settings_path):
        with open(settings_path, 'r', encoding='utf-8') as f:
            try:
                settings = json.load(f)
                youtube_config = settings.get("youtube", {})
            except json.JSONDecodeError:
                results["errors"].append("Ошибка чтения settings.json")
    
    # Проверяем путь к OAuth JSON из настроек
    oauth_json_path = youtube_config.get("oauth_client_json", "")
    if oauth_json_path and os.path.exists(oauth_json_path):
        results["oauth_json_exists"] = True
        results["oauth_json_path"] = oauth_json_path
    else:
        # Проверяем стандартные пути
        possible_paths = [
            "client_secret.json",
            "client_secrets.json", 
            "oauth_client.json",
            "youtube_client.json"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                results["oauth_json_exists"] = True
                results["oauth_json_path"] = path
                break
    
    # Проверяем существование токена
    token_paths = ["token.pickle", "youtube_token.pickle", "oauth_token.pickle"]
    for path in token_paths:
        if os.path.exists(path):
            results["token_exists"] = True
            break
    
    # Проверяем установленные пакеты
    required_packages = [
        "google-auth-oauthlib",
        "google-auth-httplib2", 
        "google-api-python-client",
        "google-auth"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    results["required_packages"] = missing_packages
    
    # Общая оценка готовности
    results["is_configured"] = (
        results["oauth_json_exists"] and 
        results["token_exists"] and
        len(results["required_packages"]) == 0
    )
    
    return results


def generate_oauth_instructions() -> str:
    """Генерация инструкций для настройки YouTube API."""
    instructions = """
# 📺 НАСТРОЙКА YOUTUBE API ДЛЯ ЗАГРУЗКИ ВИДЕО

## Шаг 1: Создание проекта в Google Cloud Console
1. Перейдите на https://console.cloud.google.com
2. Создайте новый проект или выберите существующий
3. Название проекта: "YTCont Video Uploader"

## Шаг 2: Включение YouTube Data API v3
1. В меню слева выберите "APIs & Services" → "Library"
2. Найдите "YouTube Data API v3"
3. Нажмите "Enable"

## Шаг 3: Создание OAuth 2.0 Credentials
1. Перейдите в "APIs & Services" → "Credentials"
2. Нажмите "Create Credentials" → "OAuth 2.0 Client IDs"
3. Тип приложения: "Desktop App"
4. Название: "YTCont Desktop Client"
5. Нажмите "Create"

## Шаг 4: Скачивание client_secret.json
1. После создания credentials, скачайте JSON файл
2. Переименуйте файл в `client_secret.json`
3. Поместите файл в корень проекта (рядом с main.py)

## Шаг 5: Первая авторизация
При первом запуске YouTube Upload:
1. Откроется браузер для авторизации
2. Войдите в свой Google аккаунт
3. Разрешите доступ к YouTube каналу
4. Токен будет сохранен в `token.pickle`

## Проверка:
- Файл `client_secret.json` в корне проекта
- Установлены зависимости: `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`
- Канал YouTube должен быть подтвержден (необходим для загрузки)

## Важно:
- Не коммитьте `client_secret.json` и `token.pickle` в Git
- Добавьте эти файлы в `.gitignore`
- OAuth токен действует до отзыва или истечения срока
"""
    return instructions


def save_youtube_config(oauth_json_path: str, schedule_time: str = "", 
                       auto_upload: bool = False) -> bool:
    """
    Сохранение конфигурации YouTube в settings.json.
    
    Args:
        oauth_json_path: Путь к OAuth JSON файлу
        schedule_time: Время публикации по умолчанию
        auto_upload: Автоматическая загрузка после рендеринга
        
    Returns:
        Успех операции
    """
    settings_path = "settings.json"
    
    # Читаем текущие настройки
    settings = {}
    if os.path.exists(settings_path):
        with open(settings_path, 'r', encoding='utf-8') as f:
            try:
                settings = json.load(f)
            except json.JSONDecodeError:
                pass
    
    # Создаем или обновляем раздел youtube
    youtube_config = settings.get("youtube", {})
    youtube_config.update({
        "enabled": True,
        "oauth_client_json": oauth_json_path,
        "schedule_time": schedule_time,
        "auto_upload": auto_upload,
        "generate_tags": True,
        "default_privacy": "private",
        "notify_subscribers": True
    })
    
    settings["youtube"] = youtube_config
    
    # Сохраняем
    try:
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        print(f"✅ Конфигурация YouTube сохранена в {settings_path}")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения настроек: {e}")
        return False


def get_youtube_credentials() -> dict:
    """
    Получение конфигурации YouTube из настроек.
    
    Returns:
        Словарь с конфигурацией или пустой если не настроено
    """
    settings_path = "settings.json"
    
    if not os.path.exists(settings_path):
        return {}
    
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        youtube_config = settings.get("youtube", {})
        
        # Проверяем что конфигурация полная
        if youtube_config.get("enabled", False) and youtube_config.get("oauth_client_json"):
            return youtube_config
        else:
            return {}
            
    except json.JSONDecodeError:
        return {}


def validate_oauth_json(file_path: str) -> tuple[bool, str]:
    """
    Валидация OAuth JSON файла.
    
    Args:
        file_path: Путь к JSON файлу
        
    Returns:
        Кортеж (успех, сообщение)
    """
    if not os.path.exists(file_path):
        return False, f"Файл не найден: {file_path}"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Проверяем структуру Google OAuth JSON
        if "installed" not in data and "web" not in data:
            return False, "Некорректный формат OAuth JSON. Ожидается 'installed' или 'web' секция."
        
        # Проверяем обязательные поля для desktop app
        if "installed" in data:
            installed = data["installed"]
            required_fields = ["client_id", "client_secret", "redirect_uris"]
            for field in required_fields:
                if field not in installed:
                    return False, f"Отсутствует обязательное поле: {field}"
        
        return True, "Файл OAuth JSON валиден"
        
    except json.JSONDecodeError:
        return False, "Невалидный JSON формат"
    except Exception as e:
        return False, f"Ошибка валидации: {e}"


if __name__ == "__main__":
    # Тестирование
    print("🔍 Проверка настройки YouTube API...")
    results = check_youtube_setup()
    
    print(json.dumps(results, ensure_ascii=False, indent=2))
    
    if not results["is_configured"]:
        print("\n⚠️  Настройка YouTube не завершена:")
        
        if not results["oauth_json_exists"]:
            print("   ❌ Отсутствует OAuth JSON файл")
            print("   ℹ️  Скачайте client_secret.json из Google Cloud Console")
        
        if results["required_packages"]:
            print("   ❌ Отсутствуют пакеты:")
            for pkg in results["required_packages"]:
                print(f"      - {pkg}")
            print("   ℹ️  Установите: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        
        if not results["token_exists"]:
            print("   ℹ️  Токен не найден - потребуется авторизация при первом запуске")
        
        print("\n📋 Инструкции по настройке:")
        print(generate_oauth_instructions())