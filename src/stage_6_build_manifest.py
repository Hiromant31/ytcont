import os
import json
import random
from mutagen.mp3 import MP3

# Длительность кроссфейда между сценами (в секундах).
# Должна совпадать с CROSSFADE_DURATION в stage_7_render.py
CROSSFADE_DURATION = 0.8


def get_audio_duration(file_path):
    """Определяет длительность MP3 файла в секундах"""
    try:
        audio = MP3(file_path)
        return audio.info.length
    except Exception as e:
        print(f"⚠️ Ошибка чтения длительности {file_path}: {e}")
        return 0


# ---------------------------------------------------------------------------
# Правила преемственности движения (Match Cut / Match Move)
#
# Логика основана на реальных принципах монтажа:
#   - Pan → следующий кадр продолжает движение в ту же сторону или плавно
#     переходит в zoom (зритель не теряет «инерцию» взгляда)
#   - Zoom In → нарастание; следующий кадр либо продолжает нарастание,
#     либо делает pan в любую сторону (смена вектора, но не резкая)
#   - Zoom Out → расслабление; следующий кадр либо продолжает отдаление,
#     либо pan (не начинать zoom_in сразу — это ритмический конфликт)
#
# Веса в списках отражают вероятность: чем чаще элемент, тем вероятнее выбор.
# ---------------------------------------------------------------------------
ANIMATION_TRANSITIONS = {
    "zoom_in":   ["zoom_in", "zoom_in", "pan_right", "pan_left"],
    "zoom_out":  ["zoom_out", "zoom_out", "pan_left", "pan_right"],
    "pan_left":  ["pan_left", "pan_left", "zoom_in", "zoom_out"],
    "pan_right": ["pan_right", "pan_right", "zoom_in", "zoom_out"],
}

# Тип перехода зависит от пары анимаций: одинаковое движение → crossfade,
# смена вектора (zoom↔pan) → fade (менее заметный разрыв)
def get_transition(prev_anim, curr_anim):
    same_family = (
        ("zoom" in prev_anim and "zoom" in curr_anim) or
        (prev_anim == curr_anim)
    )
    return "crossfade" if same_family else "fade"


def get_next_animation(prev_anim):
    options = ANIMATION_TRANSITIONS.get(prev_anim, ["zoom_in", "pan_left"])
    return random.choice(options)


def run_stage_6_manifest():
    scenes_root = "outputs/scenes"
    audio_root  = "outputs/audio"

    if not os.path.exists(scenes_root):
        print(f"❌ Папка со сценами не найдена: {scenes_root}")
        return

    episodes = sorted(
        [d for d in os.listdir(scenes_root) if os.path.isdir(os.path.join(scenes_root, d))]
    )

    assembly_manifest = {}

    for ep in episodes:
        print(f"📦 Обработка {ep}...")
        ep_scenes = []

        ep_scenes_path = os.path.join(scenes_root, ep)
        ep_audio_path  = os.path.join(audio_root, ep)

        image_files = sorted(
            [f for f in os.listdir(ep_scenes_path) if f.lower().endswith(('.jpeg', '.jpg', '.png'))],
            key=lambda x: int(''.join(filter(str.isdigit, x)) or 0)
        )

        last_anim = random.choice(["zoom_in", "pan_right"])  # случайный старт

        for img_name in image_files:
            scene_id  = ''.join(filter(str.isdigit, img_name))
            audio_file = os.path.join(ep_audio_path, f"scene_{scene_id}.mp3")

            if not os.path.exists(audio_file):
                print(f"  ⚠️ Пропуск: аудио не найдено → {audio_file}")
                continue

            raw_duration = get_audio_duration(audio_file)
            if raw_duration == 0:
                continue

            current_anim = get_next_animation(last_anim)
            transition   = get_transition(last_anim, current_anim)

            # Добавляем половину кроссфейда к длительности с каждой стороны,
            # чтобы переход перекрывал тишину между фразами, а не саму речь.
            # Первая сцена получает только правый запас (нет левого соседа),
            # остальные — полный запас с обеих сторон.
            padded_duration = round(raw_duration + CROSSFADE_DURATION, 3)

            ep_scenes.append({
                "scene_id":    int(scene_id),
                "image_path":  os.path.abspath(os.path.join(ep_scenes_path, img_name)),
                "audio_path":  os.path.abspath(audio_file),
                "duration":    padded_duration,
                "raw_duration": round(raw_duration, 3),
                "animation":   current_anim,
                "transition":  transition,
            })

            last_anim = current_anim

        if ep_scenes:
            assembly_manifest[ep] = ep_scenes
            print(f"  ✅ Собрано {len(ep_scenes)} сцен для {ep}")

    os.makedirs("data", exist_ok=True)
    out_path = "data/3_assembly_manifest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(assembly_manifest, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Манифест готов: {out_path}")


if __name__ == "__main__":
    run_stage_6_manifest()