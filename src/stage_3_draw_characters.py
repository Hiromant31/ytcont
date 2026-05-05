import os
import sys
import json
import pathlib
import traceback
from dotenv import load_dotenv
from yandex_ai_studio_sdk import AIStudio

load_dotenv()

def run_stage_3_refs():
    print("=" * 60, flush=True)
    print("🔍 [STAGE 3 START] Начало этапа 3: Референсы лиц", flush=True)
    print("=" * 60, flush=True)
    
    try:
        # Настройки Yandex
        api_key = os.getenv("YANDEX_API_KEY")
        folder_id = os.getenv("YANDEX_FOLDER_ID")
        
        print(f"\n🔑 [STAGE 3] Проверка переменных окружения:", flush=True)
        print(f"   YANDEX_API_KEY: {'✅ найдено' if api_key else '❌ НЕ НАЙДЕНО'}", flush=True)
        print(f"   YANDEX_FOLDER_ID: {'✅ найдено' if folder_id else '❌ НЕ НАЙДЕНО'}", flush=True)
        
        if not api_key or not folder_id:
            print("\n❌ [STAGE 3 ERROR] Проверь YANDEX_API_KEY и YANDEX_FOLDER_ID в .env", flush=True)
            return False

        print(f"\n🤖 [STAGE 3] Инициализация SDK Yandex...", flush=True)
        sdk = AIStudio(folder_id=folder_id, auth=api_key)
        model = sdk.models.image_generation("yandex-art")
        
        # Для референсов используем КВАДРАТ 1:1
        model = model.configure(width_ratio=1, height_ratio=1, seed=42)
        print("✅ [STAGE 3] Модель инициализирована", flush=True)

        # Загружаем описание персонажей из Stage 1
        print(f"\n📄 [STAGE 3] Чтение data/visual_config.json...", flush=True)
        visual_config_path = "data/visual_config.json"
        
        if not os.path.exists(visual_config_path):
            print(f"❌ [STAGE 3 ERROR] Файл {visual_config_path} не найден!", flush=True)
            print("💡 [STAGE 3] Запусти Stage 1 сначала.", flush=True)
            return False
            
        try:
            with open(visual_config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            print(f"✅ [STAGE 3] Файл успешно прочитан", flush=True)
            print(f"📊 [STAGE 3] Тип config: {type(config).__name__}", flush=True)
        except json.JSONDecodeError as e:
            print(f"❌ [STAGE 3 ERROR] Ошибка парсинга JSON: {e}", flush=True)
            traceback.print_exc()
            return False
        except Exception as e:
            print(f"❌ [STAGE 3 ERROR] Ошибка при чтении visual_config.json: {e}", flush=True)
            traceback.print_exc()
            return False

        # Извлекаем персонажей - поддержка разных форматов JSON
        characters = {}
        
        # Формат A: config - это список эпизодов (текущий проблемный случай)
        # ПРОВЕРЯЕМ СНАЧАЛА, до нормализации!
        if isinstance(config, list):
            print(f"\n⚠️ [STAGE 3] Config - список из {len(config)} элементов (эпизоды)", flush=True)
            print("💡 [STAGE 3] В visual_config.json нет секции 'characters'!", flush=True)
            print("💡 [STAGE 3] Это означает, что Stage 1 не выполнил извлечение персонажей.", flush=True)
            print("💡 [STAGE 3] Требуется перезапустить Stage 1 для корректного извлечения персонажей.", flush=True)
            
            # Пытаемся найти персонажей в каждом элементе списка
            for i, item in enumerate(config):
                if isinstance(item, dict):
                    if "characters" in item:
                        characters.update(item["characters"])
                        print(f"   ✓ Найдены персонажи в элементе {i}", flush=True)
                    # Проверяем другие возможные ключи
                    for key in item.keys():
                        if "char" in key.lower() or "hero" in key.lower() or "person" in key.lower():
                            print(f"   ⚠️ Подозрительный ключ '{key}' в элементе {i}, но не 'characters'", flush=True)
            
            if not characters:
                print("\n❌ [STAGE 3 ERROR] Персонажи не найдены ни в одном элементе списка!", flush=True)
                print("\n" + "="*60, flush=True)
                print("🛑 [STAGE 3 ABORT] Прерывание этапа 3 из-за отсутствия персонажей", flush=True)
                print("="*60, flush=True)
                print("\n📋 ИНСТРУКЦИЯ ПО ИСПРАВЛЕНИЮ:", flush=True)
                print("   1. Запусти Stage 1 заново: python src/stage_1_story.py", flush=True)
                print("   2. Проверь, что в data/visual_config.json появилась секция 'characters'", flush=True)
                print("   3. После этого запусти Stage 3 снова", flush=True)
                print("="*60, flush=True)
                return False  # Прерываем выполнение, так как нет персонажей
        
        # Нормализация config: если это список, берем первый элемент как словарь
        # (этот код теперь достигнут только если список был пуст или персонажи найдены)
        elif isinstance(config, list):
            if len(config) > 0:
                config = config[0]
                print(f"📋 [STAGE 3] Берём первый элемент списка", flush=True)
            else:
                config = {}
                print("⚠️ [STAGE 3] Пустой список, используем {}", flush=True)
        elif not isinstance(config, dict):
            print(f"⚠️ [STAGE 3] Config не dict и не list, тип: {type(config).__name__}", flush=True)
            config = {}

        print(f"🔑 [STAGE 3] Ключи в config: {list(config.keys()) if isinstance(config, dict) else 'N/A'}", flush=True)
        
        # Продолжаем извлечение персонажей для словаря
        # Формат B: {"characters": {...}}
        if isinstance(config, dict) and "characters" in config:
            characters = config.get("characters", {})
            print(f"\n👥 [STAGE 3] Найдена секция 'characters' в словаре", flush=True)
        
        # Формат C: config - словарь без ключа "characters"
        elif isinstance(config, dict) and len(characters) == 0:
            print(f"\n⚠️ [STAGE 3] Config - словарь без секции 'characters'", flush=True)
            print("💡 [STAGE 3] Проверяем альтернативные ключи...", flush=True)
            
            # Ищем похожие ключи
            alt_keys = ["chars", "heroes", "persons", "actors", "cast", "roles"]
            for key in alt_keys:
                if key in config:
                    characters = config[key]
                    print(f"   ✓ Найдена альтернативная секция '{key}'", flush=True)
                    break
            
            if not characters:
                print("   ❌ Альтернативные ключи не найдены", flush=True)
                print(f"   📋 Доступные ключи: {list(config.keys())}", flush=True)
        
        # Преобразуем characters в словарь если это список
        if isinstance(characters, list):
            print("🔄 [STAGE 3] characters - список, преобразуем...", flush=True)
            temp_chars = {}
            for i, item in enumerate(characters):
                if isinstance(item, dict) and "name" in item:
                    temp_chars[item["name"]] = item.get("description", str(item))
                elif isinstance(item, dict):
                    temp_chars[f"Character_{i+1}"] = str(item)
                else:
                    temp_chars[f"Character_{i+1}"] = str(item)
            characters = temp_chars
            print(f"✅ [STAGE 3] Преобразовано в: {characters}", flush=True)
        elif not isinstance(characters, dict):
            print(f"⚠️ [STAGE 3] characters не dict и не list, тип: {type(characters).__name__}", flush=True)
            characters = {}
        
        print(f"\n🎯 [STAGE 3] Итоговое количество персонажей: {len(characters)}", flush=True)
        
        if len(characters) == 0:
            print("\n⚠️ [STAGE 3 WARNING] Список персонажей пуст!", flush=True)
            print("💡 [STAGE 3] Возможные причины:", flush=True)
            print("   1. Stage 1 не выполнил извлечение персонажей корректно", flush=True)
            print("   2. В visual_config.json нет секции 'characters'", flush=True)
            
            # Проверяем структуру config
            if isinstance(config, dict):
                has_episodes = any(key in config for key in ['episodes', 'title', 'hook', 'start', 'build', 'impact', 'end'])
                if has_episodes:
                    print("\n❌ [STAGE 3 PROBLEM] visual_config.json содержит сценарий эпизода, а не персонажей!", flush=True)
                    print("💡 [STAGE 3] Stage 1 не создал описания персонажей.", flush=True)
                    print("💡 [STAGE 3] Решение:", flush=True)
                    print("   - Вариант A: Перезапусти Stage 1 с правильным промптом для извлечения персонажей", flush=True)
                    print("   - Вариант B: Добавь секцию 'characters' вручную в visual_config.json", flush=True)
                else:
                    print(f"\n📋 [STAGE 3] Ключи в config: {list(config.keys())}", flush=True)
            
            # Создаём пустую папку для обозначения завершения этапа
            os.makedirs("outputs/references", exist_ok=True)
            print("\n⚠️ [STAGE 3] Этап завершён БЕЗ генерации (нет персонажей)", flush=True)
            print("=" * 60, flush=True)
            return True
        
        print(f"\n📂 [STAGE 3] Создание папки outputs/references...", flush=True)
        os.makedirs("outputs/references", exist_ok=True)
        print("✅ [STAGE 3] Папка готова", flush=True)

        # ТЕХНИЧЕСКИЙ СТИЛЬ ДЛЯ ЭТАЛОНА (чтобы лицо было четко видно)
        ref_style = (
        "Gritty 2D hand-drawn illustration, bold ink outlines, "
        "dark moody atmosphere, graphic novel style, flat colors with messy textures, "
        "sharp contouring, high contrast, noir aesthetic."
        )

        print(f"\n🎨 [STAGE 3] Генерируем эталонные лица для {len(characters)} персонажей...", flush=True)
        print(f"📝 [STAGE 3] Стиль: {ref_style[:100]}...", flush=True)

        generated_count = 0
        error_count = 0

        for idx, (name, description) in enumerate(characters.items(), 1):
            print(f"\n{'=' * 60}", flush=True)
            print(f"👤 [STAGE 3 {idx}/{len(characters)}] Обработка персонажа: {name}", flush=True)
            print(f"📝 [STAGE 3] Описание ({len(description)} символов): {description[:200]}...", flush=True)
            
            # Склеиваем описание из Gemini + наш стиль
            final_prompt = f"{description}. {ref_style}"
            print(f"🔤 [STAGE 3] Промпт ({len(final_prompt)} символов): {final_prompt[:150]}...", flush=True)

            try:
                print(f"⏳ [STAGE 3] Запуск генерации изображения...", flush=True)
                operation = model.run_deferred(final_prompt)
                print(f"⏳ [STAGE 3] Ожидание результата от Yandex API...", flush=True)
                result = operation.wait()
                print(f"✅ [STAGE 3] Изображение получено ({len(result.image_bytes)} байт)", flush=True)
                
                output_path = pathlib.Path(f"outputs/references/{name}.jpeg")
                output_path.write_bytes(result.image_bytes)
                print(f"✅ [STAGE 3] Сохранено: {output_path}", flush=True)
                generated_count += 1

            except Exception as e:
                print(f"\n❌ [STAGE 3 ERROR] Ошибка при генерации {name}:", flush=True)
                print(f"   Сообщение: {e}", flush=True)
                print(f"   Трассировка:", flush=True)
                traceback.print_exc()
                error_count += 1
        
        print(f"\n{'=' * 60}", flush=True)
        print(f"✅ [STAGE 3 END] Статистика:", flush=True)
        print(f"   Всего персонажей: {len(characters)}", flush=True)
        print(f"   Успешно сгенерировано: {generated_count}", flush=True)
        print(f"   Ошибок: {error_count}", flush=True)
        
        if error_count > 0:
            print(f"\n⚠️ [STAGE 3] Некоторые персонажи не были сгенерированы!", flush=True)
        
        print("=" * 60, flush=True)
        return True
        
    except Exception as e:
        print(f"\n❌ [STAGE 3 CRITICAL ERROR] КРИТИЧЕСКАЯ ОШИБКА: {e}", flush=True)
        print(f"❌ [STAGE 3] Трассировка стека:", flush=True)
        traceback.print_exc()
        print("=" * 60, flush=True)
        return False

if __name__ == "__main__":
    success = run_stage_3_refs()
    sys.exit(0 if success else 1)
