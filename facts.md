    📊 КАРТА ПРОЕКТА AI VIDEO STUDIO

    🔷 ОБЩАЯ СТРУКТУРА ПАЙПЛАЙНА

      1 [idea.txt] 
      2     ↓
      3 Stage 1 (story.py)      → data/1_base_structure.json, data
        /visual_config.json
      4     ↓
      5 Stage 2 (scenes.py)     → data/2_production_map.json
      6     ↓
      7 Stage 3 (draw_chars.py) → outputs/references/ (эталонные лица)
      8     ↓
      9 Stage 4 (yandex_scenes) → outputs/scenes/{ep}/scene_N.jpeg
     10     ↓
     11 Stage 5 (tts_yandex)    → outputs/audio/{ep}/scene_N.mp3
     12     ↓
     13 Stage 5.5 (subtitles)   → outputs/subtitles/{ep}.json
     14     ↓
     15 Stage 6 (manifest)      → data/3_assembly_manifest.json
     16     ↓
     17 Stage 7 (renderer)      → outputs/final_videos/{ep}.mp4
     18     ↓
     19 Stage 8 (youtube)       → YouTube upload

    ---

    📂 ФАЙЛОВАЯ АРХИТЕКТУРА

    Входные файлы:

    ┌───────────────────────────────────┬────────────────┬──────────────┐
    │ Файл                              │ Назначение     │ Используется │
    │                                   │                │  в           │
    ├───────────────────────────────────┼────────────────┼──────────────┤
    │ idea.txt                          │ Исходная       │ Stage 1      │
    │                                   │ идея/концепция │              │
    ├───────────────────────────────────┼────────────────┼──────────────┤
    │ settings.json                     │ Настройки AI,  │ Весь         │
    │                                   │ формат, Colab  │ пайплайн     │
    ├───────────────────────────────────┼────────────────┼──────────────┤
    │                                   │ API ключи      │ Весь         │
    │ .env                              │ (Yandex,       │ пайплайн     │
    │                                   │ Gemini, HF)    │              │
    ├───────────────────────────────────┼────────────────┼──────────────┤
    │ prompts/writer_instruction.txt    │ Инструкция     │ Stage 1      │
    │                                   │ сценаристу     │              │
    ├───────────────────────────────────┼────────────────┼──────────────┤
    │ prompts/extractor_instruction.txt │ Инструкция     │ Stage 1      │
    │                                   │ экстрактору    │              │
    ├───────────────────────────────────┼────────────────┼──────────────┤
    │ prompts/stage_2_scenes.txt        │ Инструкция     │ Stage 2      │
    │                                   │ режиссёру      │              │
    └───────────────────────────────────┴────────────────┴──────────────┘


    Промежуточные данные:

    ┌──────────────────────────────┬────────────────────────────┬───────┐
    │ Файл                         │ Назначение                 │ Форма │
    │                              │                            │ т     │
    ├──────────────────────────────┼────────────────────────────┼───────┤
    │                              │ Master story +             │       │
    │ data/1_base_structure.json   │ episodes_raw +             │ JSON  │
    │                              │ episodes_final             │       │
    ├──────────────────────────────┼────────────────────────────┼───────┤
    │ data/visual_config.json      │ characters dict +          │ JSON  │
    │                              │ visual_style               │       │
    ├──────────────────────────────┼────────────────────────────┼───────┤
    │ data/2_production_map.json   │ scenes per episode с visua │ JSON  │
    │                              │ l_prompt/audio_segment     │       │
    ├──────────────────────────────┼────────────────────────────┼───────┤
    │ data/3_assembly_manifest.jso │ финальная сборка:          │       │
    │ n                            │ image/audio paths,         │ JSON  │
    │                              │ animation, transition      │       │
    ├──────────────────────────────┼────────────────────────────┼───────┤
    │ data/story_draft.txt         │ Драфт сценария             │ TXT   │
    └──────────────────────────────┴────────────────────────────┴───────┘


    Выходные файлы:

    ┌─────────────────────────────┬──────────────────────────────┐
    │ Файл                        │ Назначение                   │
    ├─────────────────────────────┼──────────────────────────────┤
    │ outputs/references/         │ Эталонные лица (1:1 square)  │
    ├─────────────────────────────┼──────────────────────────────┤
    │ outputs/scenes/{ep}/        │ Сгенерированные сцены (9:16) │
    ├─────────────────────────────┼──────────────────────────────┤
    │ outputs/audio/{ep}/         │ TTS аудио                    │
    ├─────────────────────────────┼──────────────────────────────┤
    │ outputs/subtitles/{ep}.json │ Пословные субтитры           │
    ├─────────────────────────────┼──────────────────────────────┤
    │ outputs/final_videos/       │ Готовые видеофайлы           │
    └─────────────────────────────┴──────────────────────────────┘

    ---

    🧠 ЛОГИКА ЭТАПОВ

    Stage 1: Story Generation (stage_1_story.py)

    Цель: Создать структуру истории и извлечь персонажей.

    Логика:
     1. Загружает idea.txt + промпты (из settings.json или файлов)
     2. ПРОМПТ 1 (STORY_PROMPT): Генерирует master story из 3 эпизодов
        - Требует: TITLE, CHARACTERS, CORE_CONFLICT, EP1/EP2/EP3 планы
     3. ПРОМПТ 2 (EPISODE_PROMPT): Раскрывает каждый эпизод (100-120 слов)
        - Структура: HOOK, START, BUILD, IMPACT, END
        - Требует связный рассказ (не обрывки)
     4. ПРОМПТ 3 (POLISH_PROMPT): Доработка под voice-over
     5. ЭКСТРАКТОР: Анализирует весь текст и извлекает персонажей в JSON
        - Вызывает call_ai_extractor() с 2мя ретраями при ошибке
        - Парсит JSON утилитами repair_truncated_json()

    Модули: load_settings(), load_prompts_from_json(),
    load_prompts_from_files()
    Инструменты: repair_truncated_json() — умная коррекция обрезанного JSON

    ---

    Stage 2: Scene Planning (stage_2_scenes.py)

    Цель: Разбить сценарий на визуальные сцены с таймингами.

    Логика:
     1. Загружает data/1_base_structure.json → episodes_final
     2. Загружает data/visual_config.json → characters_metadata
     3. Для каждой сцены формирует prompt с тегами [MAIN_1], [MAIN_2], [PLACE_1]
     4. Вызывает AI (Yandex или OpenAI) с инструкцией stage_2_scenes.txt
     5. Парсит JSON → 2_production_map.json

    Промпт AI:

     1 - Разбей текст на сцены по каждому значимому действию
     2 - visual_prompt: Shot type, [TAGS] action, environment, lighting ( макс
       150 chars)
     3 - audio_segment: Russian text for TTS

    Важно: Не пропускает части истории, не пропускает сцены.

    ---

    Stage 3: Face References (stage_3_draw_characters.py)

    Цель: Сгенерировать эталонные портреты персонажей.

    Логика:
     1. Загружает data/visual_config.json → characters
     2. Использует Yandex Art SDK (yandex_ai_studio_sdk)
     3. Формат: 1:1 square (для эталонов)
     4. Глобальный стиль:
     1    "Gritty 2D hand-drawn illustration, bold ink outlines, 
     2     dark moody atmosphere, graphic novel style..."
     5. Генерирует outputs/references/{character_name}.jpeg

    Проблема: В файле data/visual_config.json в текущей версии список 
    эпизодов, а не структура {"characters": {...}}. Это приводит к ошибке в
    Stage 3.

    Решение: Stage 1 должен генерировать правильную структуру
    visual_config.json.

    ---

    Stage 4: Scene Images (stage_4_yandex_scenes.py)

    Цель: Генерировать изображения для каждой сцены.

    Логика:
     1. Загружает data/2_production_map.json
     2. Заменяет теги [MAIN_1], [MAIN_2], [PLACE_1] на реальные описания
     3. Добавляет глобальный стиль:
     1    "Hand-drawn 2D animation style, visible ink strokes, 
     2     dark gloomy lighting, gritty atmosphere..."
     4. Формат: 9:16 (для Shorts)
     5. Генерирует outputs/scenes/{ep}/scene_{id}.jpeg

    Ограничение: Макс 500 символов на промпт.

    ---

    Stage 5: TTS Generation (stage_5_tts_yandex.py)

    Цель: Озвучить каждую сцену.

    Логика:
     1. Загружает data/2_production_map.json
     2. Для каждой сцены берёт audio_segment
     3. Запрашивает Yandex SpeechKit v1 API:

     1    url: https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize
     2    voice: ermil (глубокий мужской)
     3    emotion: neutral
     4    speed: 1.1
     5    format: mp3
     4. Сохраняет outputs/audio/{ep}/scene_{id}.mp3

    ---

    Stage 5.5: Subtitles (stage_5_5_subtitles.py)

    Цель: Генерировать субтитры через Whisper.

    Логика:
     1. Загружает модель Whisper (base)
     2. Для каждого аудиофайла:
        - Транскрибирует с word_timestamps=True
        - Очищает слова от спецсимволов
        - Сохраняет в outputs/subtitles/{ep}.json
     3. Формат: {scene_id: [{text, start, end}, ...]}

    Дублирование: Логика _get_episode_audio_files() дублируется в
    orchestrator.py.

    ---

    Stage 6: Assembly Manifest (stage_6_build_manifest.py)

    Цель: Собрать финальный манифест с правилами анимации.

    Логика:
     1. Сканирует outputs/scenes/{ep}/
     2. Читает длительность аудио через mutagen.mp3.MP3
     3. Правила переходов (Match Cut):

     1    zoom_in  → [zoom_in, pan_right, pan_left]
     2    zoom_out → [zoom_out, pan_left, pan_right]
     3    pan_left → [pan_left, zoom_in, zoom_out]
     4    pan_right → [pan_right, zoom_in, zoom_out]
     4. Выбирает transition:
        - crossfade: если одинаковая семья (zoom↔zoom, pan↔pan)
        - fade: если смена вектора (zoom↔pan)
     5. Добавляет CROSSFADE_DURATION=0.8 к длительности
     6. Сохраняет data/3_assembly_manifest.json

    Кроссфейд: Половина с каждой стороны, чтобы не перекрывать речь.

    ---

    Stage 7: Rendering (stage_7_renderer.py)

    Цель: Склеить видео из сцен.

    Логика:
     1. Загружает data/3_assembly_manifest.json
     2. Для каждой сцены:
        - Загружает изображение
        - Применяет анимацию (zoom_in/zoom_out/pan_left/pan_right)
        - Добавляет субтитры (TextClip с многострочным caption)
        - Клеит аудио
     3. Кроссфейды между сценами (CrossFadeIn)
     4. Сохраняет в outputs/final_videos/{ep}.mp4

    Особенности:
     - Font: DejaVuSans-Bold
     - Анимация через Resize и Position с easing
     - Субтитры группируются по 3 слова, с плавным появлением

    ---

    Stage 8: YouTube Upload (stage_8_youtube_upload.py)

    Цель: Загрузить видео на YouTube.

    Класс `YouTubeUploader`:
     - authenticate(): OAuth 2.0 с сохранением token.pickle
     - generate_metadata(): title, description, tags
     - upload_video(): загрузка с поддержкой schedule_time
     - generate_schedule_time(): RFC 3339 формат

    Scopes: https://www.googleapis.com/auth/youtube.upload

    ---

    🔄 ORCHESTRATOR (orchestrator.py)

    Класс `VideoProductionManager`:
     - Запускает этапы последовательно
     - Передаёт ai_settings и prompts в этапы 1 и 2
     - Поддерживает Colab GPU:
       - wrapper_subtitles(): локальный Whisper или Colab
       - wrapper_render(): локальный рендер или Colab
     - Переменные прокси: _proxy_off() / _proxy_on()

    Этапы (tuple list):

      1 [
      2   ("Сценарий",         run_stage_1),
      3   ("Раскадровка",      run_stage_2),
      4   ("Референсы лиц",    run_stage_3_refs),
      5   ("Генерация кадров", run_stage_4_scenes),
      6   ("Озвучка",          run_stage_5_yandex_tts),
      7   ("Субтитры",         wrapper_subtitles),
      8   ("Манифест",         run_stage_6_manifest),
      9   ("Рендеринг",        wrapper_render),
     10 ]

    ---

    🌐 WEB SERVER (main.py)

    FastAPI сервер:
     - /: HTML UI с панелью управления
     - /settings: GET/POST настроек
     - Запуск этапов по API
     - Логирование в реальном времени
     - Модальное окно для просмотра эпизодов

    Фичи:
     - Auto-continue
     - Test mode (15 сек)
     - Colab integration
     - Редактор промптов

    ---

    🎨 ПРОМПТЫ (код + файлы)

    Код Stage 1:

    ┌────────────────┬────────────────────────────┬────────────┐
    │ Промпт         │ Назначение                 │ max_tokens │
    ├────────────────┼────────────────────────────┼────────────┤
    │ STORY_PROMPT   │ Master story из 3 эпизодов │ 4000       │
    ├────────────────┼────────────────────────────┼────────────┤
    │ EPISODE_PROMPT │ Раскрытие эпизода          │ 4000       │
    ├────────────────┼────────────────────────────┼────────────┤
    │ POLISH_PROMPT  │ Доработка под озвучку      │ 4000       │
    ├────────────────┼────────────────────────────┼────────────┤
    │ EXTRACTOR      │ Извлечение персонажей      │ 3000       │
    └────────────────┴────────────────────────────┴────────────┘


    Файлы prompts/:

    ┌────────────────────────────┬───────┬───────────────────────────────┐
    │ Файл                       │ Язык  │ Назначение                    │
    ├────────────────────────────┼───────┼───────────────────────────────┤
    │                            │       │ Детальная инструкция          │
    │ writer_instruction.txt     │ Ru/En │ сценаристу (60-90 сек         │
    │                            │       │ эпизоды)                      │
    ├────────────────────────────┼───────┼───────────────────────────────┤
    │ extractor_instruction.txt  │ En    │ Инструкция экстрактору (JSON, │
    │                            │       │  120-150 chars)               │
    ├────────────────────────────┼───────┼───────────────────────────────┤
    │ structurer_instruction.txt │ -     │ -                             │
    ├────────────────────────────┼───────┼───────────────────────────────┤
    │ stage_2_scenes.txt         │ En    │ Режиссёр + раскадровка (Shot  │
    │                            │       │ type + tags)                  │
    └────────────────────────────┴───────┴───────────────────────────────┘

    ---

    ⚙️ ИСТОЧНИКИ ИНФОРМАЦИИ

    AI API:
     - Yandex GPT: https://ai.api.cloud.yandex.net/v1 (YandexArt, GPT)
     - Gemini: gemini-2.0-flash-exp / gemini-3.1-flash-lite-preview
     - DeepSeek: deepseek/deepseek-v4-pro (через routerai.ru)
     - Whisper: base (локально)

    Audio API:
     - Yandex SpeechKit v1:
       https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize

    YouTube API:
     - OAuth 2.0
     - Scopes: youtube.upload
     - Токен: token.pickle

    ---

    🐛 НАЙДЕННЫЕ ПРОБЛЕМЫ

    🔴 КРИТИЧНЫЕ:

     1. Структура `visual_config.json`
        - Проблема: В файле data/visual_config.json лежит список эпизодов, а не
          {"characters": {...}}
        - Влияние: Stage 3 не может найти персонажей
        - Причина: Экстрактор в Stage 1 не сохраняет в правильном формате
        - Решение: Исправить Stage 1 (строка 618: использовать episodes_final,
          не episodes)

     2. Дублирование логики в `orchestrator.py` и `stage_5_5_subtitles.py`
        - Функция _get_episode_audio_files() дублируется
        - Решение: Вынести в отдельный модуль utils.py

     3. Отсутствие кэширования
        - Каждый этап перегенерирует всё при рестарте
        - Решение: Проверять существование data/N_*.json и пропускать этап

    🟠 МОДУЛЬНЫЕ:

     4. Конфликт форматов `visual_config.json`
        - Иногда приходит как список, иногда как dict
        - Решение: Везде нормализовать: if isinstance(x, list): x = x[0]

     5. Отсутствие валидации входных данных
        - Stage 3 падает при пустом characters
        - Решение: Валидация + fallback с пустыми данными

     6. Избыточный промпт в `stage_2_scenes.txt`
        - 387 слов, можно сократить до 150-200
        - Решение: Вынести правила в код, оставить только суть

    ---

    🔁 ДВОЙНИКИ И ЗАДВОЕНИЕ ЛОГИКИ


    ┌─────────────┬─────────────────────────┬──────────────────────────┐
    │ Логика      │ Где дублируется         │ Рекомендация             │
    ├─────────────┼─────────────────────────┼──────────────────────────┤
    │ Парсинг     │ stage_1_story.py +      │ Использовать             │
    │ JSON из AI  │ stage_2_scenes.py       │ repair_truncated_json()  │
    │             │                         │ из stage_1               │
    ├─────────────┼─────────────────────────┼──────────────────────────┤
    │ Получение   │ orchestrator.py +       │ Вынести в utils/audio.py │
    │ аудиофайлов │ stage_5_5_subtitles.py  │                          │
    ├─────────────┼─────────────────────────┼──────────────────────────┤
    │ Создание    │ Везде os.makedirs(...,  │ Вынести в utils/fs.py    │
    │ папок       │ exist_ok=True)          │                          │
    ├─────────────┼─────────────────────────┼──────────────────────────┤
    │ Обработка   │ stage_1, stage_3,       │ Общий yandex_client.py   │
    │ Yandex API  │ stage_4, stage_5        │                          │
    ├─────────────┼─────────────────────────┼──────────────────────────┤
    │ Прокси      │ orchestrator.py         │ Уже централизовано ✓     │
    │ off/on      │                         │                          │
    └─────────────┴─────────────────────────┴──────────────────────────┘

    ---

    📊 ЦИФРЫ И ЛОГИКА


    ┌──────┬────────────────┬────────────────────────┬──────────────────┐
    │ Этап │ Входные данные │ Выходные данные        │ API вызовов (на  │
    │      │                │                        │ 1 эпизод)        │
    ├──────┼────────────────┼────────────────────────┼──────────────────┤
    │      │                │                        │ 8-10 (story + 3  │
    │ 1    │ idea.txt       │ 3 episodes,            │ episodes +       │
    │      │                │ visual_config          │ polish +         │
    │      │                │                        │ extractor)       │
    ├──────┼────────────────┼────────────────────────┼──────────────────┤
    │ 2    │ episodes_final │ production_map         │ 3 (по одному на  │
    │      │                │                        │ эпизод)          │
    ├──────┼────────────────┼────────────────────────┼──────────────────┤
    │      │                │                        │ 1-3 (в           │
    │ 3    │ visual_config  │ references/*.jpeg      │ зависимости от   │
    │      │                │                        │ числа            │
    │      │                │                        │ персонажей)      │
    ├──────┼────────────────┼────────────────────────┼──────────────────┤
    │ 4    │ production_map │ scenes/*.jpeg          │ ~10-15 (по числу │
    │      │                │                        │  сцен)           │
    ├──────┼────────────────┼────────────────────────┼──────────────────┤
    │ 5    │ production_map │ audio/*.mp3            │ ~10-15 (по числу │
    │      │                │                        │  сцен)           │
    ├──────┼────────────────┼────────────────────────┼──────────────────┤
    │ 5.5  │ audio/*.mp3    │ subtitles/*.json       │ 1 (Whisper на    │
    │      │                │                        │ всё аудио)       │
    ├──────┼────────────────┼────────────────────────┼──────────────────┤
    │ 6    │ scenes/*.jpeg  │ assembly_manifest.json │ 0                │
    ├──────┼────────────────┼────────────────────────┼──────────────────┤
    │ 7    │ manifest       │ final_videos/*.mp4     │ 0                │
    └──────┴────────────────┴────────────────────────┴──────────────────┘


    Итого: На 3 эпизода (~30 сцен):
     - Stage 1: ~10 API вызовов
     - Stage 2: ~3 API вызова
     - Stage 3: ~1-3 API вызова (YandexArt)
     - Stage 4: ~30 API вызовов (YandexArt)
     - Stage 5: ~30 API вызовов (YandexTTS)

    Общее: ~75-85 API вызовов на 1 серию

    ---

    🎯 РЕКОМЕНДАЦИИ

    Приоритет 1 (критично):
     1. Исправить формат visual_config.json в Stage 1
     2. Вынести общую логику в utils/
     3. Добавить кэширование этапов
     4. Валидация входных данных

    Приоритет 2 (модульность):
     1. Общий Yandex API клиент
     2. Общий JSON парсер
     3. Централизованная обработка прокси
     4. Унифицированный логгер

    Приоритет 3 (оптимизация):
     1. Сократить промпты (экономия токенов ~65%)
     2. Уменьшить max_tokens (уже применено)
     3. Уменьшить MAX_RETRIES (уже 2)

    ---

    📁 ДЕРЕВО ПРОЕКТА

      1 ytcont/
      2 ├── src/
      3 │   ├── main.py                  # FastAPI web server
      4 │   ├── orchestrator.py          # Pipeline manager
      5 │   ├── dowork.py                # Colab worker
      6 │   ├── stage_1_story.py         # Story + extract
      7 │   ├── stage_2_scenes.py        # Scene planning
      8 │   ├── stage_3_draw_characters.py  # Face refs
      9 │   ├── stage_4_yandex_scenes.py    # Scene images
     10 │   ├── stage_5_tts_yandex.py       # TTS
     11 │   ├── stage_5_5_subtitles.py      # Whisper
     12 │   ├── stage_6_build_manifest.py   # Assembly
     13 │   ├── stage_7_renderer.py         # Render
     14 │   ├── stage_7_rendererCLAUDE.py   # Alt render
     15 │   ├── stage_8_youtube_upload.py   # Upload
     16 │   ├── obyav_gemini.py             # Gemini ad generator
     17 │   ├── youtube_oauth_helper.py     # OAuth utils
     18 │   └── prompts/                    # Промпты
     19 │       ├── writer_instruction.txt
     20 │       ├── extractor_instruction.txt
     21 │       ├── stage_2_scenes.txt
     22 │       └── structurer_instruction.txt
     23 ├── data/                           # Промежуточные данные
     24 │   ├── 1_base_structure.json
     25 │   ├── 2_production_map.json
     26 │   ├── 3_assembly_manifest.json
     27 │   ├── visual_config.json
     28 │   └── story_draft.txt
     29 ├── outputs/
     30 │   ├── scenes/{ep}/                # Сгенерированные кадры
     31 │   ├── audio/{ep}/                 # TTS аудио
     32 │   ├── subtitles/{ep}.json         # Субтитры
     33 │   ├── references/                 # Эталонные лица
     34 │   └── final_videos/               # Готовые видео
     35 ├── settings.json                   # Настройки
     36 ├── .env                            # API ключи
     37 ├── idea.txt                        # Исходная идея
     38 ├── requirements.txt                # Зависимости
     39 ├── run.py                          # Запуск
     40 └── main_enhanced.py                # Бэкап

    ---

    ✅ ЗАКЛЮЧЕНИЕ

    Сильные стороны:
     - Чёткое разделение на этапы
     - Поддержка Colab GPU
     - Yandex AI + Gemini + DeepSeek (гибкость)
     - Умный парсинг JSON
     - Кроссфейды и Match Cut правила
     - UI с логами и настройками

    Что нужно исправить:
     1. Формат visual_config.json (Stage 1)
     2. Дублирование кода (utils)
     3. Отсутствие кэширования
     4. Валидация данных
     5. Объединение Yandex API клиентов

    Карта готова. Можно приступать к исправлениям.
