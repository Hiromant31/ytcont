import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import openai

load_dotenv()

def run_stage_1():
    print("🚀 Запуск Stage 1: Генерация истории через Gemma 3 (Yandex SDK API)...")

    # 1. Настройки из твоего примера
    YANDEX_CLOUD_FOLDER = os.getenv("YANDEX_FOLDER_ID")
    YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_API_KEY")
    YANDEX_CLOUD_MODEL = "gemma-3-27b-it/latest"
    
    if not YANDEX_CLOUD_API_KEY or not YANDEX_CLOUD_FOLDER:
        print("❌ Ошибка: Проверь YANDEX_API_KEY и YANDEX_FOLDER_ID в .env")
        return False

    # Инициализация клиента строго по инструкции
    client = openai.OpenAI(
        api_key=YANDEX_CLOUD_API_KEY,
        base_url="https://ai.api.cloud.yandex.net/v1",
        project=YANDEX_CLOUD_FOLDER
    )

    # 2. Загрузка промптов
    try:
        idea = Path("idea.txt").read_text(encoding="utf-8")
        writer_sys = Path("prompts/writer_instruction.txt").read_text(encoding="utf-8")
        extractor_sys = Path("prompts/extractor_instruction.txt").read_text(encoding="utf-8")
    except FileNotFoundError as e:
        print(f"❌ Ошибка: Не найден файл: {e}")
        return False

    # 3. ГЕНЕРАЦИЯ ЭПИЗОДОВ
    episodes = {}
    steps = {
        "episode_1": f"Напиши Эпизод 1: Завязка. Идея: {idea}",
        "episode_2": "Напиши Эпизод 2: Кульминация.",
        "episode_3": "Напиши Эпизод 3: Финал и развязка."
    }
    
    print("✍️ Пишем сценарий...")
    for key, user_input in steps.items():
        print(f"   ∟ {key}...")
        try:
            # Используем метод .responses.create как в твоем примере
            response = client.responses.create(
                model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
                temperature=0.7,
                instructions=writer_sys,
                input=user_input,
                max_output_tokens=2000
            )
            episodes[key] = response.output_text
            time.sleep(1) 
        except Exception as e:
            print(f"❌ Ошибка на {key}: {e}")
            return False

    # Сохранение сценария
    os.makedirs("data", exist_ok=True)
    with open("data/1_base_structure.json", "w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, indent=2)

    # 4. ЭКСТРАКТОР (JSON)
    print("👤 Извлекаем персонажей...")
    full_text = "\n\n".join(episodes.values())
    
    try:
        response = client.responses.create(
            model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
            temperature=0.2,
            instructions=extractor_sys,
            input=f"Analyze and return ONLY JSON:\n\n{full_text}",
            max_output_tokens=2000
        )
        
        raw_res = response.output_text.strip()
        
        # Очистка от возможных markdown-тегов
        if "```" in raw_res:
            raw_res = raw_res.split("```")[1].replace("json", "").strip()
            
        visual_config = json.loads(raw_res)
        
        with open("data/visual_config.json", "w", encoding="utf-8") as f:
            json.dump(visual_config, f, ensure_ascii=False, indent=2)
            
        print("✅ Stage 1 успешно завершен.")
        return True
    except Exception as e:
        print(f"❌ Ошибка экстрактора: {e}")
        return False

if __name__ == "__main__":
    run_stage_1()