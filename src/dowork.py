import os
import json
import uuid
import shutil
import asyncio
import subprocess
import tempfile
import nest_asyncio
import uvicorn
from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from google.colab import userdata

nest_asyncio.apply()

app = FastAPI()

BASE_WORK_DIR = "/content/worker_storage"
os.makedirs(BASE_WORK_DIR, exist_ok=True)

FFMPEG    = "/usr/bin/ffmpeg"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# ─────────────────────────────────────────────────────────────
# УТИЛИТЫ FFMPEG
# ─────────────────────────────────────────────────────────────

def run_ffmpeg(cmd: list, label="ffmpeg"):
    full_cmd = [FFMPEG, "-hide_banner", "-loglevel", "warning", "-y"] + cmd
    print(f"[{label}] Running...")
    result = subprocess.run(full_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg [{label}] failed:\n{result.stderr}")
    return result


# ─────────────────────────────────────────────────────────────
# ШАГ 1: РЕНДЕР СЦЕНЫ (изображение + анимация → silent mp4)
# ─────────────────────────────────────────────────────────────

def render_scene_video(img_path, duration, anim_type, target_w, target_h, out_path, codec):
    fps    = 24
    d      = int(duration * fps)
    s      = f"{target_w}x{target_h}"

    if anim_type == "zoom_in":
        zoom_expr = f"1.0+0.3*on/{d}"
        x_expr    = "iw/2-(iw/zoom/2)"
        y_expr    = "ih/2-(ih/zoom/2)"
    elif anim_type == "zoom_out":
        zoom_expr = f"1.3-0.3*on/{d}"
        x_expr    = "iw/2-(iw/zoom/2)"
        y_expr    = "ih/2-(ih/zoom/2)"
    elif anim_type == "pan_left":
        zoom_expr = "1.2"
        x_expr    = f"(iw-iw/zoom)*on/{d}"
        y_expr    = "ih/2-(ih/zoom/2)"
    elif anim_type == "pan_right":
        zoom_expr = "1.2"
        x_expr    = f"(iw-iw/zoom)*(1-on/{d})"
        y_expr    = "ih/2-(ih/zoom/2)"
    else:
        zoom_expr = "1.0"
        x_expr    = "iw/2-(iw/zoom/2)"
        y_expr    = "ih/2-(ih/zoom/2)"

    vf = (
        f"scale={target_w * 2}:{target_h * 2},"
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}'"
        f":d={d}:s={s}:fps={fps},"
        f"scale={target_w}:{target_h}"
    )

    codec_args = (
        ["-c:v", "h264_nvenc", "-preset", "p4", "-pix_fmt", "yuv420p"]
        if codec == "h264_nvenc"
        else ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
    )

    run_ffmpeg([
        "-loop", "1", "-i", img_path,
        "-vf", vf,
        "-t", str(duration),
        "-r", str(fps),
        *codec_args,
        "-an", out_path
    ], label=f"scene_video")


# ─────────────────────────────────────────────────────────────
# ШАГ 2: ГЕНЕРАЦИЯ ASS СУБТИТРОВ
# ─────────────────────────────────────────────────────────────

