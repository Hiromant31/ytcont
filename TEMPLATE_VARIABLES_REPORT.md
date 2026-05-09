# 📊 ПОЛНЫЙ ОТЧЕТ: Переменные и их применение в Template System

## ⚠️ ВАЖНО: ИСПРАВЛЕНИЕ ОШИБКИ В РАННЕЙ ДОКУМЕНТАЦИИ

В первом отчете было указано что используется 3 промпта:
- `stage_1_writer`
- `stage_1_extractor` 
- `stage_2_scenes`

**Это НЕВЕРНО.**

**Действительно в коде используется только 2 промпта в Stage 1:**
- `stage_1_writer` 
- `stage_1_extractor`

А `stage_2_scenes` используется в Stage 2 отдельно.

---

## 1. СТРУКТУРА ПРОМПТОВ В ШАБЛОНЕ

### База данных (data/ytcont.db)

**Таблица `templates`:**
```sql
prompts_json TEXT NOT NULL
settings_json TEXT
```

### Формат `prompts_json`:

```json
{
  "stage_1_writer": "... текст на РУССКОМ ...",
  "stage_1_extractor": "... текст на АНГЛИЙСКОМ ...",
  "stage_2_scenes": "... текст на АНГЛИЙСКОМ ..."
}
```

### Формат `settings_json`:

```json
{
  "visual_style": "... дефолтный стиль ...",
  "camera_motion": "slow_zoom",
  "voice_style": "dramatic"
}
```

---

## 2. ГДЕ КАКИЕ ПРОМПТЫ ИСПОЛЬЗУЮТСЯ

### Stage 1: Генерация сценария (stage_1_story.py)

#### Входные переменные из шаблона:

| Параметр | Откуда берется | Применяется | Язык |
|----------|----------------|-------------|------|
| `prompts_dict["writer"]` | `templates.prompts_json.stage_1_writer` | Генерация master story + эпизодов | РУССКИЙ |
| `prompts_dict["extractor"]` | `templates.prompts_json.stage_1_extractor` | Извлечение персонажей и visual_style | АНГЛИЙСКИЙ |

#### Код применения (stage_1_story.py:531-547):

```python
if template_id:
    print(f"   Используем шаблон: {template_id}")
    try:
        from .template_manager import get_template
        template = get_template(template_id)
        if template:
            template_prompts = json.loads(template.get("prompts_json", "{}"))
            prompts_dict = {
                "writer":    template_prompts.get("stage_1_writer", ""),
                "extractor": template_prompts.get("stage_1_extractor", "")
            }
            print("   ✅ Промпты загружены из шаблона")
```

#### Как используются промпты:

**stage_1_writer → STORY_PROMPT + EPISODE_PROMPT:**
```python
# Генерация master story
story_prompt_dynamic = STORY_PROMPT.replace("{NUM_EPISODES}", str(num_episodes))
master_story = call_ai_text(
    client,
    is_yandex,
    folder_id,
    model,
    story_prompt_dynamic,
    prompts_dict.get("idea", ""),
    max_tokens=4000
)

# Генерация эпизодов
episode_raw = call_ai_text(
    client,
    is_yandex,
    folder_id,
    model,
    EPISODE_PROMPT.format(
        MASTER_STORY=master_story,
        EPISODE_NUMBER=i
    ),
    "",
    max_tokens=4000
)
```

**stage_1_extractor → EXTRACTOR_SYSTEM:**
```python
extractor_system = (
    prompts_dict["extractor"].strip()
    + "\n\n"
    "=== СТРОГИЕ ПРАВИЛА ФОРМАТА ===\n"
    "- Верни ТОЛЬКО JSON, без текста вокруг, без ``` блоков.\n"
    # ... дополнительные правила
)

extractor_user = (
    "Проанализируй сценарий и верни ТОЛЬКО JSON (без пояснений):\n\n"
    + full_text
)

