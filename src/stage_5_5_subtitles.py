import os
import json
import re
import traceback
from datetime import datetime

# Для retry session
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_retry_session():
    """Создание сессии с retry для стабильности через Cloudflare Tunnel"""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

retry_session = create_retry_session()


def log(msg, level="INFO"):
    """Вспомогательная функция для логирования с временными метками"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    prefix = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "DEBUG": "🔍"
    }.get(level, "•")
    print(f"[{timestamp}] {prefix} [{level}] {msg}")


def run_stage_5_5_subtitles(use_api=False, api_url=None):
    """
    Генерация субтитров через Whisper для всех эпизодов.
    
    Args:
        use_api: Если True, использует удаленный API вместо локального Whisper
        api_url: URL удаленного API (например, "https://your-colab.trycloudflare.com")
    
    Returns:
        True при успехе, False при ошибке.
    """
    log("=== ЗАПУСК STAGE_5_5_SUBTITLES ===", "INFO")
    log(f"Режим работы: {'API' if use_api else 'LOCAL WHISPER'}", "INFO")
    
    try:
        # ===== ШАГ 1: Проверка зависимостей =====
        log("Шаг 1/6: Проверка зависимостей...", "INFO")
        
        if use_api:
            try:
                import requests
                log("Модуль requests импортирован успешно", "SUCCESS")
                if not api_url:
                    log("Ошибка: api_url не указан для API режима", "ERROR")
                    return False
                log(f"API URL: {api_url}", "INFO")
            except ImportError as e:
                log(f"Не удалось импортировать requests: {e}", "ERROR")
                return False
        else:
            try:
                import whisper
                log("Модуль whisper импортирован успешно", "SUCCESS")
            except ImportError as e:
                log(f"Не удалось импортировать whisper: {e}", "ERROR")
                log("Попробуйте установить: pip install openai-whisper", "INFO")
                return False

        # ===== ШАГ 2: Подготовка модели =====
        log("Шаг 2/6: Подготовка обработчика...", "INFO")
        
        if not use_api:
            try:
                import whisper
                model = whisper.load_model("base")
                log("Модель Whisper загружена успешно", "SUCCESS")
            except Exception as e:
                log(f"Ошибка загрузки модели Whisper: {e}", "ERROR")
                traceback.print_exc()
                return False
        else:
            model = None  # При API режиме модель не нужна
            log("API режим - модель не загружается локально", "INFO")

        # ===== ШАГ 3: Проверка директорий =====
        log("Шаг 3/6: Проверка директорий...", "INFO")
        audio_root = "outputs/audio"
        sub_root   = "outputs/subtitles"
        
        log(f"Проверяем наличие: {audio_root}", "DEBUG")
        if not os.path.exists(audio_root):
            log(f"Папка с аудио не найдена: {audio_root}", "ERROR")
            log(f"Текущая рабочая директория: {os.getcwd()}", "DEBUG")
            if os.path.exists("."):
                log(f"Содержимое текущей директории: {os.listdir('.')}", "DEBUG")
            return False
        
        log(f"Папка {audio_root} найдена", "SUCCESS")
        log(f"Создаем/проверяем папку для субтитров: {sub_root}", "DEBUG")
        os.makedirs(sub_root, exist_ok=True)
        log(f"Папка {sub_root} готова", "SUCCESS")

        # ===== ШАГ 4: Поиск эпизодов =====
        log("Шаг 4/6: Поиск эпизодов...", "INFO")
        episodes = sorted([
            d for d in os.listdir(audio_root)
            if os.path.isdir(os.path.join(audio_root, d))
        ])
        
        log(f"Найдено эпизодов: {len(episodes)}", "INFO")
        if not episodes:
            log(f"Нет эпизодов для обработки в {audio_root}", "WARNING")
            log(f"Содержимое {audio_root}: {os.listdir(audio_root)}", "DEBUG")
            return False
        
        for ep in episodes:
            log(f"  - {ep}", "DEBUG")

        # ===== ШАГ 5: Обработка каждого эпизода =====
        log("Шаг 5/6: Обработка эпизодов...", "INFO")
        
        total_episodes_processed = 0
        total_scenes_processed = 0
        total_words_extracted = 0

        for ep_idx, ep in enumerate(episodes, 1):
            log(f"═══ Эпизод {ep_idx}/{len(episodes)}: {ep} ═══", "INFO")
            ep_audio_path = os.path.join(audio_root, ep)
            
            # Поиск аудиофайлов
            log(f"Поиск аудиофайлов в {ep_audio_path}", "DEBUG")
            audio_files = sorted(
                [f for f in os.listdir(ep_audio_path) if f.endswith((".mp3", ".wav"))],
                key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0
            )
            
            log(f"Найдено аудиофайлов: {len(audio_files)}", "INFO")
            if not audio_files:
                log(f"Нет аудиофайлов в {ep_audio_path}", "WARNING")
                log(f"Содержимое папки: {os.listdir(ep_audio_path)}", "DEBUG")
                continue

            for af in audio_files[:3]:
                log(f"  - {af}", "DEBUG")
            if len(audio_files) > 3:
                log(f"  ... и еще {len(audio_files) - 3} файлов", "DEBUG")

            episode_subs = {}
            scenes_in_episode = 0

            for af_idx, af in enumerate(audio_files, 1):
                log(f"─── Файл {af_idx}/{len(audio_files)}: {af} ───", "DEBUG")
                
                # Извлечение scene_id
                m = re.search(r'\d+', af)
                if not m:
                    log(f"Не удалось определить scene_id из имени: {af}", "WARNING")
                    continue

                scene_id = int(m.group())
                log(f"Scene ID: {scene_id}", "DEBUG")

                # Проверка на дубли
                if scene_id in episode_subs:
                    log(f"scene_id={scene_id} уже обработан (дубль {af}), пропуск", "WARNING")
                    continue

                audio_full_path = os.path.join(ep_audio_path, af)
                log(f"Путь к аудио: {audio_full_path}", "DEBUG")
                
                if not os.path.exists(audio_full_path):
                    log(f"Файл не существует: {audio_full_path}", "ERROR")
                    continue
                
                file_size = os.path.getsize(audio_full_path)
                log(f"Размер файла: {file_size} байт ({file_size/1024:.1f} KB)", "DEBUG")

                # Транскрипция
                log(f"Запуск транскрипции для сцены {scene_id}...", "INFO")
                try:
                    if use_api:
                        # API режим
                        with open(audio_full_path, 'rb') as f:
                            files = {'audio': (af, f, 'audio/mpeg')}
                            data = {'scene_ids_json': '[]'}
                            log(f"🚀 START REQUEST: {audio_full_path}", "DEBUG")
                            log(f"Отправка запроса к API: {api_url}/whisper", "DEBUG")
                            response = retry_session.post(
                                f"{api_url}/whisper",
                                files=files,
                                data=data,
                                timeout=(30, 300),
                                headers={"Connection": "close"}
                            )

                        log(f"✅ RESPONSE: {response.status_code}", "DEBUG")

                        if response.status_code != 200:
                            log(f"API вернул ошибку: {response.status_code}", "ERROR")
                            log(f"Ответ: {response.text[:500]}", "ERROR")
                            continue

                        result_data = response.json()
                        log(f"✅ JSON RECEIVED", "SUCCESS")

                        # Конвертация формата API в формат Whisper
                        api_words = result_data.get("0", [])  # API возвращает {"0": [...]}
                        words = []
                        for w in api_words:
                            clean = re.sub(r"[^\wА-Яа-яЁёa-zA-Z0-9]", "", w["text"].strip())
                            if clean:
                                words.append({
                                    "start": round(w["start"], 3),
                                    "end": round(w["end"], 3),
                                    "text": clean.upper()
                                })
                    else:
                        # Локальный Whisper
                        result = model.transcribe(
                            audio_full_path,
                            language="ru",
                            task="transcribe",
                            word_timestamps=True
                        )
                        log(f"Транскрипция завершена", "SUCCESS")
                        log(f"Сегментов получено: {len(result.get('segments', []))}", "DEBUG")

                        # Извлечение слов
                        words = []
                        for seg_idx, segment in enumerate(result["segments"]):
                            seg_words = segment.get("words", [])
                            log(f"  Сегмент {seg_idx + 1}: {len(seg_words)} слов", "DEBUG")
                            
                            for w in seg_words:
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
                    scenes_in_episode += 1
                    total_words_extracted += len(words)
                    
                    if words:
                        log(f"Извлечено {len(words)} слов, время: {words[0]['start']:.2f}–{words[-1]['end']:.2f}s", "SUCCESS")
                    else:
                        log(f"Извлечено 0 слов (тишина или ошибка распознавания)", "WARNING")

                except Exception as e:
                    log(f"Ошибка при транскрипции {af}: {e}", "ERROR")
                    log(f"Тип ошибки: {type(e).__name__}", "ERROR")
                    log(f"Подробности:", "ERROR")
                    traceback.print_exc()
                    continue

            # Сохранение результатов эпизода
            out_path = os.path.join(sub_root, f"{ep}.json")
            log(f"Сохранение субтитров в {out_path}", "INFO")
            
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(episode_subs, f, ensure_ascii=False, indent=2)
                
                file_size = os.path.getsize(out_path)
                total_words = sum(len(v) for v in episode_subs.values())
                log(f"Эпизод сохранен: {len(episode_subs)} сцен, {total_words} слов ({file_size} байт)", "SUCCESS")
                total_episodes_processed += 1
                total_scenes_processed += scenes_in_episode
                
            except Exception as e:
                log(f"Ошибка при сохранении {out_path}: {e}", "ERROR")
                traceback.print_exc()
                return False

        # ===== ШАГ 6: Итоговая статистика =====
        log("Шаг 6/6: Финализация...", "INFO")
        log("═══════════════════════════════════", "INFO")
        log(f"Обработано эпизодов: {total_episodes_processed}/{len(episodes)}", "INFO")
        log(f"Обработано сцен: {total_scenes_processed}", "INFO")
        log(f"Извлечено слов: {total_words_extracted}", "INFO")
        log("═══════════════════════════════════", "INFO")
        
        if total_episodes_processed == 0:
            log("Ни один эпизод не был обработан!", "ERROR")
            return False
        
        log("🎉 Все субтитры сгенерированы успешно!", "SUCCESS")
        log("=== STAGE_5_5_SUBTITLES ЗАВЕРШЕН ===", "SUCCESS")
        return True

    except Exception as e:
        log(f"КРИТИЧЕСКАЯ ОШИБКА в stage_5_5_subtitles: {e}", "ERROR")
        log(f"Тип ошибки: {type(e).__name__}", "ERROR")
        log("Полный стек ошибки:", "ERROR")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    log("Запуск как standalone скрипт", "INFO")
    
    # Проверка наличия файла настроек для API режима
    use_api = False
    api_url = None
    
    if os.path.exists("settings.json"):
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
                worker_url = settings.get("worker_url")
                if worker_url:
                    use_api = True
                    api_url = worker_url
                    log(f"Найден worker_url в settings.json: {worker_url}", "INFO")
        except Exception as e:
            log(f"Не удалось прочитать settings.json: {e}", "WARNING")
    
    success = run_stage_5_5_subtitles(use_api=use_api, api_url=api_url)
    log(f"Результат выполнения: {'SUCCESS' if success else 'FAILED'}", "SUCCESS" if success else "ERROR")
    exit(0 if success else 1)