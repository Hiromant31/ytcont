import os
import json
from dotenv import load_dotenv
from google import genai

# Загружаем переменные из .env (API ключ)
load_dotenv()

def load_file(path):
    """Вспомогательная функция для чтения файлов"""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def run_stage_1():
    # --- НАСТРОЙКА ПРОКСИ ---
    # Поскольку библиотека не принимает proxy в аргументах, задаем через окружение
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:10809"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10809"
    
    api_key = os.getenv("GEMINI_API_KEY")
    
    # Инициализация клиента (без параметра proxy, подхватит из os.environ)
    client = genai.Client(
        api_key=api_key, 
        http_options={'api_version': 'v1beta'}
    )
    
    # Используем актуальную и быструю модель 2.0 Flash
    model_id = "gemini-3.1-flash-lite-preview" 

    # Загружаем инструкции из файлов
    try:
        idea = load_file("idea.txt")
        writer_system = load_file("prompts/writer_instruction.txt")
        structurer_system = load_file("prompts/structurer_instruction.txt")
    except FileNotFoundError as e:
        print(f"❌ Ошибка: Не найден файл {e.filename}. Проверь структуру папок.")
        return

    # --- ЧАСТЬ 1: ПИСАТЕЛЬ (Генерация текста) ---
    print("✍️ Начинаем написание сценария по актам...")
    
    chat = client.chats.create(model=model_id, config={'system_instruction': writer_system})
    
    episodes_text = []
    prompts_sequence = [
        f"Напиши Эпизод 1 (Завязка) на основе идеи: {idea}",
        "Теперь напиши Эпизод 2 (Кульминация). Продолжай историю.",
        "И финальный Эпизод 3 (Развязка). Заверши историю."
    ]

    for i, prompt in enumerate(prompts_sequence):
        print(f"🎬 Генерирую текст эпизода {i+1}...")
        try:
            response = chat.send_message(prompt)
            episodes_text.append(response.text)
        except Exception as e:
            print(f"❌ Ошибка при генерации эпизода {i+1}: {e}")
            return

    full_story_draft = "\n\n=== NEXT EPISODE ===\n\n".join(episodes_text)
    
    os.makedirs("data", exist_ok=True)
    with open("data/story_draft.txt", "w", encoding="utf-8") as f:
        f.write(full_story_draft)

    # --- ЧАСТЬ 2: СТРУКТУРАТОР (Конвертация в JSON) ---
    print("🧬 Упаковываю сценарий в JSON формат...")
    
    try:
        struct_response = client.models.generate_content(
            model=model_id, 
            contents=f"Текст сценария:\n{full_story_draft}",
            config={
                'response_mime_type': 'application/json',
                'system_instruction': structurer_system # Исправлено имя переменной
            }
        )

        final_data = json.loads(struct_response.text)
        with open("data/1_base_structure.json", "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)

        print("✅ Этап 1 завершен. Созданы story_draft.txt и 1_base_structure.json")
        
    except Exception as e:
        print(f"❌ Ошибка на этапе структурирования: {e}")

if __name__ == "__main__":
    run_stage_1()
