import os
import sys
import json
import pathlib
import traceback
from dotenv import load_dotenv
from yandex_ai_studio_sdk import AIStudio

load_dotenv()

def normalize_visual_config(config):
    """
    Универсальная нормализация visual_config.
    Возвращает dict с keys: characters, visual_style
    """
    # Случай 1: список
    if isinstance(config, list):
        print("🔄 [NORMALIZE] Config - список, ищем персонажей...")
        result = {"characters": {}, "visual_style": "Not specified"}
        
        for i, item in enumerate(config):
            if isinstance(item, dict):
                if "characters" in item:
                    result["characters"].update(item["characters"])
                    print(f"   ✓ Найдены персонажи в элементе {i}")
                if "visual_style" in item:
                    result["visual_style"] = item["visual_style"]
        
        return result
    
    # Случай 2: словарь
    if isinstance(config, dict):
        if "characters" not in config:
            print("⚠️ [NORMALIZE] Нет секции 'characters'")
            config["characters"] = {}
        
        # Нормализация characters
        chars = config["characters"]
        if isinstance(chars, list):
            normalized = {}
            for i, item in enumerate(chars):
                if isinstance(item, dict) and "name" in item:
                    normalized[item["name"]] = item.get("description", str(item))
                else:
                    normalized[f"Character_{i+1}"] = str(item)
            config["characters"] = normalized
        elif not isinstance(chars, dict):
            config["characters"] = {}
        
        if "visual_style" not in config:
            config["visual_style"] = "Not specified"
        
        return config
    
    # Случай 3: неизвестный тип
    print(f"⚠️ [NORMALIZE] Неизвестный тип: {type(config).__name__}")
    return {"characters": {}, "visual_style": "Not specified"}


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
        print("✅ [STAGE 3] Модель инициализирована (формат 1:1)", flush=True)

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

        # Нормализация конфига
        print("\n🔄 [STAGE 3] Нормализация конфига...", flush=True)
        config = normalize_visual_config(config)
        
        characters = config.get("characters", {})
        visual_style = config.get("visual_style", "Not specified")
        
        print(f"🎯 [STAGE 3] Итоговое количество персонажей: {len(characters)}", flush=True)
        print(f"🎨 [STAGE 3] Визуальный стиль: {visual_style[:100]}...", flush=True)
        
        # Проверка наличия персонажей
        if len(characters) == 0:
            print("\n⚠️ [STAGE 3 WARNING] Список персонажей пуст!", flush=True)
            print("💡 [STAGE 3] Возможные причины:", flush=True)
            print("   1. Stage 1 не выполнил извлечение персонажей корректно", flush=True)
            print("   2. В visual_config.json нет секции 'characters'", flush=True)
            print("   3. Требуется перезапустить Stage 1", flush=True)
            
            # Создаём пустую папку для обозначения завершения этапа
            os.makedirs("outputs/references", exist_ok=True)
            print("\n⚠️ [STAGE 3] Этап завершён БЕЗ генерации (нет персонажей)", flush=True)
            print("=" * 60, flush=True)
            return True
        
        print(f"\n📂 [STAGE 3] Создание папки outputs/references...", flush=True)
        os.makedirs("outputs/references", exist_ok=True)
        print("✅ [STAGE 3] Папка готова", flush=True)

        # ТЕХНИЧЕСКИЙ СТИЛЬ ДЛЯ ЭТАЛОНА (чтобы лицо было четко видно)
        # Используем visual_style из конфига если есть, иначе дефолтный
        if visual_style and visual_style != "Not specified":
            ref_style = visual_style
        else:
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
            # Проверяем, является ли персонаж группой людей
            is_group = any(word in name.lower() for word in ['семья', 'толпа', 'банда', 'команда', 'группа', 'family', 'crowd', 'gang', 'team', 'group'])
            
            if is_group:
                print(f"👥 [STAGE 3] Обнаружена ГРУППА персонажей: {name}", flush=True)
                final_prompt = f"{description}. Group portrait, multiple people. {ref_style}"
            else:
                final_prompt = f"{description}. Single character portrait. {ref_style}"
            
            print(f"🔤 [STAGE 3] Промпт ({len(final_prompt)} символов): {final_prompt[:150]}...", flush=True)

            try:
                print(f"⏳ [STAGE 3] Запуск генерации изображения...", flush=True)
                operation = model.run_deferred(final_prompt)
                print(f"⏳ [STAGE 3] Ожидание результата от Yandex API...", flush=True)
                result = operation.wait()
                print(f"✅ [STAGE 3] Изображение получено ({len(result.image_bytes)} байт)", flush=True)
                
                # Sanitize filename
                safe_name = "".join(c if c.isalnum() or c in "_ -" else "_" for c in name)
                output_path = pathlib.Path(f"outputs/references/{safe_name}.jpeg")
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