import os
import json
import pathlib
import time
import requests
from dotenv import load_dotenv

load_dotenv()

def synthesize_speech(text, output_path, folder_id, api_key):
    """Функция запроса к Yandex SpeechKit API v1"""
    url = 'https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize'
    
    headers = {
        'Authorization': f'Api-Key {api_key}',
    }
    
    data = {
        'text': text,
        'lang': 'ru-RU',
        'voice': 'ermil', # Глубокий мужской голос. Альтернатива: 'madirus'
        'emotion': 'neutral', # Мрачный/драматичный окрас
        'speed': '1.1',
        'format': 'mp3',
        'folderId': folder_id # Обязательно для некоторых типов аккаунтов
    }

    with requests.post(url, headers=headers, data=data, stream=True) as resp:
        if resp.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=None):
                    f.write(chunk)
            return True
        else:
            print(f"❌ Ошибка SpeechKit: {resp.status_code}, {resp.text}")
            return False

def run_stage_5_yandex_tts():
    # ПРИНУДИТЕЛЬНАЯ ОЧИСТКА ПРОКСИ (для работы в Google Colab)
    for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        os.environ.pop(var, None)

    api_key = os.getenv("YANDEX_API_KEY")
    folder_id = os.getenv("YANDEX_FOLDER_ID")
    
    if not api_key:
        print("❌ Ошибка: YANDEX_API_KEY не найден в .env")
        return

    # Загружаем карту сцен
    try:
        with open("data/2_production_map.json", "r", encoding="utf-8") as f:
            production_map = json.load(f)
    except FileNotFoundError:
        print("❌ Ошибка: Файл data/2_production_map.json не найден.")
        return

    episodes = production_map.get("episodes", {})

    print(f"🎙️ Запуск Yandex SpeechKit для {len(episodes)} эпизодов...")

    for ep_name, scenes in episodes.items():
        print(f"\n📢 Озвучка: {ep_name}")
        audio_folder = pathlib.Path(f"outputs/audio/{ep_name}")
        audio_folder.mkdir(parents=True, exist_ok=True)

        for scene in scenes:
            scene_id = scene.get("scene_id")
            text = scene.get("audio_segment")
            
            if not text:
                continue

            target_file = audio_folder / f"scene_{scene_id}.mp3"
            print(f"   ∟ Сцена {scene_id} ({len(text)} симв.)...")

            try:
                success = synthesize_speech(text, target_file, folder_id, api_key)
                if success:
                    print(f"      ✅ Сохранено")
                
                # Небольшая пауза между запросами (соблюдаем лимиты SpeechKit)
                time.sleep(0.5)

            except Exception as e:
                print(f"   ❌ Ошибка в сцене {scene_id}: {e}")

    print("\n🎉 Озвучка от Яндекса завершена! Файлы в outputs/audio/")

if __name__ == "__main__":
    run_stage_5_yandex_tts()