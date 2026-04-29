import os
import json
import pathlib
from dotenv import load_dotenv
from yandex_ai_studio_sdk import AIStudio

load_dotenv()

def run_yandex_chars():
    api_key = os.getenv("YANDEX_API_KEY")
    folder_id = os.getenv("YANDEX_FOLDER_ID")

    if not api_key or not folder_id:
        print("❌ Ошибка: Проверь YANDEX_API_KEY и YANDEX_FOLDER_ID в .env")
        return

    sdk = AIStudio(folder_id=folder_id, auth=api_key)
    model = sdk.models.image_generation("yandex-art")

    # Конфигурируем модель (квадрат 1:1)
    model = model.configure(width_ratio=1, height_ratio=1, seed=42)

    # Загружаем наш конфиг
    try:
        with open("data/visual_config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ Ошибка: Файл data/visual_config.json не найден.")
        return

    entities = config.get("characters", {})

    # УНИВЕРСАЛЬНЫЙ ТЕХНИЧЕСКИЙ СТИЛЬ
    # Он дает четкие формы и чистые цвета без привязки к конкретной художке
    universal_style = (
        "High-quality studio character concept art, full length body shot, "
        "neutral grey background, soft studio lighting, sharp focus, "
        "highly detailed, professional 3D render aesthetics, clean lines"
    )

    os.makedirs("outputs/references", exist_ok=True)

    print(f"🎨 Запуск YandexART. Генерация {len(entities)} универсальных референсов...")

    for name, description in entities.items():
        print(f"\n👤 Персонаж: {name}")
        
        # Основной промпт: берем только описание внешности из JSON
        # Ограничиваем длину описания, чтобы не вылетало за лимиты YandexART
        char_desc_short = description[:600] 
        
        final_prompt = f"Character reference sheet: {char_desc_short}. {universal_style}"
        
        # Печатаем для контроля длины
        print(f"📏 Длина итогового промпта: {len(final_prompt)} символов.")

        try:
            # Отправляем один объединенный текст (так надежнее для контроля лимитов)
            operation = model.run_deferred(final_prompt)
            
            result = operation.wait()
            
            output_path = pathlib.Path(f"outputs/references/{name}.jpeg")
            output_path.write_bytes(result.image_bytes)
            
            print(f"✅ Успешно сохранено: {output_path}")

        except Exception as e:
            print(f"❌ Ошибка при генерации {name}: {e}")

if __name__ == "__main__":
    run_yandex_chars()