visual_config = call_ai_extractor(
    client=client,
    system_prompt=extractor_system,
    user_text=extractor_user,
    max_tokens=3000
)
```

#### Выходы Stage 1:

| Файл | Содержимое | Источник |
|------|------------|----------|
| `data/1_base_structure.json` | master_story, episodes_raw, episodes_final | Stage 1 (writer) |
| `data/visual_config.json` | characters + visual_style | Stage 1 (extractor AI) |

---

### Stage 2: Раскадровка (stage_2_scenes.py)

#### Входные переменные из шаблона:

| Параметр | Откуда берется | Применяется | Язык |
|----------|----------------|-------------|------|
| `system_instruction` | `templates.prompts_json.stage_2_scenes` | Генерация сцен | АНГЛИЙСКИЙ |

#### Код применения (stage_2_scenes.py:229-237):

```python
# Берем промпт из UI или из файла
system_instruction = prompts.get("stage_2_scenes", "") if prompts else ""

# Если промпт не найден, пробуем из шаблона
if not system_instruction:
    try:
        active_template = get_active_template()
        if active_template and not active_template.get("from_legacy"):
            template_prompts = json.loads(active_template.get("prompts_json", "{}"))
            system_instruction = template_prompts.get("stage_2_scenes", "")
            if system_instruction:
                print(f"   Используем промпт из шаблона: {active_template.get('id', 'unknown')}")
    except Exception as e:
        print(f"   ⚠️  Ошибка загрузки промпта из шаблона: {e}")
