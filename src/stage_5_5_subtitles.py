import os
import json
import re
import whisper


def run_stage_5_5_subtitles():
    print("⏳ Загрузка модели Whisper (base)...")
    model = whisper.load_model("base")

    audio_root = "outputs/audio"
    sub_root   = "outputs/subtitles"

    if not os.path.exists(audio_root):
        print(f"❌ Папка с аудио не найдена: {audio_root}")
        return

    episodes = sorted([
        d for d in os.listdir(audio_root)
        if os.path.isdir(os.path.join(audio_root, d))
    ])

    for ep in episodes:
        print(f"\n✍️  Обработка субтитров для: {ep}")
        ep_audio_path = os.path.join(audio_root, ep)
        os.makedirs(sub_root, exist_ok=True)

        audio_files = sorted(
            [f for f in os.listdir(ep_audio_path) if f.endswith((".mp3", ".wav"))],
            # Сортируем по числу в имени файла, а не лексикографически
            key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0
        )

        episode_subs = {}

        for af in audio_files:
            # Берём только первое число из имени файла через re,
            # а не все цифры подряд — иначе "scene_13.mp3" даёт "13" вместо "1"
            # (здесь мы хотим именно полный номер сцены как он есть в имени файла)
            m = re.search(r'\d+', af)
            if not m:
                print(f"   ⚠️  Не удалось определить scene_id из имени: {af}")
                continue

            scene_id = int(m.group())

            # Защита от дублей: если scene_id уже есть — пропускаем
            if scene_id in episode_subs:
                print(f"   ⚠️  scene_id={scene_id} уже обработан (дубль {af}), пропуск")
                continue

            audio_full_path = os.path.join(ep_audio_path, af)
            print(f"   ∟ Распознавание сцены {scene_id} ({af})...")

            result = model.transcribe(
                audio_full_path,
                language="ru",
                task="transcribe",
                word_timestamps=True
            )

            words = []
            for segment in result["segments"]:
                for w in segment.get("words", []):
                    word  = w["word"].strip()
                    clean = re.sub(r"[^\wА-Яа-яЁёa-zA-Z0-9]", "", word)
                    if not clean:
                        continue
                    words.append({
                        "start": round(w["start"], 3),
                        "end":   round(w["end"],   3),
                        "text":  clean.upper()
                    })

            episode_subs[scene_id] = words
            print(f"      → {len(words)} слов, t={words[0]['start']:.2f}–{words[-1]['end']:.2f}s" if words else "      → 0 слов")

        out_path = os.path.join(sub_root, f"{ep}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(episode_subs, f, ensure_ascii=False, indent=2)

        total_words = sum(len(v) for v in episode_subs.values())
        print(f"   ✅ {len(episode_subs)} сцен, {total_words} слов → {out_path}")

    print("\n🎉 Все субтитры сгенерированы!")


if __name__ == "__main__":
    run_stage_5_5_subtitles()