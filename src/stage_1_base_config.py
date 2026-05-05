import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

def run_extraction():
    # Настройка прокси
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:10809"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10809"

    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    
    # Читаем исходники
    try:
        with open("data/story_draft.txt", "r", encoding="utf-8") as f:
            story = f.read()
        with open("prompts/extractor_instruction.txt", "r", encoding="utf-8") as f:
            instruction = f.read()
    except FileNotFoundError as e:
        print(f"❌ Файл не найден: {e.filename}")
        return

    print("🔍 Анализ сценария и формирование базы...")

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=f"Сценарий:\n{story}",
            config={
                'response_mime_type': 'application/json',
                'system_instruction': instruction
            }
        )
        
        # Получаем чистый результат
        result = json.loads(response.text)

        # Нормализация: гарантируем, что result - это словарь с ключом "characters"
        if isinstance(result, list):
            # Если нейросеть вернула список, оборачиваем его
            result = {"characters": result}
        elif not isinstance(result, dict):
            # Если вообще не словарь и не список, создаем пустую структуру
            result = {"characters": {}}
        elif "characters" not in result:
            # Если словарь есть, но ключа "characters" нет, добавляем его
            # Предполагаем, что весь ответ - это и есть данные персонажей, если структура плоская
            # Но лучше оставить как есть, если там другая структура, или создать пустой список
            result["characters"] = {}

        # Сохраняем в один файл
        os.makedirs("data", exist_ok=True)
        with open("data/visual_config.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print("✅ Готово. Результат в data/visual_config.json")
        print(f"👥 Найдено персонажей: {len(result['characters'])}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    run_extraction()