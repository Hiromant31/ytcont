import os
import json
from dotenv import load_dotenv
from google import genai

# Загружаем переменные из .env
load_dotenv()

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_stage_2():
    # --- НАСТРОЙКА ПРОКСИ ---
    # Убедись, что твой прокси-клиент (например, v2ray или Nekoray) запущен на этом порту
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:10809"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10809"
    
    api_key = os.getenv("GEMINI_API_KEY")
    
    # Инициализация клиента
    client = genai.Client(
        api_key=api_key, 
        http_options={'api_version': 'v1beta'}
    )
    
    # Загружаем данные первого этапа и инструкцию
    try:
        base_data = load_json("data/1_base_structure.json")
        with open("prompts/stage_2_scenes.txt", "r", encoding="utf-8") as f:
            system_instruction = f.read()
    except FileNotFoundError as e:
        print(f"❌ Ошибка: Не найден файл {e.filename}")
        return
    except json.JSONDecodeError:
        print("❌ Ошибка: Файл data/1_base_structure.json поврежден или пуст.")
        return

    print("🎬 Начинаю техническую раскадровку...")

    try:
        # Используем gemini-3.1-flash-lite-preview для экономии и скорости
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=f"Данные проекта: {json.dumps(base_data, ensure_ascii=False)}",
            config={
                'response_mime_type': 'application/json',
                'system_instruction': system_instruction
            }
        )
        
        # Парсим ответ
        scenes_data = json.loads(response.text)
        
        # ГИБКАЯ СБОРКА: 
        # Если нейросеть вернула список сцен прямо в корне, или внутри ключа "scenes"
        scenes_list = scenes_data.get("scenes", []) if isinstance(scenes_data, dict) else scenes_data

        final_production_map = {
            "visual_pack": base_data.get("visual_pack", {}), 
            "production_scenes": scenes_list
        }

        # Сохранение результата
        os.makedirs("data", exist_ok=True)
        with open("data/2_production_map.json", "w", encoding="utf-8") as f:
            json.dump(final_production_map, f, ensure_ascii=False, indent=2)

        print(f"✅ Этап 2 завершен. Создано сцен: {len(scenes_list)}")
        print("Файл data/2_production_map.json готов.")

    except Exception as e:
        print(f"❌ Ошибка при генерации или парсинге JSON: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print("Ответ от модели был:", response.text)

if __name__ == "__main__":
    run_stage_2()