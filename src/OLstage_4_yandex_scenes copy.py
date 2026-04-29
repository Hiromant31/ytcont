import os
import json
import pathlib
from dotenv import load_dotenv
from yandex_ai_studio_sdk import AIStudio

load_dotenv()

def run_yandex_scenes():
    # Настройки доступа
    api_key = os.getenv("YANDEX_API_KEY")
    folder_id = os.getenv("YANDEX_FOLDER_ID")
    sdk = AIStudio(folder_id=folder_id, auth=api_key)
    model = sdk.models.image_generation("yandex-art")
    model = model.configure(width_ratio=16, height_ratio=9, seed=42)

    # 1. Загружаем данные
    with open("data/visual_config.json", "r", encoding="utf-8") as f:
        v_config = json.load(f)
    with open("data/2_production_map.json", "r", encoding="utf-8") as f:
        p_map = json.load(f)

    # 2. Готовим сжатые версии для лимита 500 символов
    # Берем только первые 60 символов стиля для экономии места
    short_style = "Cinematic dark thriller, high-contrast, cold palette, 8k" 
    
    # Создаем карту коротких описаний персонажей (берем только первые 100 символов)
    chars = v_config.get("characters", {})
    short_chars = {name: desc[:100] for name, desc in chars.items()}

    scenes = p_map.get("production_scenes", [])
    os.makedirs("outputs/scenes", exist_ok=True)

    print(f"🎬 Начинаю генерацию первых {min(len(scenes), 3)} кадров...")

    # Генерируем только первые 3 кадра для теста
    for i, scene in enumerate(scenes[:3]):
        raw_prompt = scene.get("visual_prompt", "")
        
        # ЛОГИКА ЗАМЕНЫ ТЕГОВ
        # Заменяем [STYLE]
        final_prompt = raw_prompt.replace("[STYLE]", short_style)
        
        # Заменяем [MAIN_1], [MAIN_2] и т.д. на реальные описания из конфига
        # В твоем production_map [MAIN_1] - это Протагонист, [MAIN_2] - Родственники
        final_prompt = final_prompt.replace("[MAIN_1]", short_chars.get("The_Protagonist", ""))
        final_prompt = final_prompt.replace("[MAIN_2]", short_chars.get("The_Relatives", ""))
        final_prompt = final_prompt.replace("[PLACE_1]", "luxurious dark grand hall")

        # ЖЕСТКАЯ ОБРЕЗКА ПОД ЛИМИТ ЯНДЕКСА (500 символов)
        if len(final_prompt) > 500:
            final_prompt = final_prompt[:497] + "..."

        print(f"📸 Кадр {i+1} | Длина: {len(final_prompt)} | Текст: {final_prompt[:80]}...")

        try:
            operation = model.run_deferred(final_prompt)
            result = operation.wait()
            
            out_path = pathlib.Path(f"outputs/scenes/scene_{i+1}.jpeg")
            out_path.write_bytes(result.image_bytes)
            print(f"✅ Готово: {out_path}")
        except Exception as e:
            print(f"❌ Ошибка в кадре {i+1}: {e}")

if __name__ == "__main__":
    run_yandex_scenes()