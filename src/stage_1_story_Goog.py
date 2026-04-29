import os
import json
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

def run_stage_1():
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:10809"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10809"
    
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    model_id = "gemini-2.5-flash" 

    try:
        idea = open("idea.txt", "r", encoding="utf-8").read()
        writer_sys = open("prompts/writer_instruction.txt", "r", encoding="utf-8").read()
        extractor_sys = open("prompts/extractor_instruction.txt", "r", encoding="utf-8").read()
    except FileNotFoundError as e:
        print(f"❌ Ошибка: {e}")
        return

    # 1. ГЕНЕРАЦИЯ ЭПИЗОДОВ
    print("✍️ Пишем 3 отдельных эпизода...")
    chat = client.chats.create(model=model_id, config={'system_instruction': writer_sys})
    
    episodes = {}
    prompts = {
        "episode_1": "Напиши Эпизод 1: Завязка. На основе идеи: " + idea,
        "episode_2": "Напиши Эпизод 2: Кульминация.",
        "episode_3": "Напиши Эпизод 3: Финал и развязка."
    }

    for key, pr in prompts.items():
        print(f"   ∟ {key}...")
        res = chat.send_message(pr)
        episodes[key] = res.text
        time.sleep(10) # Пауза для лимитов

    # Сохраняем структуру сценария
    os.makedirs("data", exist_ok=True)
    with open("data/1_base_structure.json", "w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, indent=2)

    # 2. ЭКСТРАКТОР (анализирует ВСЁ для консистентности)
    print("👤 Создаем единые описания персонажей...")
    full_text = "\n\n".join(episodes.values())
    char_res = client.models.generate_content(
        model=model_id, 
        contents=full_text,
        config={'response_mime_type': 'application/json', 'system_instruction': extractor_sys}
    )
    
    with open("data/visual_config.json", "w", encoding="utf-8") as f:
        json.dump(json.loads(char_res.text), f, ensure_ascii=False, indent=2)

    print("✅ Stage 1 готов. Сценарий разделен на 3 части.")

if __name__ == "__main__":
    run_stage_1()