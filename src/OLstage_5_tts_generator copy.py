import os
import json
import pathlib
import struct
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ GOOGLE ---

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
    bits_per_sample = params["bits_per_sample"]
    sample_rate = params["rate"]
    num_channels = 1
    data_size = len(audio_data)
    block_align = num_channels * (bits_per_sample // 8)
    byte_rate = sample_rate * block_align
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE", b"fmt ", 16, 1,
        num_channels, sample_rate, byte_rate, block_align, bits_per_sample,
        b"data", data_size
    )
    return header + audio_data

# --- ОСНОВНАЯ ЛОГИКА ---

def run_tts_test():
    # Настройка прокси (если нужно)
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:10809"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10809"

    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    
    base_path = pathlib.Path(__file__).parent.parent
    json_path = base_path / "data" / "2_production_map.json"
    
    with open(json_path, "r", encoding="utf-8") as f:
        p_map = json.load(f)

    # БЕРЕМ ТОЛЬКО ПЕРВЫЕ 2 СЦЕНЫ ДЛЯ ТЕСТА
    scenes = p_map.get("production_scenes", [])[:2]
    os.makedirs(base_path / "outputs" / "audio", exist_ok=True)

    print(f"🚀 ТЕСТОВЫЙ ЗАПУСК: Озвучка первых {len(scenes)} сцен (БЕЗ ЛИМИТОВ)...")

    for scene in scenes:
        scene_id = scene.get("scene_id")
        text = scene.get("audio_segment")
        if not text: continue

        target_file = base_path / "outputs" / "audio" / f"scene_{scene_id}.wav"
        
        # Удаляем старый файл, если он был, чтобы точно проверить новую генерацию
        if target_file.exists():
            target_file.unlink()

        print(f"🎙️ Генерация (WAV Stream): Сцена {scene_id}...")
        full_audio_data = b""
        current_mime = "audio/L16;rate=24000"

        try:
            config = types.GenerateContentConfig(
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Alnilam"
                        )
                    )
                )
            )

            # Потоковая генерация без искусственных пауз
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
                print(f"✅ Готово: {target_file.name}")

        except Exception as e:
            print(f"❌ Ошибка в сцене {scene_id}: {e}")

    print("\n🎉 Тестовая озвучка завершена. Проверяй outputs/audio/")

if __name__ == "__main__":
    run_tts_test()