def words_to_ass(words, target_w, target_h):
    GROUP_SIZE  = 3
    PHRASE_GAP  = 0.35
    font_size   = max(28, target_h // 30)
    margin_v    = int(target_h * 0.08)

    lines = [
        "[Script Info]",
        f"PlayResX: {target_w}",
        f"PlayResY: {target_h}",
        "ScriptType: v4.00+",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,DejaVu Sans,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
        f"1,0,0,0,100,100,0,0,1,2,1,2,20,20,{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    def ts(sec):
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = sec % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    if not words:
        return "\n".join(lines)

    phrases, cur = [], [words[0]]
    for w in words[1:]:
        if w['start'] - cur[-1]['end'] > PHRASE_GAP:
            phrases.append(cur)
            cur = []
        cur.append(w)
    phrases.append(cur)

    for phrase in phrases:
        for gi in range(0, len(phrase), GROUP_SIZE):
            group       = phrase[gi:gi + GROUP_SIZE]
            group_end   = group[-1]['end']
            for wi, word in enumerate(group):
                w_start = word['start']
                w_end   = group[wi + 1]['start'] if wi + 1 < len(group) else group_end
                parts   = []
                for j, w in enumerate(group[:wi + 1]):
                    if j == wi:
                        parts.append(r"{\c&H00FFFF&}" + w['text'] + r"{\c&H00FFFFFF&}")
                    else:
                        parts.append(w['text'])
                text = " ".join(parts)
                lines.append(f"Dialogue: 0,{ts(w_start)},{ts(w_end)},Default,,0,0,0,,{text}")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# ШАГ 3: СКЛЕЙКА СЦЕНЫ (видео + аудио + субтитры)
# ─────────────────────────────────────────────────────────────

def merge_scene(video_path, audio_path, ass_path, out_path, codec):
    vf = f"ass={ass_path}" if ass_path and os.path.exists(ass_path) else "null"
    codec_args = (
        ["-c:v", "h264_nvenc", "-preset", "p4", "-pix_fmt", "yuv420p"]
        if codec == "h264_nvenc"
        else ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
    )
    run_ffmpeg([
        "-i", video_path,
        "-i", audio_path,
        "-vf", vf,
        *codec_args,
        "-c:a", "aac",
        "-shortest", out_path
    ], label="merge_scene")


# ─────────────────────────────────────────────────────────────
# ШАГ 4: ФИНАЛЬНАЯ СКЛЕЙКА
# ─────────────────────────────────────────────────────────────

def concat_scenes(scene_paths, out_path, codec):
    list_file = out_path + "_list.txt"
    with open(list_file, "w") as f:
        for p in scene_paths:
            f.write(f"file '{p}'\n")

    codec_args = (
        ["-c:v", "h264_nvenc", "-preset", "p4", "-pix_fmt", "yuv420p"]
        if codec == "h264_nvenc"
        else ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
    )
    run_ffmpeg([
        "-f", "concat", "-safe", "0", "-i", list_file,
        *codec_args, "-c:a", "aac", out_path
    ], label="concat_final")
    os.remove(list_file)


# ─────────────────────────────────────────────────────────────
# ЭНДПОИНТ /whisper — транскрипция аудио
# ─────────────────────────────────────────────────────────────

@app.post("/whisper")
async def api_whisper(
    audio: UploadFile = File(...),
    scene_ids_json: str = Form(default="[]")
):
    """
    Принимает аудиофайл, прогоняет через Whisper, возвращает JSON с пословной разметкой.
    Если переданы scene_ids_json — список scene_id для разбивки по сценам.
    Возвращает: { "scene_id": [{text, start, end}, ...], ... }
    """
    import whisper

    tmp_dir  = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, audio.filename)

    try:
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

        print(f"🎙️ Whisper: транскрипция {audio.filename}...")
        model  = whisper.load_model("base")
        result = model.transcribe(tmp_path, word_timestamps=True, language="ru")

        scene_ids = json.loads(scene_ids_json)

        # Если scene_ids не переданы — отдаём всё как одну сцену "0"
        if not scene_ids:
            words = []
            for seg in result.get("segments", []):
                for w in seg.get("words", []):
                    words.append({
                        "text":  w["word"].strip(),
                        "start": round(w["start"], 3),
                        "end":   round(w["end"], 3),
                    })
            return {"0": words}

        # Если scene_ids есть — оркестратор передаёт тайминги сцен отдельно
        # Просто возвращаем все слова, клиент сам разобьёт по сценам
        all_words = []
        for seg in result.get("segments", []):
            for w in seg.get("words", []):
                all_words.append({
                    "text":  w["word"].strip(),
                    "start": round(w["start"], 3),
                    "end":   round(w["end"], 3),
                })

        return {"words": all_words, "scene_ids": scene_ids}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ─────────────────────────────────────────────────────────────
# ЭНДПОИНТ /render — рендер видео
# ─────────────────────────────────────────────────────────────

@app.post("/render")
async def api_render(
    background_tasks: BackgroundTasks,
    manifest_json:   str = Form(...),
    subtitles_json:  str = Form(...),
    settings_json:   str = Form(...),
    audio_files:     list[UploadFile] = File(...),
    image_files:     list[UploadFile] = File(...)
):
    project_id  = str(uuid.uuid4())
    project_dir = os.path.join(BASE_WORK_DIR, project_id)
    dirs = {
        "audio":   os.path.join(project_dir, "inputs", "audio"),
        "images":  os.path.join(project_dir, "inputs", "images"),
        "scenes":  os.path.join(project_dir, "scenes"),
        "subs":    os.path.join(project_dir, "subs"),
        "outputs": os.path.join(project_dir, "outputs"),
    }
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)

    for a in audio_files:
        with open(os.path.join(dirs["audio"], a.filename), "wb") as f:
            shutil.copyfileobj(a.file, f)
    for img in image_files:
        with open(os.path.join(dirs["images"], img.filename), "wb") as f:
            shutil.copyfileobj(img.file, f)

    settings     = json.loads(settings_json)
    manifest     = json.loads(manifest_json)
    subtitles    = json.loads(subtitles_json) if subtitles_json.strip() else {}

    quality      = settings.get("quality", "1080p")
    aspect_ratio = settings.get("aspect_ratio", "9:16")
    codec        = settings.get("codec", "libx264")

    resolutions = {
        "1080p": {"16:9": (1920, 1080), "9:16": (1080, 1920)},
        "720p":  {"16:9": (1280, 720),  "9:16": (720,  1280)},
        "480p":  {"16:9": (854,  480),  "9:16": (480,  854)},
        "360p":  {"16:9": (640,  360),  "9:16": (360,  640)},
        "240p":  {"16:9": (426,  240),  "9:16": (240,  426)},
    }
    target_w, target_h = resolutions.get(quality, resolutions["1080p"]).get(aspect_ratio, (1080, 1920))

    print(f"🚀 РЕНДЕР: {quality} | {aspect_ratio} | {target_w}x{target_h} | codec={codec}")

    try:
        merged_scene_paths = []

        for idx, scene in enumerate(manifest):
            scene_id   = str(scene.get("scene_id", idx))
            duration   = float(scene["duration"])
            anim_type  = scene.get("animation", "zoom_in")
            img_name   = os.path.basename(scene["image_path"])
            audio_name = os.path.basename(scene["audio_path"])

            img_path   = os.path.join(dirs["images"], img_name)
            audio_path = os.path.join(dirs["audio"],  audio_name)

            # 1. Анимированное видео без звука
            silent_video = os.path.join(dirs["scenes"], f"scene_{idx:03d}_silent.mp4")
            render_scene_video(img_path, duration, anim_type, target_w, target_h, silent_video, codec)

            # 2. ASS субтитры
            words = subtitles.get(scene_id) or subtitles.get(
                int(scene_id) if scene_id.isdigit() else scene_id, []
            )
            ass_path = ""
            if words:
                ass_content = words_to_ass(words, target_w, target_h)
                ass_path    = os.path.join(dirs["subs"], f"scene_{idx:03d}.ass")
                with open(ass_path, "w", encoding="utf-8") as f:
                    f.write(ass_content)

            # 3. Мержим аудио + субтитры
            merged = os.path.join(dirs["scenes"], f"scene_{idx:03d}_merged.mp4")
            merge_scene(silent_video, audio_path, ass_path, merged, codec)
            merged_scene_paths.append(merged)
            os.remove(silent_video)

        # 4. Склейка всех сцен
        out_path = os.path.join(dirs["outputs"], "final.mp4")
        if len(merged_scene_paths) == 1:
            shutil.copy(merged_scene_paths[0], out_path)
        else:
            concat_scenes(merged_scene_paths, out_path, codec)

        return FileResponse(out_path, media_type="video/mp4")

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        background_tasks.add_task(shutil.rmtree, project_dir, ignore_errors=True)


@app.get("/", response_class=HTMLResponse)
async def index():
    return "<h1>Colab Worker Active</h1><p>Waiting for requests...</p>"


# ─────────────────────────────────────────────────────────────
# ЗАПУСК
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        # Cloudflare Tunnel (instead of ngrok)
        # Cloudflared запускается автоматически, просто запускаем сервер
        print("🚀 Колаб воркер запущен")
        
        config = uvicorn.Config(app, host="0.0.0.0", port=8001, loop="asyncio")
        server = uvicorn.Server(config)
        loop   = asyncio.get_event_loop()
        loop.run_until_complete(server.serve())

    except Exception as e:
        print(f"❌ Ошибка: {e}")