import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import openai
import base64

load_dotenv()


def run_stage_3(ai_settings=None, prompts=None):
    """
    Stage 3: Озвучка сцен с использованием TTS API
    Создает аудиофайлы для каждой сцены из production_map
    """
    print("🎙️ Stage 3: Начинаем озвучку сцен...")

    # 1. Настройки AI
    settings = load_settings()
    ai_voice = ai_settings["voice"] if ai_settings and "voice" in ai_settings else settings.get("ai_settings", {}).get("voice", {})
    
    api_url = ai_voice.get("api_url", "https://api.openai.com/v1")
    api_key = ai_voice.get("api_key", "")
    model = ai_voice.get("model", "tts-1-hd")
    voice = ai_voice.get("voice", "onyx")  # onyx - глубокий мужской голос
    
    if not api_key:
        print("❌ Ошибка: Не задан api_key для TTS")
        return False

    # Клиент OpenAI
    client = openai.OpenAI(api_key=api_key, base_url=api_url)

    # 2. Загрузка production_map
    try:
        with open("data/2_production_map.json", "r", encoding="utf-8") as f:
            production_map = json.load(f)
        
        episodes = production_map.get("episodes", {})
        
        if not episodes:
            print("❌ Нет эпизодов в production_map")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка загрузки production_map: {e}")
        return False

    # 3. Создаем директории для аудио
    audio_dir = Path("output/audio")
    audio_dir.mkdir(parents=True, exist_ok=True)

    # Словарь для хранения путей к аудиофайлам
    audio_paths = {"episodes": {}}
    total_scenes = 0
    processed_scenes = 0

    # 4. Цикл по эпизодам и сценам
    for ep_key, scenes in episodes.items():
        print(f"\n🎬 Озвучиваем {ep_key} ({len(scenes)} сцен)...")
        
        episode_dir = audio_dir / ep_key
        episode_dir.mkdir(exist_ok=True)
        
        audio_paths["episodes"][ep_key] = []
        total_scenes += len(scenes)

        for scene in scenes:
            scene_id = scene.get("scene_id", 0)
            audio_text = scene.get("audio_segment", "")
            
            if not audio_text:
                print(f"   ⚠️ Сцена {scene_id}: нет текста для озвучки")
                continue

            # Формируем имя файла
            audio_file = episode_dir / f"scene_{scene_id:03d}.mp3"
            
            try:
                # Генерация аудио через OpenAI TTS
                print(f"   🎤 Сцена {scene_id}: '{audio_text[:50]}...'")
                
                response = client.audio.speech.create(
                    model=model,
                    voice=voice,
                    input=audio_text,
                    speed=0.95  # Немного медленнее для драматичности
                )
                
                # Сохранение аудиофайла
                response.stream_to_file(str(audio_file))
                
                # Добавляем путь в мапу
                audio_paths["episodes"][ep_key].append({
                    "scene_id": scene_id,
                    "audio_path": str(audio_file),
                    "text": audio_text,
                    "duration_estimate": estimate_duration(audio_text)
                })
                
                processed_scenes += 1
                print(f"      ✓ Сохранено: {audio_file.name}")
                
                # Пауза между запросами
                time.sleep(0.5)
                
            except Exception as e:
                print(f"   ❌ Ошибка озвучки сцены {scene_id}: {e}")
                continue

    # 5. Сохранение мапы с путями к аудио
    audio_map_file = "data/3_audio_map.json"
    with open(audio_map_file, "w", encoding="utf-8") as f:
        json.dump(audio_paths, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Stage 3 завершен:")
    print(f"   📊 Обработано сцен: {processed_scenes}/{total_scenes}")
    print(f"   💾 Аудиофайлы: output/audio/")
    print(f"   📄 Карта аудио: {audio_map_file}")
    
    return True


def estimate_duration(text: str) -> float:
    """
    Примерная оценка длительности аудио в секундах
    На основе количества символов и средней скорости речи
    """
    # Средняя скорость: ~150 слов/мин или ~12-15 символов/сек для русского
    chars_per_second = 13
    duration = len(text) / chars_per_second
    return round(duration, 2)


def load_settings():
    """Загружает настройки из settings.json"""
    if os.path.exists("settings.json"):
        with open("settings.json", "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Дефолтные настройки
    return {
        "ai_settings": {
            "voice": {
                "api_url": "https://api.openai.com/v1",
                "api_key": "",
                "model": "tts-1-hd",  # или tts-1 для быстрой генерации
                "voice": "onyx",  # Глубокий мужской голос
                "provider": "openai"
            }
        }
    }


def test_voice_sample():
    """
    Тестовая функция для проверки голоса
    Создает короткий аудио-семпл
    """
    print("🎤 Тестируем голос...")
    
    settings = load_settings()
    ai_voice = settings.get("ai_settings", {}).get("voice", {})
    
    client = openai.OpenAI(
        api_key=ai_voice.get("api_key", ""),
        base_url=ai_voice.get("api_url", "https://api.openai.com/v1")
    )
    
    test_text = """В клубе «Врата» вышибала Виктор вершит суд с помощью монокля, 
    видящего грехи. Его голос звучит как приговор, от которого нет спасения."""
    
    try:
        response = client.audio.speech.create(
            model=ai_voice.get("model", "tts-1-hd"),
            voice=ai_voice.get("voice", "onyx"),
            input=test_text,
            speed=0.95
        )
        
        test_file = "output/voice_test.mp3"
        os.makedirs("output", exist_ok=True)
        response.stream_to_file(test_file)
        
        print(f"✅ Тестовый семпл сохранен: {test_file}")
        print(f"   Голос: {ai_voice.get('voice', 'onyx')}")
        print(f"   Модель: {ai_voice.get('model', 'tts-1-hd')}")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")


if __name__ == "__main__":
    # Раскомментируйте для тестирования голоса
    # test_voice_sample()
    
    run_stage_3()
