import os
import json
import pathlib
import time
from dotenv import load_dotenv
from yandex_ai_studio_sdk import AIStudio

load_dotenv()

def run_stage_4_scenes():
    # Настройки Yandex
    api_key = os.getenv("YANDEX_API_KEY")
    folder_id = os.getenv("YANDEX_FOLDER_ID")
    
    if not api_key or not folder_id:
        print("❌ Ошибка: Проверь YANDEX_API_KEY и YANDEX_FOLDER_ID")
        return

    sdk = AIStudio(folder_id=folder_id, auth=api_key)
    model = sdk.models.image_generation("yandex-art")
    
    # УСТАНАВЛИВАЕМ ВЕРТИКАЛЬНЫЙ ФОРМАТ 9:16
    model = model.configure(width_ratio=9, height_ratio=16, seed=42)

    # ГЛОБАЛЬНЫЙ СТИЛЬ (держим коротким, ~100 симв.)
    # Это гарантирует, что все кадры будут в одной "рисовке"
    global_style = (
    "Hand-drawn 2D animation style, visible ink strokes, "
    "dark gloomy lighting, gritty atmosphere, deep shadows, "
    "cel shaded, cinematic comic book look, muffled colors."
)
    # Загружаем данные из предыдущих этапов
    try:
        with open("data/2_production_map.json", "r", encoding="utf-8") as f:
            production_map = json.load(f)
    except FileNotFoundError:
        print("❌ Ошибка: Файл data/2_production_map.json не найден. Запусти Stage 2.")
        return

    episodes = production_map.get("episodes", {})
    chars_metadata = production_map.get("characters_metadata", {})
    
    # Подготовим список имен для сопоставления с тегами
    char_names = list(chars_metadata.keys())

    print(f"🚀 Начинаем генерацию сцен для {len(episodes)} эпизодов...")

    for ep_name, scenes in episodes.items():
        print(f"\n📺 Работаем над: {ep_name}")
        ep_folder = f"outputs/scenes/{ep_name}"
        os.makedirs(ep_folder, exist_ok=True)

        for scene in scenes:
            scene_id = scene.get("scene_id")
            raw_visual = scene.get("visual_prompt", "")
            
            # 1. ЗАМЕНА ТЕГОВ ПЕРСОНАЖЕЙ
            # Берем описание из метаданных (ограничим до 150 симв, чтобы влезло действие)
            main_1_desc = chars_metadata.get(char_names[0], "")[:150] if len(char_names) > 0 else ""
            main_2_desc = chars_metadata.get(char_names[1], "")[:150] if len(char_names) > 1 else ""
            
            processed_prompt = raw_visual.replace("[MAIN_1]", main_1_desc)
            processed_prompt = processed_prompt.replace("[MAIN_2]", main_2_desc)
            # Если в Director (Stage 2) мы не определили место, добавим дефолт
            processed_prompt = processed_prompt.replace("[PLACE_1]", "cinematic environment")

            # 2. ФИНАЛЬНАЯ СБОРКА ПРОМПТА
            # Структура: [Действие] + [Стиль]
            final_prompt = f"{processed_prompt}. {global_style}"

            # 3. КОНТРОЛЬ ЛИМИТА (500 символов)
            if len(final_prompt) > 500:
                final_prompt = final_prompt[:497] + "..."

            print(f"   📸 Сцена {scene_id} | Промпт: {len(final_prompt)} симв.")

            try:
                operation = model.run_deferred(final_prompt)
                result = operation.wait()
                
                output_path = pathlib.Path(f"{ep_folder}/scene_{scene_id}.jpeg")
                output_path.write_bytes(result.image_bytes)
                
            except Exception as e:
                print(f"   ❌ Ошибка в сцене {scene_id}: {e}")
            
            # Небольшая пауза, чтобы не спамить API Яндекса
            time.sleep(1)

    print("\n✅ Все сцены отрисованы! Проверяй папку outputs/scenes/")

if __name__ == "__main__":
    run_stage_4_scenes()