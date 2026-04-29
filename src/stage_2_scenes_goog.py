import os
import json
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

def run_stage_2():
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:10809"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10809"
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"), http_options={'api_version': 'v1beta'})
    model_id = "gemini-2.5-flash"

    with open("data/1_base_structure.json", "r", encoding="utf-8") as f:
        episodes = json.load(f)
    with open("data/visual_config.json", "r", encoding="utf-8") as f:
        visual_config = json.load(f)
    system_instruction = open("prompts/stage_2_scenes.txt", "r", encoding="utf-8").read()

    char_names = list(visual_config.get("characters", {}).keys())
    production_map = {"episodes": {}}

    print(f"🎬 Режиссер начинает работу над {len(episodes)} эпизодами...")

    for ep_key, ep_text in episodes.items():
        print(f"🎥 Планируем кадры для {ep_key}...")
        
        prompt_context = f"TEXT: {ep_text}\nCHARACTERS: [MAIN_1]={char_names[0] if len(char_names)>0 else 'N/A'}"
        
        res = client.models.generate_content(
            model=model_id,
            contents=prompt_context,
            config={'response_mime_type': 'application/json', 'system_instruction': system_instruction}
        )
        
        scenes_data = json.loads(res.text)
        # Сохраняем сцены конкретного эпизода
        production_map["episodes"][ep_key] = scenes_data.get("scenes", [])
        
        time.sleep(10) # Защита от 429 ошибки

    # Добавляем общие метаданные персонажей
    production_map["characters_metadata"] = visual_config.get("characters", {})

    with open("data/2_production_map.json", "w", encoding="utf-8") as f:
        json.dump(production_map, f, ensure_ascii=False, indent=2)

    print("✅ Stage 2 завершен. Теперь у нас 3 отдельных списка сцен в одном файле.")

if __name__ == "__main__":
    run_stage_2()