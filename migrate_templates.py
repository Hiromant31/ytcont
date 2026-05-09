#!/usr/bin/env python3
"""
Миграция данных из старой структуры шаблонов в новую.
Переносит промпты из templates.prompts_json в template_prompts.
"""

import sqlite3
import json

def migrate():
    conn = sqlite3.connect('data/ytcont.db')
    cursor = conn.cursor()
    
    # Находим все шаблоны со старым форматом prompts_json
    cursor.execute("SELECT id, name, prompts_json, settings_json FROM templates WHERE prompts_json IS NOT NULL AND prompts_json != ''")
    templates = cursor.fetchall()
    
    print(f"Найдено {len(templates)} шаблонов для миграции")
    
    for template_id, name, prompts_json, settings_json in templates:
        print(f"\n--- Миграция шаблона: {template_id} ({name}) ---")
        
        try:
            prompts = json.loads(prompts_json)
            
            # Мигрируем каждый промпт
            for prompt_name, prompt_text in prompts.items():
                if not prompt_text or prompt_text.strip() == "":
                    continue
                    
                # Определяем язык
                lang = 'ru' if prompt_name.startswith('stage_1') else 'en'
                
                # Добавляем промпт
                cursor.execute("""
                    INSERT INTO template_prompts (template_id, prompt_name, prompt_text, language, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (template_id, prompt_name, prompt_text, lang, f"Перенесено из старой структуры: {prompt_name}"))
                
                print(f"  ✓ {prompt_name} ({lang})")
            
            # Мигрируем настройки (если есть)
            if settings_json and settings_json.strip() != "":
                try:
                    settings = json.loads(settings_json)
                    for key, value in settings.items():
                        if isinstance(value, (str, int, float)):
                            cursor.execute("""
                                INSERT INTO template_settings (template_id, setting_key, setting_value)
                                VALUES (?, ?, ?)
                            """, (template_id, key, str(value)))
                            print(f"  ✓ settings.{key} = {value}")
                except:
                    print("  ⚠️  Ошибка парсинга settings_json")
            
            # Обновляем флаг миграции
            cursor.execute("""
                UPDATE templates 
                SET settings_json = json_insert(settings_json, '$.migrated_to_v2', 'true')
                WHERE id = ?
            """, (template_id,))
            
            print(f"  ✅ Миграция завершена для {template_id}")
            
        except json.JSONDecodeError as e:
            print(f"  ❌ Ошибка парсинга prompts_json: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*50)
    print("Миграция завершена!")
    print("="*50)

if __name__ == "__main__":
    migrate()
