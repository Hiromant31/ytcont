import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import openai
# Импортируем утилиты из stage_1 для единообразия
from .stage_1_story import load_settings, repair_truncated_json

load_dotenv()

def run_stage_2(ai_settings=None, prompts=None):
    print("🎬 Stage 2: Режиссер начинает планирование кадров...")

    # 1. Настройки AI (универсально как в Stage 1)
    settings = load_settings()
    ai_text = ai_settings["text"] if ai_settings and "text" in ai_settings else settings.get("ai_settings", {}).get("text", {})
    
    api_url   = ai_text.get("api_url", "https://ai.api.cloud.yandex.net/v1")
    api_key   = ai_text.get("api_key", "")
    folder_id = ai_text.get("folder_id", "")
    model     = ai_text.get("model", "gemma-3-27b-it/latest")
    is_yandex = "yandex" in api_url.lower() or "ai.api.cloud.yandex" in api_url

    if not api_key:
        print("❌ Ошибка: Не задан api_key")
        return False

    # Клиент
    client = openai.OpenAI(api_key=api_key, base_url=api_url, project=folder_id if is_yandex else None)

    # 2. Загрузка данных и промптов
    try:
        with open("data/1_base_structure.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        # Поддержка обоих форматов: старый (episodes) и новый (episodes_final)
        episodes = data.get("episodes_final", data.get("episodes", {}))
        
        # Загружаем visual_config
        with open("data/visual_config.json", "r", encoding="utf-8") as f:
            visual_config = json.load(f)
        
        # Извлекаем characters — обработка разных форматов
        if isinstance(visual_config, list) and len(visual_config) > 0:
            visual_config = visual_config[0]  # Берем первый элемент как dict
        elif isinstance(visual_config, dict):
            pass  # Уже dict
        else:
            visual_config = {}  # Пустой словарь по умолчанию

        char_data = visual_config.get("characters", {})
        
        # Дополнительная защита: если char_data - это список, преобразуем в словарь
        if isinstance(char_data, list):
            temp_chars = {}
            for i, item in enumerate(char_data):
                if isinstance(item, dict) and "name" in item:
                    temp_chars[item["name"]] = item.get("description", str(item))
                elif isinstance(item, dict):
                    temp_chars[f"Character_{i+1}"] = str(item)
                else:
                    temp_chars[f"Character_{i+1}"] = str(item)
            char_data = temp_chars
        elif not isinstance(char_data, dict):
            char_data = {}

        # Берем промпт из UI или из файла
        system_instruction = prompts.get("stage_2_scenes", "") if prompts else ""
        if not system_instruction:
            system_instruction = Path("prompts/stage_2_scenes.txt").read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ Ошибка загрузки данных: {e}")
        return False

    char_names = list(char_data.keys())
    production_map = {"episodes": {}}

    # 3. Цикл по эпизодам
    for ep_key, ep_text in episodes.items():
        print(f"🎥 Планируем кадры для {ep_key}...")
        main_char = char_names[0] if len(char_names) > 0 else "N/A"
        prompt_input = f"TEXT: {ep_text}\nCHARACTERS: [MAIN_1]={main_char}. Output ONLY valid JSON."
        
        try:
            if is_yandex:
                response = client.responses.create(
                    model=f"gpt://{folder_id}/{model}",
                    temperature=0.2,
                    instructions=system_instruction,
                    input=prompt_input,
                    max_output_tokens=4000
                )
                raw_res = response.output_text
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt_input}
                    ],
                    temperature=0.2
                )
                raw_res = response.choices[0].message.content

            # Используем надежный парсер из Stage 1
            scenes_data = repair_truncated_json(raw_res)
            production_map["episodes"][ep_key] = scenes_data.get("scenes", [])
            time.sleep(1)

        except Exception as e:
            print(f"❌ Ошибка на {ep_key}: {e}")
            return False

    production_map["characters_metadata"] = visual_config.get("characters", {})
    os.makedirs("data", exist_ok=True)
    with open("data/2_production_map.json", "w", encoding="utf-8") as f:
        json.dump(production_map, f, ensure_ascii=False, indent=2)

    print(f"✅ Stage 2 завершен.")
    return True
