import os
import json
import time
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# Загружаем переменные окружения (HF_TOKEN)
load_dotenv()

def run_stage_3_ref():
    # Настройка прокси (убедись, что твой прокси-клиент запущен на этом порту)
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:10809"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10809"

    # Инициализация клиента
    # Убедись, что в .env файле есть переменная HF_TOKEN
    token = os.getenv("HF_TOKEN")
    if not token:
        print("❌ Ошибка: HF_TOKEN не найден в .env файле")
        return

    client = InferenceClient(api_key=token)
    
    # Модель FLUX.1-dev (требует Pro аккаунт или может быть лимит)
    # Если будет ошибка 403/429, можно заменить на "black-forest-labs/FLUX.1-schnell"
    MODEL_ID = "black-forest-labs/FLUX.1-dev"

    # --- ТЕСТОВАЯ ЗАГЛУШКА ВМЕСТО JSON ---
    print("🛠 Режим теста: использую встроенные описания персонажей...")
    entities = {
        "cyber_samurai": "Cybernetic samurai in neon-lit chrome armor, holding a plasma katana",
        "witch_astrologist": "Young witch in a starry cloak, surrounded by floating crystal orbs"
    }
    style = "Highly detailed digital illustration, concept art, cinematic lighting, 8k resolution"
    # -------------------------------------

    os.makedirs("outputs/references", exist_ok=True)

    print(f"🧬 Генерирую референсы персонажей через {MODEL_ID}...")

    for key, description in entities.items():
        print(f"👤 Создаю эталон для: {key}")
        
        # Промпт для чистого листа персонажа (Character Sheet)
        prompt = (
            f"Character sheet of {description}. "
            f"Full body, multiple views: front view, side view, and back view. "
            f"Simple neutral solid background. Style: {style}"
        )

        try:
            # Генерация изображения
            image = client.text_to_image(
                prompt=prompt,
                model=MODEL_ID
            )
            
            filename = f"outputs/references/{key}_ref.png"
            image.save(filename)
            print(f"✅ Успешно сохранено: {filename}")
            
            # Небольшая пауза между запросами, чтобы API не ругалось
            time.sleep(2)

        except Exception as e:
            print(f"❌ Ошибка при генерации {key}: {e}")
            if "401" in str(e):
                print("   Подсказка: Проверь правильность HF_TOKEN.")
            elif "503" in str(e):
                print("   Подсказка: Модель загружается, попробуй запустить снова через минуту.")

if __name__ == "__main__":
    run_stage_3_ref()
