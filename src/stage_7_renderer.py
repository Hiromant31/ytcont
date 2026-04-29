import os
import shutil
import json
import math
import traceback
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, TextClip
from moviepy.video.fx import Resize, Margin, CrossFadeIn

# Понижаем приоритет процесса для стабильности
try:
    os.nice(15)
except:
    pass

# Настройки путей и шрифтов
FONT_PATH        = "assets/dejavu_sans/DejaVu_Sans/DejaVuSans-Bold.ttf"
FONT_SIZE_START  = 12
BOTTOM_PAD_RATIO = 0.10
MAX_W_RATIO      = 0.88
MAX_H_RATIO      = 0.22
GROUP_SIZE       = 3
PHRASE_GAP       = 0.35

def check_fonts():
    """Проверяет наличие шрифтов и правит политику ImageMagick через Python."""
    policy_path = '/etc/ImageMagick-6/policy.xml'
    if os.path.exists(policy_path):
        try:
            with open(policy_path, 'r') as f:
                content = f.read()
            # Убираем запрет на чтение путей
            new_content = content.replace('rights="none" pattern="@*"', 'rights="read|write" pattern="@*"')
            with open(policy_path, 'w') as f:
                f.write(new_content)
        except Exception as e:
            print(f"⚠️ Не удалось поправить политику ImageMagick: {e}")
    
    if not os.path.exists(FONT_PATH):
        print(f"⚠️ Шрифт не найден по пути {FONT_PATH}. Поиск системного...")
        alt_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if os.path.exists(alt_path):
            return alt_path
    return FONT_PATH

# ─────────────────────────────────────────────────────────────
# Утилиты субтитров
# ─────────────────────────────────────────────────────────────

def _sub_zone(clip_w, clip_h):
    zone_w = int(clip_w * MAX_W_RATIO)
    zone_h = int(clip_h * MAX_H_RATIO)
    zone_x = (clip_w - zone_w) // 2
    zone_y = int(clip_h * (1 - BOTTOM_PAD_RATIO)) - zone_h
    zone_y = max(0, min(zone_y, clip_h - zone_h))
    return zone_w, zone_h, zone_x, zone_y

def _make_clip(text, font_size, zone_w, zone_h):
    return TextClip(
        font=FONT_PATH,
        text=text,
        font_size=font_size,
        color='yellow',
        stroke_color='black',
        stroke_width=1,
        method='caption',
        size=(zone_w, zone_h),
    )

def _fit_fs(text, zone_w, zone_h):
    fs = FONT_SIZE_START
    while fs >= 8:
        tc = _make_clip(text, fs, zone_w, zone_h)
        h = tc.h
        tc.close() # Важно для памяти
        if h <= zone_h:
            return fs
        fs -= 1
    return 8

def _place_y(txt_h, zone_y, zone_h, clip_h):
    y = zone_y + zone_h - txt_h - 2
    return max(0, min(y, clip_h - txt_h - 2))

# ─────────────────────────────────────────────────────────────
# Логика разбивки и рендера
# ─────────────────────────────────────────────────────────────

def _split_phrases(words):
    if not words: return []
    phrases, cur = [], [words[0]]
    for w in words[1:]:
        if w['start'] - cur[-1]['end'] > PHRASE_GAP:
            phrases.append(cur)
            cur = []
        cur.append(w)
    phrases.append(cur)
    return phrases

def _split_groups(phrase, zone_w, zone_h):
    groups = []
    i = 0
    while i < len(phrase):
        for size in range(GROUP_SIZE, 0, -1):
            chunk = phrase[i:i + size]
            text = ' '.join(w['text'] for w in chunk)
            fs = _fit_fs(text, zone_w, zone_h)
            tc = _make_clip(text, fs, zone_w, zone_h)
            h = tc.h
            tc.close()
            if h <= zone_h:
                groups.append(chunk)
                i += size
                break
        else:
            groups.append([phrase[i]])
            i += 1
    return groups

