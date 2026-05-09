# 📊 ПОЛНЫЙ ОТЧЕТ: Переменные и их применение в Template System

## ✅ ИСПРАВЛЕНИЕ

**Проблема:** В оригинальном коде Stage 1 использовал жёстко закодированные промпты (STORY_PROMPT, EPISODE_PROMPT, POLISH_PROMPT), которые **НЕ БЕРУТСЯ** из шаблона в БД.

**Решение:** Изменён `stage_1_story.py` чтобы загружать промпты из шаблона и разбивать их на 3 части для разных шагов.

---

## 1. СТРУКТУРА ПРОМПТОВ В ШАБЛОНЕ (БД)

### База данных: `data/ytcont.db`

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

## 2. ИСПРАВЛЕННЫЙ КОД stage_1_story.py

### Загрузка промптов из шаблона (ПРИОРИТЕТ 2):

```python
# ── ЗАГРУЗКА ПРОМПТОВ ИЗ ШАБЛОНА (ПРИОРИТЕТ) ──
template_prompts = None

# Сначала пробуем получить активный шаблон
active_template = get_active_template()
if active_template and not active_template.get("from_legacy"):
    try:
        template_prompts = json.loads(active_template.get("prompts_json", "{}"))
        print(f"   🎭 Загружен шаблон: {active_template.get('id', 'unknown')}")
    except Exception as e:
        print(f"   ⚠️  Ошибка загрузки шаблона: {e}")

# ── Промпты ──
if prompts and "stage_1_writer" in prompts:
    # Приоритет 1: prompts из вызова API
    prompts_dict = {
        "writer":    prompts.get("stage_1_writer", ""),
        "extractor": prompts.get("stage_1_extractor", "")
    }
    print("   Используем промпты из вызова")
elif template_prompts and template_prompts.get("stage_1_writer"):
    # Приоритет 2: промпты из шаблона
    prompts_dict = {
        "writer":    template_prompts.get("stage_1_writer", ""),
        "extractor": template_prompts.get("stage_1_extractor", "")
    }
    print("   Используем промпты из шаблона (БД)")
else:
    # Приоритет 3: fallback к legacy
    prompts_dict = load_prompts_from_json()
    if not prompts_dict["writer"] or not prompts_dict["extractor"]:
        print("⚠️ Промпты не найдены в settings.json, загружаю из файлов...")
        file_prompts = load_prompts_from_files()
        if not file_prompts["writer"]:
            print("❌ Ошибка: Не найден промпт writer_instruction.txt")
            return False
        prompts_dict = file_prompts
```

### Разделение промптов на 3 части:

```python
# ── РАЗДЕЛЕНИЕ ПРОМПТОВ ИЗ stage_1_writer ──
# Промпт stage_1_writer может содержать 3 части через разделители:
# - STORY_PROMPT (для генерации master story)
# - EPISODE_PROMPT (для генерации эпизодов)
# - POLISH_PROMPT (для полиша под озвучку)

if prompts_dict["writer"]:
    writer_parts = _split_writer_prompt(prompts_dict["writer"])
    prompts_dict["writer_story"] = writer_parts.get("story", prompts_dict["writer"])
    prompts_dict["writer_episode"] = writer_parts.get("episode", prompts_dict["writer"])
    prompts_dict["writer_polish"] = writer_parts.get("polish", prompts_dict["writer"])
    print("   ✅ Промпты разделены на STORY/EPISODE/POLISH")
else:
    # Fallback если нет разделителей
    prompts_dict["writer_story"] = prompts_dict["writer"]
    prompts_dict["writer_episode"] = prompts_dict["writer"]
    prompts_dict["writer_polish"] = prompts_dict["writer"]
```

### Использование в вызовах AI:

```python
# Генерация master story
story_prompt = prompts_dict.get("writer_story", STORY_PROMPT)
story_prompt_dynamic = story_prompt.replace("{NUM_EPISODES}", str(num_episodes))
master_story = call_ai_text(..., story_prompt_dynamic, ...)

# Генерация эпизодов
episode_prompt = prompts_dict.get("writer_episode", EPISODE_PROMPT)
episode_raw = call_ai_text(..., episode_prompt.format(...), ...)

# Полиш под озвучку
polish_prompt = prompts_dict.get("writer_polish", POLISH_PROMPT)
episode_final = call_ai_text(..., polish_prompt, ...)
```

---

## 3. ФУНКЦИЯ _split_writer_prompt()