```

#### Как используется промпт:

```python
prompt_input = f"""TEXT: {ep_text}

CHARACTERS:
[MAIN_1] = {main_char}
[MAIN_2] = {supporting[0]}
[MAIN_3] = {supporting[1] if len(supporting) > 1 else ""}

VISUAL_STYLE: {visual_style}

TARGET: Разбей текст на сцены так, чтобы СУММАРНО получилось ~60 секунд озвучки.
ПРАВИЛО: Каждое значимое действие = отдельная сцена.

Output ONLY valid JSON:
{{
  "scenes": [
    {{
      "scene_id": 1,
      "visual_prompt": "Shot type, [TAGS] action, environment, lighting",
      "audio_segment": "Russian text for TTS"
    }}
  ]
}}
```

#### Выход Stage 2:

| Файл | Содержимое | Источник |
|------|------------|----------|
| `data/2_production_map.json` | episodes (сцены с visual_prompt + audio_segment), characters_metadata | Stage 2 (stage_2_scenes) |

---

### Stage 3: Референсы лиц (stage_3_draw_characters.py)

#### Входные переменные:

| Параметр | Откуда берется | Применяется | Язык |
|----------|----------------|-------------|------|
| `visual_style` | `data/visual_config.json.visual_style` | Генерация эталонных лиц | - |

**❗ ВАЖНО:** Stage 3 НЕ использует `visual_style` из шаблона!
- Он берет его из `data/visual_config.json`
- А `visual_config.json` создает AI в Stage 1

#### Код (stage_3_draw_characters.py:140-150):

```python
# Проверяем наличие персонажей
if visual_style and visual_style != "Not specified":
    ref_style = visual_style
else:
    ref_style = (
        "Gritty 2D hand-drawn illustration, bold ink outlines, "
        "dark moody atmosphere, graphic novel style, flat colors with messy textures, "
        "sharp contouring, high contrast, noir aesthetic."
    )
```

---

### Stage 4: Генерация сцен (stage_4_yandex_scenes.py)

#### Входные переменные:

| Параметр | Откуда берется | Применяется | Язык |
|----------|----------------|-------------|------|
| `visual_style` | `data/visual_config.json.visual_style` | Глобальный стиль всех кадров | - |

#### Код (stage_4_yandex_scenes.py:20-30):

```python
# ГЛОБАЛЬНЫЙ СТИЛЬ (держим коротким, ~100 симв.)
# Это гарантирует, что все кадры будут в одной "рисовке"
global_style = (
    "Hand-drawn 2D animation style, visible ink strokes, "
    "dark gloomy lighting, gritty atmosphere, deep shadows, "
    "cel shaded, cinematic comic book look, muffled colors."
)
```

---

## 3. ПРОМПТЫ В settings.json

### Старый формат (устаревший):

```json
{
  "prompts": {
    "stage_1_writer": "...",
    "stage_1_extractor": "...",
    "stage_2_scenes": "..."
  }
}
```

### Новый формат (с шаблонами):

```json
{
  "active_template_id": "manga-drama",
  "visual_style": "..."
}
```

**Важно:** `settings.json` больше НЕ хранит промпты! Он хранит только:
- `active_template_id` - ID активного шаблона
- `visual_style` - опциональный override

---

## 4. ИТОГОВАЯ СВОДКА

| ЭТАП | ПЕРЕМЕННАЯ | ШАБЛОН | ИСТОЧНИК | НАЗНАЧЕНИЕ |
|------|------------|--------|----------|------------|
| Stage 1 | `stage_1_writer` | ✅ | `prompts_json.stage_1_writer` | Генерация сценария (master + episodes) |
| Stage 1 | `stage_1_extractor` | ✅ | `prompts_json.stage_1_extractor` | Извлечение персонажей и visual_style |
| Stage 2 | `stage_2_scenes` | ✅ | `prompts_json.stage_2_scenes` | Генерация раскадровки |
| Stage 3 | `visual_style` | ❌ | `data/visual_config.json` | Стиль для генерации эталонов |
| Stage 4 | `visual_style` | ❌ | `data/visual_config.json` | Глобальный стиль для кадров |

**Суммарно:**
- **3 промпта в шаблоне**: stage_1_writer, stage_1_extractor, stage_2_scenes
- **0 промптов для TTS** (используются жёстко заданные настройки в stage_5_tts_yandex.py)

---

## 5. ПОЧЕМУ ОШИБКА В ПЕРВОМ ОТЧЕТЕ

В первом отчёте было указано что `visual_style` берётся из шаблона. Это **неверно**:

1. ✅ **Шаблон** содержит `settings_json.visual_style` - это **только дефолт**
2. ✅ **Stage 1 AI экстрактор** генерирует `visual_style` из сценария
3. ✅ **Stage 1 сохраняет** его в `data/visual_config.json`
4. ✅ **Stage 3-4 читают** из `data/visual_config.json` (не из шаблона!)

---

## 6. ФАЙЛЫ В PROMPTS FOLDER

| Файл | Назначение | Используется |
|------|------------|--------------|
| `writer_instruction.txt` | Промпт для Stage 1 writer | ✅ (fallback) |
| `extractor_instruction.txt` | Промпт для Stage 1 extractor | ✅ (fallback) |
| `stage_2_scenes.txt` | Промпт для Stage 2 | ✅ (fallback) |
| `structurer_instruction.txt` | Парсинг JSON | ❌ (не используется) |
| `voice_prompt_config.txt` | Настройки TTS | ❌ (не используется) |

**Все промпты используются ТОЛЬКО как fallback** когда БД недоступна!

---

## 7. ПОРЯДОК ЗАГРУЗКИ ПРОМПТОВ

### Stage 1:

```
1. Если template_id передан:
   → load from templates.prompts_json
   
2. Если prompts передан (из UI):
   → use prompts.stage_1_writer, prompts.stage_1_extractor
   
3. Иначе:
   → load from settings.json.prompts
   
4. Если пусто:
   → load from prompts/*.txt files
```

### Stage 2:

```
1. Если prompts передан:
   → use prompts.stage_2_scenes
   
2. Иначе:
   → get_active_template() → templates.prompts_json.stage_2_scenes
   
3. Если пусто:
   → load from prompts/stage_2_scenes.txt
```

---

## 8. ЗАКЛЮЧЕНИЕ

**Ключевые моменты:**

1. **В шаблоне 3 промпта** (stage_1_writer, stage_1_extractor, stage_2_scenes)
2. **Stage 1 использует 2 промпта** (writer + extractor)
3. **Stage 2 использует 1 промпт** (stage_2_scenes)
4. **Stage 3-4 НЕ используют промпты из шаблона** - они читают `visual_style` из `data/visual_config.json`
5. **`visual_style` в шаблоне - только дефолт**, фактический стиль генерирует AI в Stage 1
6. **TTS не использует промпты** - настройки захардкожены в stage_5_tts_yandex.py
