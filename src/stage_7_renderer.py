import os
import shutil
import json
import math
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, TextClip
from moviepy.video.fx import Resize, Margin, CrossFadeIn

os.nice(15)

FONT_PATH        = "assets/dejavu_sans/DejaVu_Sans/DejaVuSans-Bold.ttf"
FONT_SIZE_START  = 12        # начальный размер шрифта (уменьшается если не влезает)
BOTTOM_PAD_RATIO = 0.10      # отступ снизу = 10% высоты кадра
MAX_W_RATIO      = 0.88      # ширина зоны субтитров
MAX_H_RATIO      = 0.22      # высота зоны субтитров
GROUP_SIZE       = 3         # максимум слов в одной группе
PHRASE_GAP       = 0.35      # пауза между словами для разбивки на фразы (сек)

def check_fonts():
    """Проверяет наличие шрифтов, критично для Colab."""
    if not os.path.exists(FONT_PATH):
        print(f"⚠️ Шрифт не найден по пути {FONT_PATH}. Попытка поиска в системе...")
        # Если на Гитхабе забыли папку, это спасет рендер
        alt_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if os.path.exists(alt_path):
            return alt_path
    return FONT_PATH

# ─────────────────────────────────────────────────────────────
# Утилиты зоны и шрифта
# ─────────────────────────────────────────────────────────────

def _sub_zone(clip_w, clip_h):
    """Прямоугольник зоны субтитров: (zone_w, zone_h, zone_x, zone_y)."""
    zone_w = int(clip_w * MAX_W_RATIO)
    zone_h = int(clip_h * MAX_H_RATIO)
    zone_x = (clip_w - zone_w) // 2
    zone_y = int(clip_h * (1 - BOTTOM_PAD_RATIO)) - zone_h
    zone_y = max(0, min(zone_y, clip_h - zone_h))
    return zone_w, zone_h, zone_x, zone_y


def _make_clip(text, font_size, zone_w, zone_h):
    """
    Создаёт TextClip: только жёлтый текст, тонкая чёрная обводка.
    Никаких подложек, теней, bg_color — чистый текст поверх видео.
    size явный с обеих сторон — MoviePy не выйдет за холст.
    """
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
    """Подбирает шрифт начиная с FONT_SIZE_START, уменьшает пока не влезет."""
    fs = FONT_SIZE_START
    while fs >= 8:
        tc = _make_clip(text, fs, zone_w, zone_h)
        if tc.h <= zone_h:
            return fs
        fs -= 1
    return 8


def _place_y(txt_h, zone_y, zone_h, clip_h):
    """Вертикальная позиция: низ зоны, clamp чтобы не выйти за кадр."""
    y = zone_y + zone_h - txt_h - 2
    return max(0, min(y, clip_h - txt_h - 2))


# ─────────────────────────────────────────────────────────────
# Разбивка слов
# ─────────────────────────────────────────────────────────────

def _split_phrases(words):
    """Разбивает список слов на фразы по паузам > PHRASE_GAP сек."""
    if not words:
        return []
    phrases, cur = [], [words[0]]
    for w in words[1:]:
        if w['start'] - cur[-1]['end'] > PHRASE_GAP:
            phrases.append(cur)
            cur = []
        cur.append(w)
    phrases.append(cur)
    return phrases


def _split_groups(phrase, zone_w, zone_h):
    """
    Внутри фразы формирует группы до GROUP_SIZE слов.
    Проверяет: если все слова группы влезают в одну строку zone_w —
    оставляем GROUP_SIZE, иначе уменьшаем группу до тех пор пока влезет.
    Возвращает список групп: каждая группа = список слов.
    """
    groups = []
    i = 0
    while i < len(phrase):
        # Пробуем взять GROUP_SIZE слов, уменьшаем если не влезают
        for size in range(GROUP_SIZE, 0, -1):
            chunk = phrase[i:i + size]
            text  = ' '.join(w['text'] for w in chunk)
            fs    = _fit_fs(text, zone_w, zone_h)
            tc    = _make_clip(text, fs, zone_w, zone_h)
            if tc.h <= zone_h:
                groups.append(chunk)
                i += size
                break
        else:
            # Одно слово, всегда влезет
            groups.append([phrase[i]])
            i += 1
    return groups


# ─────────────────────────────────────────────────────────────
# Рендер группы субтитров
#
# Логика:
#   - Группа из N слов (1–3).
#   - Группа видна с момента первого слова по конец последнего.
#   - Каждое слово появляется по своему тайминг-старту.
#   - Все слова исчезают вместе в конце последнего слова группы.
#   - Дизайн: только жёлтый текст, stroke 1px чёрный, ничего лишнего.
#   - Реализация: один TextClip на всю группу (все слова сразу, жёлтые)
#     появляется в момент t_start группы. Поверх него для каждого слова
#     накладывается "маскирующий" клип того же текста но прозрачным цветом
#     (transparent) — MoviePy не поддерживает прозрачный цвет в label,
#     поэтому используем другую стратегию:
#
#   Стратегия "нарастающий текст":
#     - Клип 1: только слово 1 → появляется в t_start[0]
#     - Клип 2: слово 1 + слово 2 → появляется в t_start[1], перекрывает клип 1
#     - Клип 3: слово 1 + 2 + 3 → появляется в t_start[2], перекрывает клип 2
#     - Все клипы заканчиваются в t_end последнего слова.
#     - Каждый последующий клип ставится поверх предыдущего.
#     - Итог: слова "нарастают" по таймингу, исчезают все вместе.
# ─────────────────────────────────────────────────────────────

