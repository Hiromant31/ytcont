# 🎭 Prompt Template System Flow

## Общая архитектура

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Template System                              │
├─────────────────────────────────────────────────────────────────────┤
│  БД: data/ytcont.db                                                 │
│  Таблицы: templates, template_versions                             │
│  Модуль: src/template_manager.py                                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Settings (runtime config)                          │
├─────────────────────────────────────────────────────────────────────┤
│  settings.json:                                                    │
│  {                                                                  │
│    "active_template_id": "manga-drama",  ← КЛЮЧЕВОЕ ПОЛЕ         │
│    "visual_style": "..."                 ← опционально            │
│    "prompts": {...}                      ← override               │
│    ...runtime config...                                             │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Orchestrator Pipeline                            │
├─────────────────────────────────────────────────────────────────────┤
│  Загружает активный шаблон → применяет промпты → запускает этапы  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Как шаблоны применяются в pipeline

### 1. Запуск pipeline (orchestrator.py)

```python
# Загружаем активный шаблон
active_template = get_active_template()

if active_template and not active_template.get("from_legacy"):
    template_prompts = json.loads(active_template.get("prompts_json", "{}"))
    # Объединяем промпты из шаблона с пользовательскими (user override)
    if prompts:
        template_prompts.update(prompts)
    prompts = template_prompts
```

**Где хранится активный шаблон:**
- В `settings.json` поле `active_template_id` (например: `"manga-drama"`)

---

### 2. Stage 1: Генерация сценария (stage_1_story.py)

```python
def run_stage_1(ai_settings=None, prompts=None, num_episodes=3, template_id=None):
    # Загрузка промптов из шаблона
    
    if template_id:
        template = get_template(template_id)
        template_prompts = json.loads(template.get("prompts_json", "{}"))
        prompts_dict = {
            "writer":    template_prompts.get("stage_1_writer", ""),
            "extractor": template_prompts.get("stage_1_extractor", "")
        }
    elif prompts and "stage_1_writer" in prompts:
        prompts_dict = {
            "writer":    prompts.get("stage_1_writer", ""),
            "extractor": prompts.get("stage_1_extractor", "")
        }
    else:
        prompts_dict = load_prompts_from_json()  # fallback
```

**Откуда берутся промпты:**
| Поле | Откуда | Куда применяется |
|------|--------|------------------|
| `stage_1_writer` | БД → `templates.prompts_json` | Для генерации master story и эпизодов |
| `stage_1_extractor` | БД → `templates.prompts_json` | Для извлечения персонажей и visual_style |

**Входные данные Stage 1:**
```
prompts_dict = {
    "writer": "Ты — сценарный движок для YouTube Shorts...",
    "extractor": "Role: Technical Character Extractor...",
    "idea": "Из idea.txt"
}
```

**Выходы Stage 1:**
```
data/1_base_structure.json:
{
    "master_story": "...",
    "episodes_raw": {"episode_1": "...", ...},
    "episodes_final": {"episode_1": "...", ...}
}

data/visual_config.json:
{
    "characters": {
        "Имя_Персонажа": "Описание (120-150 симв)",
        ...
    },
    "visual_style": "Gritty graphic novel style..."
}
```

**❗ Важно:** `visual_style` генерируется **AI экстрактором** на основе сценария, НЕ из шаблона!
- Шаблон содержит `visual_style` в `settings_json` — это дефолтное значение
- Но фактический `visual_style` всегда генерируется AI и сохраняется в `data/visual_config.json`
- Stage 3 и Stage 4 читают `visual_style` из `data/visual_config.json`

---

### 3. Stage 2: Раскадровка (stage_2_scenes.py)

```python
# Берем промпт из UI или из файла
system_instruction = prompts.get("stage_2_scenes", "")

# Если промпт не найден, пробуем из шаблона
if not system_instruction:
    active_template = get_active_template()
    if active_template and not active_template.get("from_legacy"):
        template_prompts = json.loads(active_template.get("prompts_json", "{}"))
        system_instruction = template_prompts.get("stage_2_scenes", "")
```

**Откуда берётся промпт:**
- `stage_2_scenes` из `templates.prompts_json` → сохраняется в `prompts.stage_2_scenes`

**Входные данные Stage 2:**
```
prompts = {
    "stage_2_scenes": "Role: Video Production Director..."
}

data/1_base_structure.json (из Stage 1)
data/visual_config.json (из Stage 1):
  - characters
  - visual_style
```

**Выход Stage 2:**
```
data/2_production_map.json:
{
    "episodes": {
        "episode_1": [
            {"scene_id": 1, "visual_prompt": "...", "audio_segment": "..."},
            ...
        ]
    },
    "characters_metadata": {...}
}
```

**Stage 4 читает из Stage 2:**
- `episodes` — для генерации кадров
- `characters_metadata` — для подстановки в visual_prompt

---

### 4. Stage 3: Референсы лиц

**Вход:**
```
data/visual_config.json (от Stage 1):
  - characters (описания персонажей)
  - visual_style (от AI экстрактора)
```

**Stage 3 использует `visual_style` из Stage 1** — он сгенерирован AI, а не берётся из шаблона.

---

### 5. Stage 4: Генерация сцен

**Вход:**
```
data/2_production_map.json (от Stage 2):
  - episodes (сцены с visual_prompt)
  - characters_metadata (описания персонажей)

data/visual_config.json (от Stage 1):
  - visual_style
```

**Stage 4** использует:
- `visual_prompt` из сцен (от Stage 2)
- `characters_metadata` для замены тегов [MAIN_1], [MAIN_2]
- `visual_style` из Stage 1 как глобальный стиль

---

## Структура шаблона в БД

```sql
CREATE TABLE templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    
    prompts_json TEXT NOT NULL,    -- ГЛАВНОЕ: промпты
    settings_json TEXT,             -- Доп. настройки (visual_style по умолчанию)
    
    created_at TEXT,
    updated_at TEXT,
    
    is_default INTEGER DEFAULT 0,
    archived INTEGER DEFAULT 0
);
```

### Формат `prompts_json`:

```json
{
  "stage_1_writer": "... long prompt ...",
  "stage_1_extractor": "... long prompt ...",
  "stage_2_scenes": "... long prompt ..."
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

**❗ Важно:** `settings_json.visual_style` — это **только дефолтное значение**!
- Фактический стиль генерируется AI в Stage 1
- Сохраняется в `data/visual_config.json`
- Используется во всех последующих этапах

---

## Цепочка применения шаблона

```
1. Пользователь выбирает шаблон → нажимает "Применить"
   ↓
2. Шаблон ID сохраняется в settings.json: "active_template_id": "..."
   ↓
3. При запуске pipeline:
   - Orchestrator загружает активный шаблон
   - Извлекает prompts_json → применяет промпты в stage_1, stage_2
   ↓
4. Stage 1:
   - stage_1_writer → генерирует сценарий
   - stage_1_extractor → извлекает characters + visual_style (от AI)
   - visual_style сохраняется в data/visual_config.json
   ↓
5. Stage 2:
   - stage_2_scenes → генерирует раскадровку
   - Использует visual_style из data/visual_config.json (не из шаблона!)
   ↓
6. Stage 3-4:
   - Читают visual_style из data/visual_config.json (от Stage 1)
```

---

## Где хранятся данные и откуда берутся

| Данные | Где хранятся | Откуда берутся в pipeline |
|--------|--------------|---------------------------|
| `stage_1_writer` | `templates.prompts_json` | Stage 1 из шаблона |
| `stage_1_extractor` | `templates.prompts_json` | Stage 1 из шаблона |
| `stage_2_scenes` | `templates.prompts_json` | Stage 2 из шаблона |
| `visual_style` (фактический) | `data/visual_config.json` | Stage 1 AI экстрактор |
| `characters` | `data/visual_config.json` | Stage 1 AI экстрактор |
| `episodes_raw/final` | `data/1_base_structure.json` | Stage 1 |
| `episodes` (сцены) | `data/2_production_map.json` | Stage 2 |

---

## Fallback система

Если шаблоны недоступны (нет БД или шаблона):

```
1. Проверка active_template_id в settings.json
2. Проверка templates.prompts_json
3. Fallback: load_prompts_from_files() → prompts/*.txt
4. Fallback: load_prompts_from_json() → settings.json.prompts
```

---

## Кнопки UI и их действия

| Кнопка | Действие |
|--------|----------|
| `➕ Новый шаблон` | Открывает modal для создания пустого шаблона |
| `✎` (редактировать) | Загружает шаблон в modal для правки |
| `💾 Сохранить` | Создаёт (если ID пустой) или обновляет шаблон |
| `⧉` (дублировать) | Создаёт копию шаблона с суффиксом `_copy_...` |
| `🗑️` (удалить) | Удаляет шаблон из БД |
| `Архив/Разархив` | Скрывает/показывает шаблон (archived=1/0) |
| `Выбрать` в modal | Сохраняет ID в `selectedTemplateId` |
| `Применить шаблон` | POST /api/templates/{id}/apply → сохраняет в settings.json |

---

## Пример полного потока

```
1. Создаю шаблон "True Crime":
   - id: "true-crime"
   - prompts_json: {"stage_1_writer": "...Crime style...", ...}
   - settings_json: {"visual_style": "Dark noir"}

2. Применяю шаблон → сохраняется в settings.json:
   { "active_template_id": "true-crime" }

3. Запускаю pipeline:
   - Orchestrator читает active_template_id
   - Загружает True Crime шаблон
   - Применяет stage_1_writer, stage_1_extractor, stage_2_scenes
   
4. Stage 1:
   - Генерирует сценарий в стиле True Crime
   - AI экстрактор извлекает visual_style (но уже из сценария!)
   
5. Stage 2-4:
   - Используют visual_style из data/visual_config.json (от AI)
```

---

## Заключение

**Ключевые моменты:**

1. **Шаблоны управляют промптами**, а не поведением pipeline
2. **`visual_style` всегда генерируется AI** — шаблон только дефолт
3. **Pipeline загружает шаблон один раз в начале** (orchestrator)
4. **Stage 1 сохраняет `visual_style` в файл** → Stage 3-4 читают оттуда
5. **settings.json хранит только ID шаблона**, не промпты
