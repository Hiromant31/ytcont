import threading
import time
import os
import re
import shutil
import traceback
import json
import requests

from .stage_1_story import run_stage_1
from .stage_2_scenes import run_stage_2
from .stage_3_draw_characters import run_stage_3_refs
from .stage_4_yandex_scenes import run_stage_4_scenes
from .stage_5_tts_yandex import run_stage_5_yandex_tts
from .stage_5_5_subtitles import run_stage_5_5_subtitles
from .stage_6_build_manifest import run_stage_6_manifest
from .stage_7_renderer import run_stage_7_render
from .template_manager import get_active_template


class VideoProductionManager:
    def __init__(self):
        self.status            = "Ожидание"
        self.current_stage_idx = 0
        self.logs              = []
        self.is_running        = False
        self.settings_path     = "settings.json"

        self.stages = [
            ("Сценарий",         run_stage_1),
            ("Раскадровка",      run_stage_2),
            ("Референсы лиц",    run_stage_3_refs),
            ("Генерация кадров", run_stage_4_scenes),
            ("Озвучка",          run_stage_5_yandex_tts),
            ("Субтитры",         self.wrapper_subtitles),
            ("Манифест",         run_stage_6_manifest),
            ("Рендеринг",        self.wrapper_render),
        ]

    # ─────────────────────────────────────────────────────────────
    # ВСПОМОГАТЕЛЬНЫЕ
    # ─────────────────────────────────────────────────────────────

    def log(self, message):
        ts  = time.strftime("%H:%M:%S")
        msg = f"[{ts}] {message}"
        self.logs.append(msg)
        print(msg)

    def load_config(self):
        if os.path.exists(self.settings_path):
            with open(self.settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "use_colab_whisper": False,
            "use_colab_render":  False,
            "colab_url":         "",
        }

    def _proxy_off(self):
        for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
            os.environ.pop(var, None)

    def _proxy_on(self):
        proxy = "http://127.0.0.1:10809"
        os.environ["HTTP_PROXY"]  = proxy
        os.environ["HTTPS_PROXY"] = proxy

    def _colab_url(self, config):
        return config.get("colab_url", "").rstrip("/")

    # ─────────────────────────────────────────────────────────────
    # УТИЛИТА: список аудио-файлов эпизода, отсортированных по scene_id
    # Полностью повторяет логику stage_5_5_subtitles.py
    # outputs/audio/{ep_name}/scene_{scene_id}.mp3
    # ─────────────────────────────────────────────────────────────

    def _get_episode_audio_files(self, ep_name):
        ep_audio_dir = os.path.join("outputs", "audio", ep_name)
        if not os.path.isdir(ep_audio_dir):
            self.log(f"⚠️ Папка аудио не найдена: {ep_audio_dir}")
            return []

        files = sorted(
            [f for f in os.listdir(ep_audio_dir) if f.endswith((".mp3", ".wav"))],
            key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0
        )

        result = []
        seen   = set()
        for fname in files:
            m = re.search(r'\d+', fname)
            if not m:
                continue
            scene_id = int(m.group())
            if scene_id in seen:
                self.log(f"⚠️ Дубль scene_id={scene_id} ({fname}), пропуск")
                continue
            seen.add(scene_id)
            result.append((scene_id, os.path.join(ep_audio_dir, fname)))

        return result

    # ─────────────────────────────────────────────────────────────
    # ЭТАП 6: СУБТИТРЫ — COLAB (Whisper) ИЛИ ЛОКАЛЬНО
    # ─────────────────────────────────────────────────────────────

    def wrapper_subtitles(self):
        config    = self.load_config()
        use_cloud = config.get("use_colab_whisper", False) and config.get("colab_url", "")

        if not use_cloud:
            self.log("🖥️ Субтитры: локальный Whisper...")
            return run_stage_5_5_subtitles()

        self.log("☁️ Субтитры: отправка на Colab Whisper...")
        url = self._colab_url(config)

        try:
            self._proxy_off()

            audio_root = os.path.join("outputs", "audio")
            if not os.path.isdir(audio_root):
                self.log(f"❌ Папка аудио не найдена: {audio_root}")
                return False

            # Все подпапки в outputs/audio/ — каждая папка = один эпизод
            episodes = sorted([
                d for d in os.listdir(audio_root)
                if os.path.isdir(os.path.join(audio_root, d))
            ])

            if not episodes:
                self.log("❌ Не найдено ни одного эпизода в outputs/audio/")
                return False

            os.makedirs("outputs/subtitles", exist_ok=True)
            all_ok = True

            for ep_name in episodes:
                self.log(f"\n✍️  Colab Whisper: эпизод {ep_name}")
                audio_files = self._get_episode_audio_files(ep_name)

                if not audio_files:
                    self.log(f"⚠️ Аудио-файлы не найдены для {ep_name}, пропуск")
                    continue

                episode_subs = {}

                # Каждый аудио-файл сцены — отдельный запрос на Colab,
                # так же как stage_5_5 обрабатывает их по одному
                for scene_id, audio_path in audio_files:
                    fname   = os.path.basename(audio_path)
                    size_kb = os.path.getsize(audio_path) // 1024
                    self.log(f"   ∟ Сцена {scene_id} ({fname}, {size_kb} KB)...")

                    with open(audio_path, "rb") as f_audio:
                        resp = requests.post(
                            f"{url}/whisper",
                            files={"audio": (fname, f_audio)},
                            data={"scene_ids_json": "[]"},
                            timeout=300,
                        )

                    if resp.status_code != 200:
                        self.log(f"   ❌ Whisper {resp.status_code}: {resp.text[:200]}")
                        all_ok = False
                        continue

                    result = resp.json()

                    # dowork.py возвращает {"0": [words]} для одиночного файла
                    words_raw = result.get("0", result.get("words", []))

                    # Чистим слова — та же логика что в stage_5_5
                    words = []
                    for w in words_raw:
                        clean = re.sub(r"[^\wА-Яа-яЁёa-zA-Z0-9]", "", w.get("text", ""))
                        if not clean:
                            continue
                        words.append({
                            "start": round(w["start"], 3),
                            "end":   round(w["end"],   3),
                            "text":  clean.upper(),
                        })

                    episode_subs[scene_id] = words
                    if words:
                        self.log(f"      → {len(words)} слов, {words[0]['start']:.2f}–{words[-1]['end']:.2f}s")
                    else:
                        self.log(f"      → 0 слов")

                # Сохраняем JSON — формат {scene_id: [words]} идентичен stage_5_5
                out_path = os.path.join("outputs", "subtitles", f"{ep_name}.json")
                with open(out_path, "w", encoding="utf-8") as f_out:
                    json.dump(episode_subs, f_out, ensure_ascii=False, indent=2)

                total_words = sum(len(v) for v in episode_subs.values())
                self.log(f"   ✅ {len(episode_subs)} сцен, {total_words} слов → {out_path}")

            return all_ok

        except Exception as e:
            self.log(f"❌ Ошибка Colab-Whisper: {e}")
            self.log(traceback.format_exc())
            return False
        finally:
            self._proxy_on()

    # ─────────────────────────────────────────────────────────────
    # ЭТАП 8: РЕНДЕР — COLAB ИЛИ ЛОКАЛЬНО
    # ─────────────────────────────────────────────────────────────

    def wrapper_render(self):
        config    = self.load_config()
        use_cloud = config.get("use_colab_render", False) and config.get("colab_url", "")

        if not use_cloud:
            self.log("🖥️ Рендер: локальный...")
            return run_stage_7_render()

        self.log("☁️ Рендер: отправка на Colab GPU...")
        url = self._colab_url(config)

        try:
            self._proxy_off()

            manifest_path = os.path.join("data", "3_assembly_manifest.json")
            if not os.path.exists(manifest_path):
                self.log("❌ Манифест не найден: data/3_assembly_manifest.json")
                return False

            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            os.makedirs("outputs/final_videos", exist_ok=True)

            for ep_name, scenes in manifest.items():
                self.log(f"📦 Подготовка эпизода {ep_name} ({len(scenes)} сцен)...")

                audio_handles = []
                image_handles = []
                try:
                    audio_files = []
                    image_files = []

                    for scene in scenes:
                        a_path = scene["audio_path"]
                        i_path = scene["image_path"]

                        a_fobj = open(a_path, "rb")
                        i_fobj = open(i_path, "rb")
                        audio_handles.append(a_fobj)
                        image_handles.append(i_fobj)

                        audio_files.append(("audio_files", (os.path.basename(a_path), a_fobj, "audio/mpeg")))
                        image_files.append(("image_files", (os.path.basename(i_path), i_fobj, "image/jpeg")))

                    # Субтитры для эпизода
                    sub_path = os.path.join("outputs", "subtitles", f"{ep_name}.json")
                    sub_data = "{}"
                    if os.path.exists(sub_path):
                        with open(sub_path, "r", encoding="utf-8") as f:
                            sub_data = f.read()
                    else:
                        self.log(f"⚠️ Субтитры не найдены для {ep_name}, рендерим без них")

                    data = {
                        "manifest_json":  json.dumps(scenes),
                        "subtitles_json": sub_data,
                        "settings_json":  json.dumps(config),
                    }

                    self.log(f"📤 Отправка на рендер: {ep_name}...")
                    resp = requests.post(
                        f"{url}/render",
                        data=data,
                        files=audio_files + image_files,
                        timeout=900,
                        stream=True,
                    )

                    if resp.status_code != 200:
                        self.log(f"❌ Рендер вернул {resp.status_code}: {resp.text[:500]}")
                        return False

                    target_path = os.path.join("outputs", "final_videos", f"{ep_name}.mp4")
                    size_bytes  = 0
                    with open(target_path, "wb") as f_out:
                        for chunk in resp.iter_content(chunk_size=512 * 1024):
                            f_out.write(chunk)
                            size_bytes += len(chunk)

                    self.log(f"✅ Видео получено: {ep_name}.mp4 ({size_bytes // 1024 // 1024} MB)")

                finally:
                    for fobj in audio_handles + image_handles:
                        fobj.close()

            return True

        except Exception as e:
            self.log(f"❌ Ошибка Colab-Render: {e}")
            self.log(traceback.format_exc())
            return False
        finally:
            self._proxy_on()

    # ─────────────────────────────────────────────────────────────
    # ОСНОВНОЙ ЦИКЛ
    # ─────────────────────────────────────────────────────────────

    def run_pipeline(self, start_from=1, custom_idea=None, num_episodes=3, ai_settings=None, prompts=None, auto_continue=True):
        self.is_running = True
        try:
            if custom_idea and custom_idea.strip():
                with open("idea.txt", "w", encoding="utf-8") as f:
                    f.write(custom_idea)
                self.log(f"💡 Идея: {custom_idea[:60]}...")
                self.log(f"🎬 Количество эпизодов: {num_episodes}")

            # Загружаем активный шаблон
            active_template = get_active_template()
            if active_template and not active_template.get("from_legacy"):
                self.log(f"🎭 Активный шаблон: {active_template.get('id', 'unknown')}")
                # Объединяем промпты из шаблона с пользовательскими
                try:
                    template_prompts = json.loads(active_template.get("prompts_json", "{}"))
                    if prompts:
                        template_prompts.update(prompts)
                    prompts = template_prompts
                except Exception as e:
                    self.log(f"⚠️ Ошибка объединения промптов из шаблона: {e}")

            # Сохраняем настройки AI и промпты (если переданы) перед первым этапом
            if start_from == 1:
                if ai_settings or prompts:
                    config = self.load_config()
                    if ai_settings:
                        config["ai_settings"] = ai_settings
                    if prompts:
                        if "prompts" not in config:
                            config["prompts"] = {}
                        config["prompts"].update(prompts)
                    config["auto_continue"] = auto_continue
                    config["num_episodes"] = num_episodes
                    with open(self.settings_path, "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=4, ensure_ascii=False)
                    self.log(f"🔄 Auto-continue: {'ВКЛ' if auto_continue else 'ВЫКЛ'}")

            # Запускаем этапы
            for i in range(start_from - 1, len(self.stages)):
                name, func = self.stages[i]
                self.current_stage_idx = i + 1
                self.status = f"Выполнение: {name}"
                self.log(f"━━━ ЭТАП {i+1}: {name} ━━━")

                # Передача настроек в этапы 1 и 2
                if i in [0, 1]:  # Stage 1 и Stage 2
                    config = self.load_config()
                    success = func(ai_settings=config.get("ai_settings", {}),
                                  prompts=config.get("prompts", {}),
                                  num_episodes=num_episodes)
                else:
                    self.log(f"📋 [ORCHESTRATOR] Вызов функции этапа {i+1}: {func.__name__}")
                    success = func()
                    self.log(f"📋 [ORCHESTRATOR] Функция этапа {i+1} вернула: {success}")

                if success is False:
                    raise Exception(f"Этап '{name}' завершился с ошибкой.")

                self.log(f"✅ Этап {i+1} завершён.")

                # Проверяем auto_continue
                if not auto_continue:
                    self.log(f"⏸️ Ожидание ручного запуска следующего этапа...")
                    break

                # Если не последний этап и auto_continue включён — продолжаем
                if i < len(self.stages) - 1:
                    self.log(f"🚀 Запуск следующего этапа...")
                    time.sleep(1)

            self.status = "Завершено"
            self.log("🎉 Пайплайн завершён успешно!")

        except Exception as e:
            self.status = "Ошибка"
            self.log(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            self.log(traceback.format_exc())
        finally:
            self.is_running = False


manager = VideoProductionManager()