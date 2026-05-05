import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import openai

load_dotenv()

def run_stage_2():
    print("🎬 Stage 2: Режиссер начинает планирование кадров (Gemma 3)...")

    # 1. Настройки доступа (как в инструкции)
    YANDEX_CLOUD_FOLDER = os.getenv("YANDEX_FOLDER_ID")
    YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_API_KEY")
    YANDEX_CLOUD_MODEL = "gemma-3-27b-it/latest"
    
    if not YANDEX_CLOUD_API_KEY or not YANDEX_CLOUD_FOLDER:
        print("❌ Ошибка: Проверь YANDEX_API_KEY и YANDEX_FOLDER_ID в .env")
        return False

    client = openai.OpenAI(
        api_key=YANDEX_CLOUD_API_KEY,
        base_url="https://ai.api.cloud.yandex.net/v1",
        project=YANDEX_CLOUD_FOLDER
    )

    # 2. Загрузка данных из Stage 1
    try:
        with open("data/1_base_structure.json", "r", encoding="utf-8") as f:
            episodes = json.load(f)
        with open("data/visual_config.json", "r", encoding="utf-8") as f:
            visual_config = json.load(f)
        
        # Берем промпт из UI или из файла
        system_instruction = prompts.get("stage_2_scenes", "") if prompts else ""
        if not system_instruction:
            system_instruction = Path("prompts/stage_2_scenes.txt").read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ Ошибка загрузки данных: {e}")
        return False

    char_names = list(visual_config.get("characters", {}).keys())
    production_map = {"episodes": {}}

    # 3. ЦИКЛ ПО ЭПИЗОДАМ
    for ep_key, ep_text in episodes.items():
        print(f"🎥 Планируем кадры для {ep_key}...")
        
        # Подготовка контекста для Gemma
        main_char = char_names[0] if len(char_names) > 0 else "N/A"
        prompt_input = f"TEXT: {ep_text}\nCHARACTERS: [MAIN_1]={main_char}. Output ONLY valid JSON."
        
        try:
            # Используем метод .responses.create строго по примеру
            response = client.responses.create(
                model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
                temperature=0.3, # Понижаем для стабильного JSON
                instructions=system_instruction,
                input=prompt_input,
                max_output_tokens=3000
            )
            
            raw_res = response.output_text.strip()
            
            # Очистка JSON от маркдауна Gemma
            if "```" in raw_res:
                raw_res = raw_res.split("```")[1]
                if raw_res.startswith("json"):
                    raw_res = raw_res[4:].strip()
                raw_res = raw_res.strip()

            scenes_data = json.loads(raw_res)
            production_map["episodes"][ep_key] = scenes_data.get("scenes", [])
            
            # Небольшая пауза для стабильности
            time.sleep(1)

        except Exception as e:
            print(f"❌ Ошибка на {ep_key}: {e}")
            # Для отладки выведем часть ответа, если он был
            if 'response' in locals():
                 print(f"Ответ модели: {response.output_text[:200]}...")
            return False

    # 4. Сохранение итоговой карты производства
    production_map["characters_metadata"] = visual_config.get("characters", {})

    os.makedirs("data", exist_ok=True)
    with open("data/2_production_map.json", "w", encoding="utf-8") as f:
        json.dump(production_map, f, ensure_ascii=False, indent=2)

    print(f"✅ Stage 2 завершен. Сцены сохранены в 2_production_map.json")
    return True

if __name__ == "__main__":
    run_stage_2()