def _render_group(group, clip_w, clip_h):
    """
    Возвращает список TextClip для одной группы слов.
    Каждый клип живёт строго от своего старта до старта следующего —
    никакого накопления слоёв: клип_i удаляется ровно в момент
    появления клип_(i+1). Последний клип живёт до конца группы.
    """
    zone_w, zone_h, zone_x, zone_y = _sub_zone(clip_w, clip_h)
    t_group_end = group[-1]['end']
    result = []

    for i in range(len(group)):
        partial_text = ' '.join(w['text'] for w in group[:i + 1])
        fs = _fit_fs(partial_text, zone_w, zone_h)
        tc = _make_clip(partial_text, fs, zone_w, zone_h)

        txt_h   = min(tc.h, zone_h)
        final_y = _place_y(txt_h, zone_y, zone_h, clip_h)

        t_start = group[i]['start']
        # Клип живёт до старта следующего слова в группе;
        # последний клип — до конца группы
        t_end    = group[i + 1]['start'] if i + 1 < len(group) else t_group_end
        duration = max(t_end - t_start, 0.05)

        tc = (tc
            .with_start(t_start)
            .with_duration(duration)
            .with_position((zone_x, final_y))
        )
        result.append(tc)

    return result


# ─────────────────────────────────────────────────────────────
# Публичный API
# ─────────────────────────────────────────────────────────────

_sub_cache = {}

def get_subtitles_for_scene(scene_id, ep_name, clip_w, clip_h):
    if ep_name not in _sub_cache:
        sub_path = f"outputs/subtitles/{ep_name}.json"
        if not os.path.exists(sub_path):
            _sub_cache[ep_name] = {}
        else:
            with open(sub_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            _sub_cache[ep_name] = {int(k): v for k, v in raw.items()}

    words = _sub_cache[ep_name].get(int(scene_id), [])
    if not words:
        return []

    zone_w, zone_h, _, _ = _sub_zone(clip_w, clip_h)
    all_clips = []

    for phrase in _split_phrases(words):
        for group in _split_groups(phrase, zone_w, zone_h):
            all_clips.extend(_render_group(group, clip_w, clip_h))

    return all_clips


# ─────────────────────────────────────────────────────────────
# Рендер сцены
# ─────────────────────────────────────────────────────────────

def create_animated_clip(scene_data, ep_name, target_size=(240, 426)):
    duration  = scene_data['duration']
    img_path  = scene_data['image_path']
    scene_id  = scene_data['scene_id']
    anim_type = scene_data.get('animation', 'zoom_in')

    zoom_scale   = 0.3
    pan_distance = 500

    def ease_io(t):
        t_c = max(0.0, min(t, duration))
        return (1 - math.cos(t_c / duration * math.pi)) / 2

    clip = ImageClip(img_path).with_duration(duration).with_fps(24)

    if anim_type == "zoom_in":
        clip = clip.with_effects([Resize(new_size=lambda t: 1 + zoom_scale * ease_io(t))])
    elif anim_type == "zoom_out":
        clip = clip.with_effects([Resize(new_size=lambda t: (1 + zoom_scale) - zoom_scale * ease_io(t))])
    elif anim_type == "pan_left":
        clip = clip.with_position(lambda t: (-pan_distance * ease_io(t), 'center'))
    elif anim_type == "pan_right":
        clip = clip.with_position(lambda t: (-pan_distance + pan_distance * ease_io(t), 'center'))

    clip = (clip
            .with_effects([Margin(margin_size=0)])
            .with_effects([Resize(width=target_size[0])])
            .with_position('center'))

    sub_clips = get_subtitles_for_scene(scene_id, ep_name, target_size[0], target_size[1])

    if sub_clips:
        clip = CompositeVideoClip(
            [clip] + sub_clips,
            size=target_size
        ).with_duration(duration)

    audio = AudioFileClip(scene_data['audio_path'])
    clip = clip.with_audio(audio)
    return clip, audio


# ─────────────────────────────────────────────────────────────
# Основной рендер
# ─────────────────────────────────────────────────────────────

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
            audio_refs  = []

        for i, scene in enumerate(scenes):
            print(f"   ∟ Сцена {scene['scene_id']} + субтитры")
            clip, audio = create_animated_clip(scene, ep_name)
            audio_refs.append(audio)
            if i > 0:
                clip = clip.with_effects([CrossFadeIn(duration=0.6)])
            final_clips.append(clip)

        final_video = concatenate_videoclips(final_clips, method="compose", padding=-0.6)
        target_path = os.path.join(output_dir, f"{ep_name}.mp4")
        print(f"🚀 Запись: {target_path}...")

        final_video.write_videofile(
            target_path, fps=24,
            codec="libx264", audio_codec="aac",
            
        )

        final_video.close()
        return True # Сигнал успеха для оркестратора
    except Exception as e:
        print(f"❌ Ошибка рендеринга: {e}")
        return False