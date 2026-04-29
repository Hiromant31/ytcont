import os
import json
import pathlib
import struct
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ КОНВЕРТАЦИИ ---

def parse_audio_mime_type(mime_type: str) -> dict:
    bits_per_sample = 16
    rate = 24000
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip().lower()
        if param.startswith("rate="):
            try: rate = int(param.split("=", 1)[1])
            except: pass
        elif "audio/l" in param:
            try: bits_per_sample = int(param.split("l", 1)[1])
            except: pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    params = parse_audio_mime_type(mime_type)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(audio_data), b"WAVE", b"fmt ", 16, 1,
        1, params["rate"], params["rate"] * (params["bits_per_sample"] // 8),
        params["bits_per_sample"] // 8, params["bits_per_sample"],
        b"data", len(audio_data)
    )
    return header + audio_data

# --- ОСНОВНАЯ ЛОГИКА ---

def run_stage_5_tts():
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:10809"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10809"

    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    
    # Загружаем карту продакшена
    try:
        with open("data/2_production_map.json", "r", encoding="utf-8") as f:
            production_map = json.load(f)
    except FileNotFoundError:
        print("❌ Ошибка: Файл data/2_production_map.json не найден.")
        return

    episodes = production_map.get("episodes", {})
    
    # Конфигурация голоса
    # Рекомендую "Charon" для мрачной атмосферы или "Aoede" для таинственной женской
    voice_name = "Charon" 

    print(f"🎙️ Начинаю озвучку для {len(episodes)} эпизодов голосом {voice_name}...")

    for ep_name, scenes in episodes.items():
        print(f"\n📢 Озвучка: {ep_name}")
        audio_folder = pathlib.Path(f"outputs/audio/{ep_name}")
        audio_folder.mkdir(parents=True, exist_ok=True)

        for scene in scenes:
            scene_id = scene.get("scene_id")
            text = scene.get("audio_segment")
            
            if not text:
                continue

            target_file = audio_folder / f"scene_{scene_id}.wav"
            print(f"   ∟ Сцена {scene_id}...")

            full_audio_data = b""
            current_mime = "audio/L16;rate=24000"

            try:
                config = types.GenerateContentConfig(
                    response_modalities=["audio"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name
                            )
                        )
                    )
                )

                # Используем gemini-2.0-flash (она стабильнее и поддерживает аудио)
                for chunk in client.models.generate_content_stream(
                    model="gemini-2.5-flash-preview-tts",
                    contents=text,
                    config=config,
                ):
                    if chunk.parts:
                        for part in chunk.parts:
                            if part.inline_data:
                                full_audio_data += part.inline_data.data
                                current_mime = part.inline_data.mime_type

                if full_audio_data:
                    wav_data = convert_to_wav(full_audio_data, current_mime)
                    target_file.write_bytes(wav_data)
                
                # Пауза, чтобы не поймать 429 Resource Exhausted
                time.sleep(5)

            except Exception as e:
                print(f"   ❌ Ошибка в сцене {scene_id}: {e}")
                time.sleep(10) # Увеличиваем паузу при ошибке

    print("\n🎉 Озвучка всех эпизодов завершена! Файлы в outputs/audio/")

if __name__ == "__main__":
    run_stage_5_tts()