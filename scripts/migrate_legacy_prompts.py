#!/usr/bin/env python3
"""
Migration Script: Legacy Prompts to SQLite Template System

Читает старые txt промпты и создаёт дефолтный шаблон в SQLite БД.
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from template_manager import (
    init_db,
    create_template,
    reset_default_template
)


def load_file(path: Path) -> str:
    """Загрузить файл как текст."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"⚠️  Не удалось загрузить {path}: {e}")
        return ""


def migrate():
    """Выполнить миграцию."""
    print("=" * 60)
    print("🔄 Migrating Legacy Prompts to SQLite Template System")
    print("=" * 60)
    
    # 1. Инициализировать БД
    print("\n1️⃣  Инициализация БД...")
    init_db()
    print("   ✅ БД готова: data/ytcont.db")
    
    # 2. Загрузить старые промпты
    print("\n2️⃣  Загрузка legacy промптов...")
    
    legacy_path = Path("prompts/legacy")
    prompts = {}
    
    # Пытаемся загрузить из legacy папки
    writer_path = legacy_path / "writer_instruction.txt"
    extractor_path = legacy_path / "extractor_instruction.txt"
    stage2_path = legacy_path / "stage_2_scenes.txt"
    
    # Если legacy папки нет, пробуем старые пути
    if not legacy_path.exists():
        legacy_path = Path("prompts")
    
    prompts["stage_1_writer"] = load_file(writer_path)
    prompts["stage_1_extractor"] = load_file(extractor_path)
    prompts["stage_2_scenes"] = load_file(stage2_path)
    
    # Проверяем что хоть что-то загрузилось
    if not any(prompts.values()):
        print("   ❌ Ошибка: Не найдены legacy промпты!")
        print("   Требуется создать дефолтный шаблон вручную.")
        return False
    
    print("   ✅ Загружено промптов:")
    for key, value in prompts.items():
        if value:
            print(f"      • {key}: {len(value)} симв.")
    
    # 3. Сформировать settings_json (визуальный стиль)
    print("\n3️⃣  Создание дефолтных settings...")
    settings = {
        "visual_style": "Gritty graphic novel style, bold ink outlines, "
                       "high contrast noir lighting, dark moody atmosphere, "
                       "urban dystopian setting",
        "camera_motion": "slow_zoom",
        "voice_style": "dramatic"
    }
    settings_json = json.dumps(settings, ensure_ascii=False)
    
    # 4. Создать шаблон
    print("\n4️⃣  Создание шаблона...")
    
    # Создаём ID из текущей даты
    template_id = f"migrated_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Определяем категорию по содержимому
    category = "Развлекательное"
    if "криминал" in prompts["stage_1_writer"].lower() or "crime" in prompts["stage_1_writer"].lower():
        category = "Криминал"
    elif "sci-fi" in prompts["stage_1_writer"].lower() or "sci fi" in prompts["stage_1_writer"].lower():
        category = "Sci-Fi"
    elif "документал" in prompts["stage_1_writer"].lower():
        category = "Документальное"
    
    template_name = "Дефолтный (Мигрированный)"
    
    # Создаём шаблон
    success = create_template(
        template_id=template_id,
        name=template_name,
        description="Дефолтный шаблон мигрирован из legacy txt файлов",
        category=category,
        prompts_json=json.dumps(prompts, ensure_ascii=False),
        settings_json=settings_json,
        is_default=True
    )
    
    if success:
        print(f"   ✅ Шаблон создан: {template_id}")
        print(f"      Название: {template_name}")
        print(f"      Категория: {category}")
    else:
        print("   ❌ Ошибка создания шаблона!")
        return False
    
    # 5. Сбросить дефолт у других шаблонов
    print("\n5️⃣  Сброс дефолтных шаблонов...")
    reset_default_template()
    print("   ✅ Готово")
    
    # 6. Вывести статистику
    print("\n6️⃣  Миграция завершена!")
    print("\n📊 Статистика:")
    print(f"   • БД: data/ytcont.db")
    print(f"   • Шаблонов: 1")
    print(f"   • Legacy файлы: prompts/legacy/")
    print("\n💡 Далее:")
    print("   1. Запустить: python -m src.main")
    print("   2. Открыть в браузере: http://localhost:8000")
    print("   3. Перейти в раздел '🎭 Prompt Templates'")
    print("\n" + "=" * 60)
    
    return True


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
