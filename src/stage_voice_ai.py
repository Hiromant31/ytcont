
import os
import json
import time
import base64
import subprocess
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()


def generate_tts(
    text: str,
    output_file: str,
    api_key: str,
    model: str = "openai/gpt-audio-mini",
    voice: str = "onyx",
    speed: float = 0.95
):

    url = "https://routerai.ru/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Немного чистим текст
    clean_text = (
        text
        .replace("—", "...")
        .replace("«", "")
        .replace("»", "")
        .strip()
    )

    payload = {
        "model": model,
        "modalities": ["text", "audio"],
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты движок озвучки. " "Строго читай текст пользователя ДОСЛОВНО. " "Ничего не добавляй. " "Ничего не объясняй. " "Не продолжай мысль. " "Не интерпретируй текст. " "Не отвечай как ассистент. " "Только озвучь присланный текст."
"Голос низкий, медленный, тяжелый. "
                    "Читай атмосферно, с паузами, "
                )
            },
            {
                "role": "user",
                "content": ( "Озвучь дословно следующий текст. " "Не добавляй ничего.\n\n" f"{clean_text}" )
            }
        ],
        "audio": {
            "voice": voice,
            "format": "pcm16"
        },
        "temperature": 0,
        "stream": True
    }

    pcm_chunks = bytearray()

    try:

        with requests.post(
            url,
            headers=headers,
            json=payload,
            stream=True,
            timeout=120
        ) as r:

            r.raise_for_status()

            for raw_line in r.iter_lines(decode_unicode=True):

                if not raw_line:
                    continue

                if not raw_line.startswith("data: "):
                    continue

                data = raw_line[6:]

                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices", [])

                if not choices:
                    continue

                delta = choices[0].get("delta", {})

                audio = delta.get("audio", {})

                audio_b64 = audio.get("data")

                if audio_b64:
                    try:
                        pcm_chunks += base64.b64decode(audio_b64)
                    except Exception:
                        pass

        if not pcm_chunks:
            raise Exception("Пустой audio stream")

        temp_pcm = output_file.replace(".mp3", ".pcm")

        with open(temp_pcm, "wb") as f:
            f.write(pcm_chunks)

        # PCM -> MP3
        subprocess.run([
            "ffmpeg",
            "-y",
            "-f", "s16le",
            "-ar", "24000",
            "-ac", "1",
            "-i", temp_pcm,
            "-codec:a", "libmp3lame",
            "-q:a", "3",
            output_file
        ], check=True)

        os.remove(temp_pcm)

        return True

    except Exception as e:
        print(f"❌ Ошибка TTS: {e}")
        return False


def run_stage_3():

    print("🎙️ Stage 3: Озвучка сцен")

    settings = load_settings()

    voice_settings = settings["ai_settings"]["voice"]

    api_key = voice_settings["api_key"]
    model = voice_settings["model"]
    voice = voice_settings["voice"]
    speed = voice_settings.get("speed", 0.95)

    with open("data/2_production_map.json", "r", encoding="utf-8") as f:
        production_map = json.load(f)

    episodes = production_map.get("episodes", {})

    audio_root = Path("output/audio")
    audio_root.mkdir(parents=True, exist_ok=True)

    total = 0
    success = 0

    audio_map = {
        "episodes": {}
    }

    for ep_key, scenes in episodes.items():

        print(f"\n🎬 {ep_key} ({len(scenes)} сцен)")

        ep_dir = audio_root / ep_key
        ep_dir.mkdir(exist_ok=True)

        audio_map["episodes"][ep_key] = []

        for scene in scenes:

            total += 1

            scene_id = scene.get("scene_id")
            text = scene.get("audio_segment", "").strip()

            if not text:
                continue

            output_file = ep_dir / f"scene_{scene_id:03d}.mp3"

            print(f"   🎤 Сцена {scene_id}: {text[:60]}...")

            ok = generate_tts(
                text=text,
                output_file=str(output_file),
                api_key=api_key,
                model=model,
                voice=voice,
                speed=speed
            )

            if ok:

                success += 1

                audio_map["episodes"][ep_key].append({
                    "scene_id": scene_id,
                    "audio_path": str(output_file),
                    "text": text
                })

                print(f"      ✅ {output_file.name}")

            else:
                print(f"      ❌ FAIL")

            # Анти-rate-limit
            time.sleep(1.2)

    with open("data/3_audio_map.json", "w", encoding="utf-8") as f:
        json.dump(audio_map, f, ensure_ascii=False, indent=2)

    print("\n✅ Stage 3 завершен")
    print(f"📊 Успешно: {success}/{total}")


def load_settings():

    if os.path.exists("settings.json"):

        with open("settings.json", "r", encoding="utf-8") as f:
            return json.load(f)

    raise Exception("settings.json не найден")


if __name__ == "__main__":
    run_stage_3()