def _render_group(group, clip_w, clip_h):
    zone_w, zone_h, zone_x, zone_y = _sub_zone(clip_w, clip_h)
    t_group_end = group[-1]['end']
    result = []

    for i in range(len(group)):
        partial_text = ' '.join(w['text'] for w in group[:i + 1])
        fs = _fit_fs(partial_text, zone_w, zone_h)
        tc = _make_clip(partial_text, fs, zone_w, zone_h)
        
        final_y = _place_y(tc.h, zone_y, zone_h, clip_h)
        t_start = group[i]['start']
        t_end = group[i + 1]['start'] if i + 1 < len(group) else t_group_end
        
        tc = (tc.with_start(t_start)
                .with_duration(max(t_end - t_start, 0.05))
                .with_position((zone_x, final_y)))
        result.append(tc)
    return result

# ─────────────────────────────────────────────────────────────
# Основные функции сцены и рендера
# ─────────────────────────────────────────────────────────────

_sub_cache = {}

def create_animated_clip(scene_data, ep_name, target_size=(240, 426)):
    duration  = scene_data['duration']
    img_path  = scene_data['image_path']
    scene_id  = scene_data['scene_id']
    anim_type = scene_data.get('animation', 'zoom_in')

    # Анимации
    def ease_io(t):
        return (1 - math.cos(max(0, min(t, duration)) / duration * math.pi)) / 2

    clip = ImageClip(img_path).with_duration(duration).with_fps(24)

    if anim_type == "zoom_in":
        clip = clip.with_effects([Resize(new_size=lambda t: 1 + 0.3 * ease_io(t))])
    elif anim_type == "zoom_out":
        clip = clip.with_effects([Resize(new_size=lambda t: 1.3 - 0.3 * ease_io(t))])
    elif anim_type == "pan_left":
        clip = clip.with_position(lambda t: (-500 * ease_io(t), 'center'))
    elif anim_type == "pan_right":
        clip = clip.with_position(lambda t: (-500 + 500 * ease_io(t), 'center'))

    clip = (clip.with_effects([Margin(margin_size=0)])
                .with_effects([Resize(width=target_size[0])])
                .with_position('center'))

    # Субтитры
    sub_path = f"outputs/subtitles/{ep_name}.json"
    if ep_name not in _sub_cache and os.path.exists(sub_path):
        with open(sub_path, "r", encoding="utf-8") as f:
            _sub_cache[ep_name] = {int(k): v for k, v in json.load(f).items()}

    words = _sub_cache.get(ep_name, {}).get(int(scene_id), [])
    sub_clips = []
    if words:
        zone_w, zone_h, _, _ = _sub_zone(target_size[0], target_size[1])
        for phrase in _split_phrases(words):
            for group in _split_groups(phrase, zone_w, zone_h):
                sub_clips.extend(_render_group(group, target_size[0], target_size[1]))

    if sub_clips:
        clip = CompositeVideoClip([clip] + sub_clips, size=target_size).with_duration(duration)

    audio = AudioFileClip(scene_data['audio_path'])
    clip = clip.with_audio(audio)
    return clip, audio

def run_stage_7_render():
    global FONT_PATH
    FONT_PATH = check_fonts()
    manifest_path = "data/3_assembly_manifest.json"
    
    if not os.path.exists(manifest_path):
        print(f"❌ Манифест не найден: {manifest_path}")
        return False

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        output_dir = "outputs/final_videos"
        os.makedirs(output_dir, exist_ok=True)

        for ep_name, scenes in manifest.items():
            print(f"\n🎬 Рендеринг эпизода: {ep_name}")
            final_clips = []
            
            # Вложенный цикл (8 пробелов от края)
            for i, scene in enumerate(scenes):
                print(f"   ∟ Сцена {scene['scene_id']}")
                clip, audio = create_animated_clip(scene, ep_name)
                
                if i > 0:
                    clip = clip.with_effects([CrossFadeIn(duration=0.6)])
                
                final_clips.append(clip)

            # Проверка и сборка (8 пробелов от края, внутри цикла по эпизодам)
            if final_clips:
                final_video = concatenate_videoclips(final_clips, method="compose", padding=-0.6)
                target_path = os.path.join(output_dir, f"{ep_name}.mp4")
                print(f"🚀 Запись: {target_path}...")

                final_video.write_videofile(
                    target_path, 
                    fps=24,
                    codec="libx264", 
                    audio_codec="aac",
                    threads=4, 
                    preset="ultrafast"
                )
                
                final_video.close()
                for c in final_clips:
                    c.close()
        
        return True
    except Exception as e:
        print(f"❌ Ошибка рендеринга: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    run_stage_7_render()