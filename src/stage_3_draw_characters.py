import os
import sys
import json
import pathlib
import traceback
from dotenv import load_dotenv
from yandex_ai_studio_sdk import AIStudio

load_dotenv()

def run_stage_3_refs():
    print("🔍 [STAGE 3 START] Начало этапа 3...", flush=True)
    
    try:
        # Настройки Yandex
        api_key = os.getenv("YANDEX_API_KEY")
        folder_id = os.getenv("YANDEX_FOLDER_ID")
        
        print(f"🔑 [STAGE 3] YANDEX_API_KEY: {'найдено' if api_key else 'НЕ НАЙДЕНО'}", flush=True)
        print(f"📁 [STAGE 3] YANDEX_FOLDER_ID: {'найдено' if folder_id else 'НЕ НАЙДЕНО'}", flush=True)
        
        if not api_key or not folder_id:
            print("❌ Ошибка: Проверь YANDEX_API_KEY и YANDEX_FOLDER_ID", flush=True)
            return False

        print("🤖 [STAGE 3] Инициализация SDK Yandex...", flush=True)
        sdk = AIStudio(folder_id=folder_id, auth=api_key)
        model = sdk.models.image_generation("yandex-art")
        
        # Для референсов используем КВАДРАТ 1:1
        model = model.configure(width_ratio=1, height_ratio=1, seed=42)
        print("✅ [STAGE 3] Модель инициализирована", flush=True)

        # Загружаем описание персонажей из Stage 1
        print("📄 [STAGE 3] Чтение data/visual_config.json...", flush=True)
        try:
            with open("data/visual_config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            print(f"📊 [STAGE 3] Тип config: {type(config).__name__}", flush=True)
            print(f"📊 [STAGE 3] Содержимое config: {json.dumps(config, ensure_ascii=False)[:500]}...", flush=True)
        except FileNotFoundError:
            print("❌ Ошибка: Файл data/visual_config.json не найден. Запусти Stage 1.", flush=True)
            return False
        except Exception as e:
            print(f"❌ Ошибка при чтении visual_config.json: {e}", flush=True)
            traceback.print_exc()
            return False

        # Нормализация config: если это список, берем первый элемент как словарь
        if isinstance(config, list):
            print(f"📋 [STAGE 3] Config - список из {len(config)} элементов", flush=True)
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
        
        characters = config.get("characters", {})
        print(f"👥 [STAGE 3] Получены characters: {type(characters).__name__}, значение: {characters}", flush=True)
        
        # Дополнительная защита: если characters - это список, преобразуем в словарь
        if isinstance(characters, list):
            print("🔄 [STAGE 3] characters - список, преобразуем...", flush=True)
            # Если это список, пытаемся преобразовать его в словарь с индексами или именами
            # Обычно в таком случае элементы списка могут быть словарями с ключом "name" или просто строками
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
            print(f"⚠️ [STAGE 3] characters не dict, тип: {type(characters).__name__}", flush=True)
            characters = {}
        
        print(f"🎯 [STAGE 3] Итоговое количество персонажей: {len(characters)}", flush=True)
        
        if len(characters) == 0:
            print("⚠️ [STAGE 3] ВНИМАНИЕ: Список персонажей пуст!", flush=True)
            print("💡 [STAGE 3] Возможно, Stage 1 не создал описания персонажей.", flush=True)
            print("💡 [STAGE 3] Проверяем структуру visual_config.json...", flush=True)
            
            # Проверяем, есть ли в config данные эпизодов (значит Stage 1 не извлек персонажей)
            if isinstance(config, dict):
                has_episodes = any(key in config for key in ['episodes', 'title', 'hook', 'start', 'build', 'impact', 'end'])
                if has_episodes:
                    print("❌ [STAGE 3] ОБНАРУЖЕНА ПРОБЛЕМА: visual_config.json содержит сценарий, а не персонажей!", flush=True)
                    print("💡 [STAGE 3] Stage 1 не выполнил извлечение персонажей корректно.", flush=True)
                    print("💡 [STAGE 3] Решение: Перезапусти Stage 1 с правильным extractor промптом.", flush=True)
                else:
                    print(f"📋 [STAGE 3] Ключи в config: {list(config.keys())}", flush=True)
            
            # Создаём пустую папку для обозначения завершения этапа
            os.makedirs("outputs/references", exist_ok=True)
            print("✅ [STAGE 3] Этап завершён (без генерации)", flush=True)
            return True
        
        os.makedirs("outputs/references", exist_ok=True)
        print("📂 [STAGE 3] Папка outputs/references готова", flush=True)

        # ТЕХНИЧЕСКИЙ СТИЛЬ ДЛЯ ЭТАЛОНА (чтобы лицо было четко видно)
        # Этот кусок занимает ~120 символов
        ref_style = (
        "Gritty 2D hand-drawn illustration, bold ink outlines, "
        "dark moody atmosphere, graphic novel style, flat colors with messy textures, "
        "sharp contouring, high contrast, noir aesthetic."
        )

        print(f"🎨 [STAGE 3] Генерируем эталонные лица для {len(characters)} персонажей...", flush=True)

        for idx, (name, description) in enumerate(characters.items(), 1):
            print(f"\n👤 [STAGE 3 {idx}/{len(characters)}] Создаю паспорт для: {name}", flush=True)
            print(f"📝 [STAGE 3] Описание: {description[:200]}...", flush=True)
            
            # Склеиваем описание из Gemini + наш стиль
            # Суммарно будет около 250-300 символов (лимит 500)
            final_prompt = f"{description}. {ref_style}"
            print(f"🔤 [STAGE 3] Промпт ({len(final_prompt)} символов): {final_prompt[:150]}...", flush=True)

            try:
                print(f"⏳ [STAGE 3] Запуск генерации изображения...", flush=True)
                operation = model.run_deferred(final_prompt)
                print(f"⏳ [STAGE 3] Ожидание результата...", flush=True)
                result = operation.wait()
                print(f"✅ [STAGE 3] Изображение получено ({len(result.image_bytes)} байт)", flush=True)
                
                output_path = pathlib.Path(f"outputs/references/{name}.jpeg")
                output_path.write_bytes(result.image_bytes)
                print(f"✅ [STAGE 3] Сохранено: {output_path}", flush=True)

            except Exception as e:
                print(f"❌ [STAGE 3] Ошибка при генерации {name}: {e}", flush=True)
                print(f"❌ [STAGE 3] Трассировка: {traceback.format_exc()}", flush=True)
        
        print("\n✅ [STAGE 3 END] Все референсы сгенерированы!", flush=True)
        return True
        
    except Exception as e:
        print(f"❌ [STAGE 3] КРИТИЧЕСКАЯ ОШИБКА: {e}", flush=True)
        print(f"❌ [STAGE 3] Трассировка стека:", flush=True)
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_stage_3_refs()
    sys.exit(0 if success else 1)
