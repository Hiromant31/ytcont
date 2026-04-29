import os
import json
import pathlib
from dotenv import load_dotenv
from yandex_ai_studio_sdk import AIStudio

load_dotenv()

def run_stage_3_refs():
    # Настройки Yandex
    api_key = os.getenv("YANDEX_API_KEY")
    folder_id = os.getenv("YANDEX_FOLDER_ID")
    
    if not api_key or not folder_id:
        print("❌ Ошибка: Проверь YANDEX_API_KEY и YANDEX_FOLDER_ID")
        return

    sdk = AIStudio(folder_id=folder_id, auth=api_key)
    model = sdk.models.image_generation("yandex-art")
    
    # Для референсов используем КВАДРАТ 1:1
    model = model.configure(width_ratio=1, height_ratio=1, seed=42)

    # Загружаем описание персонажей из Stage 1
    try:
        with open("data/visual_config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ Ошибка: Файл data/visual_config.json не найден. Запусти Stage 1.")
        return

    characters = config.get("characters", {})
    os.makedirs("outputs/references", exist_ok=True)

    # ТЕХНИЧЕСКИЙ СТИЛЬ ДЛЯ ЭТАЛОНА (чтобы лицо было четко видно)
    # Этот кусок занимает ~120 символов
    ref_style = (
    "Gritty 2D hand-drawn illustration, bold ink outlines, "
    "dark moody atmosphere, graphic novel style, flat colors with messy textures, "
    "sharp contouring, high contrast, noir aesthetic."
)

    print(f"🎨 Генерируем эталонные лица для {len(characters)} персонажей...")

    for name, description in characters.items():
        print(f"👤 Создаю паспорт для: {name}")
        
        # Склеиваем описание из Gemini + наш стиль
        # Суммарно будет около 250-300 символов (лимит 500)
        final_prompt = f"{description}. {ref_style}"

        try:
            operation = model.run_deferred(final_prompt)
            result = operation.wait()
            
            output_path = pathlib.Path(f"outputs/references/{name}.jpeg")
            output_path.write_bytes(result.image_bytes)
            print(f"✅ Сохранено: {output_path}")

        except Exception as e:
            print(f"❌ Ошибка при генерации {name}: {e}")

if __name__ == "__main__":
    run_stage_3_refs()