```python
def _split_writer_prompt(text: str) -> dict:
    """
    Разделяет единый промпт stage_1_writer на 3 части:
    - story: для генерации master story
    - episode: для генерации эпизодов
    - polish: для полиша под озвучку
    
    Формат: "---STORY---\n...\n---EPISODE---\n...\n---POLISH---\n..."
    """
    result = {"story": "", "episode": "", "polish": ""}
    parts = re.split(r'---(?:STORY|EPISODE|POLISH)---\s*\n?', text, flags=re.IGNORECASE)
    
    if len(parts) >= 2:
        result["story"] = parts[1].strip()
    else:
        result["story"] = text.strip()
    
    if len(parts) >= 3:
        result["episode"] = parts[2].strip()
    else:
        result["episode"] = text.strip()
    
    if len(parts) >= 4:
        result["polish"] = parts[3].strip()
    else:
        result["polish"] = text.strip()
    
    return result
```

**Пример использования:**
```
Вход: "---STORY---\nСтрока 1\n---EPISODE---\nСтрока 2\n---POLISH---\nСтрока 3"
Выход: {"story": "Строка 1", "episode": "Строка 2", "polish": "Строка 3"}
```

**Если разделителей нет:** используется один общий промпт для всех шагов.

---

## 4. ИТОГОВАЯ СВОДКА ПЕРЕМЕННЫХ

| ЭТАП | ПЕРЕМЕННАЯ | ШАБЛОН | ИСПОЛЬЗУЕТСЯ | ОПИСАНИЕ |
|------|------------|--------|---------------|----------|
| Stage 1 | `stage_1_writer` | ✅ | ✅ | Общий промпт для генерации сценария (разбивается на 3 части) |
| Stage 1 | `stage_1_writer.story` | ✅ | ✅ | Для генерации master story |
| Stage 1 | `stage_1_writer.episode` | ✅ | ✅ | Для генерации эпизодов |
| Stage 1 | `stage_1_writer.polish` | ✅ | ✅ | Для полиша под озвучку |
| Stage 1 | `stage_1_extractor` | ✅ | ✅ | Для извлечения персонажей и visual_style |
| Stage 2 | `stage_2_scenes` | ✅ | ✅ | Для генерации раскадровки |
| Stage 3-4 | `visual_style` | ❌ | ❌ | Берётся из `data/visual_config.json` (AI экстрактор Stage 1) |

---

## 5. ПОРЯДОК ЗАГРУЗКИ ПРОМПТОВ

```
1. Если prompts передан (из API вызова):
   → use prompts.stage_1_writer, prompts.stage_1_extractor

2. Иначе если активный шаблон найден:
   → load from templates.prompts_json

3. Иначе:
   → load from settings.json.prompts

4. Если пусто:
   → load from prompts/*.txt files (fallback)
```

---

## 6. ПРИМЕРЫ

### Пример 1: Промпт с разделителями

```json
{
  "stage_1_writer": "---STORY---\nТы — сценарист...\n---EPISODE---\nТы — Story Engine...\n---POLISH---\nТы — редактор..."
}
```

### Пример 2: Промпт без разделителей (fallback)

```json
{
  "stage_1_writer": "Ты — сценарный движок (Story Engine) для вирусного YouTube Shorts..."
}
```

В этом случае один промпт используется для всех 3 шагов.

---

## 7. ИЗМЕНЕННЫЕ ФАЙЛЫ

| Файл | Изменения |
|------|-----------|
| `src/stage_1_story.py` | Добавлена загрузка промптов из шаблона, функция `_split_writer_prompt`, использование `prompts_dict["writer_story"]`, `prompts_dict["writer_episode"]`, `prompts_dict["writer_polish"]` вместо жёстко закодированных промптов |

---

## 8. ЗАКЛЮЧЕНИЕ

**Что изменилось:**

1. ✅ Stage 1 теперь загружает `stage_1_writer` из шаблона в БД
2. ✅ Промпт разбивается на 3 части: `writer_story`, `writer_episode`, `writer_polish`
3. ✅ Используются эти части в вызовах AI вместо жёстко закодированных промптов
4. ✅ Если разделителей нет, используется один общий промпт (fallback)
5. ✅ Порядок приоритетов: API → БД → settings.json → файлы

**Как использовать:**

1. Создать новый шаблон в UI
2. В поле `stage_1_writer` ввести текст с разделителями:
   ```
   ---STORY---
   Ты — сценарист...
   ---EPISODE---
   Ты — Story Engine...
   ---POLISH---
   Ты — редактор...
   ```
3. Сохранить шаблон
4. Активировать шаблон
5. Запустить Stage 1 - он будет использовать промпты из шаблона!
