import os
import json
import math
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
from moviepy.video.fx import Resize, Margin, CrossFadeIn

# Снижаем приоритет процесса — аналог запуска через nice -n 15
os.nice(15)


def create_animated_clip(scene_data, target_size=(1080, 1920)):
    """
    Создаёт клип с плавным движением (Ease In-Out) для MoviePy 2.x
    """
    duration = scene_data['duration']
    img_path = scene_data['image_path']
    anim_type = scene_data.get('animation', 'zoom_in')

    zoom_scale = 0.15
    pan_distance = 120

    def ease_io(t):
        t_c = max(0.0, min(t, duration))
        return (1 - math.cos(t_c / duration * math.pi)) / 2

    # 1. Загружаем изображение
    clip = ImageClip(img_path).with_duration(duration).with_fps(24)

    # 2. Применяем анимацию
    # В v2.x with_effects([Effect(...)]) заменяет applied_fx(Effect, ...)
    if anim_type == "zoom_in":
        clip = clip.with_effects([
            Resize(new_size=lambda t: 1 + zoom_scale * ease_io(t))
        ])

    elif anim_type == "zoom_out":
        clip = clip.with_effects([
            Resize(new_size=lambda t: (1 + zoom_scale) - zoom_scale * ease_io(t))
        ])

    elif anim_type == "pan_left":
        clip = clip.with_position(lambda t: (-pan_distance * ease_io(t), 'center'))

    elif anim_type == "pan_right":
        clip = clip.with_position(
            lambda t: (-pan_distance + pan_distance * ease_io(t), 'center')
        )

    # 3. Добавляем поля, подгоняем под ширину и центрируем
    clip = (clip
            .with_effects([Margin(margin_size=60)])
            .with_effects([Resize(width=target_size[0])])
            .with_position('center'))

    # 4. Добавляем звук
    audio = AudioFileClip(scene_data['audio_path'])
    clip = clip.with_audio(audio)

    # Возвращаем аудио отдельно, чтобы закрыть его после рендера
    return clip, audio


def run_stage_7_render():
    manifest_path = "data/3_assembly_manifest.json"
    if not os.path.exists(manifest_path):
        print(f"❌ Манифест не найден: {manifest_path}")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    output_dir = "outputs/final_videos"
    os.makedirs(output_dir, exist_ok=True)

    for ep_name, scenes in manifest.items():
        print(f"\n🎬 Рендеринг эпизода: {ep_name}")
        final_clips = []
        audio_refs = []  # Держим ссылки, чтобы закрыть после рендера

        for i, scene in enumerate(scenes):
            print(f"   ∟ Обработка сцены {scene['scene_id']} [{scene['animation']}]")
            clip, audio = create_animated_clip(scene)
            audio_refs.append(audio)

            # В v2.x кроссфейд применяется через with_effects([CrossFadeIn(...)])
            if i > 0:
                clip = clip.with_effects([CrossFadeIn(duration=0.6)])

            final_clips.append(clip)

        # padding=-0.6 создаёт нахлёст для плавных переходов
        final_video = concatenate_videoclips(
            final_clips, method="compose", padding=-0.6
        )

        target_path = os.path.join(output_dir, f"{ep_name}.mp4")
        print(f"🚀 Запись файла: {target_path}...")

        final_video.write_videofile(
            target_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            threads=2    # MacBook Pro 2012 — 2 физических ядра, 4 вешает систему
            
        )
        print(f"✅ Эпизод {ep_name} готов!")

        # Явно освобождаем память после каждого эпизода
        final_video.close()
        for clip in final_clips:
            clip.close()
        for audio in audio_refs:
            audio.close()
        final_clips.clear()
        audio_refs.clear()


if __name__ == "__main__":
    run_stage_7_render()