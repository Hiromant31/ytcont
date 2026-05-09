# 📋 ЗАДАНИЕ: ПЕРЕРАБОТКА СИСТЕМЫ ШАБЛОНОВ

## 🎯 ЦЕЛЬ

Сделать систему шаблонов гибкой, чтобы можно было создавать **множество отдельных промптов** для каждого этапа (Stage 1 и Stage 2), без ограничения количества промптов.

---

## 📊 ТЕКУЩЕЕ СОСТОЯНИЕ (ПРОБЛЕМЫ)

### 1. База данных (data/ytcont.db)

**Таблица `templates`:**
```sql
templates {
  id TEXT,
  name TEXT,
  description TEXT,
  category TEXT,
  prompts_json TEXT,   -- {"stage_1_writer": "...", "stage_1_extractor": "...", "stage_2_scenes": "..."}
  settings_json TEXT,
  created_at TEXT,
  updated_at TEXT,
  is_default INTEGER,
  archived INTEGER
}
```

**Проблемы:**
- Только 3 промпта в `prompts_json`: stage_1_writer, stage_1_extractor, stage_2_scenes
- Нельзя добавить новые промпты - структура фиксирована
- Все промпты в одной ячейке JSON

### 2. UI (main.py)

**Проблемы:**
- Кнопка "➕ Новый шаблон" открывает список существующих шаблонов (а не создаёт новый)
- Нет кнопки для создания пустого шаблона
- Редактор шаблона показывает 3 промпта в 1 строке ( Stage 1 Writer и Stage 1 Extractor в одной строке)

---

## ✅ ТРЕБОВАНИЯ

### 1. База данных - НОВАЯ СТРУКТУРА

**Новая таблица `templates`:**
```sql
templates {
  id TEXT PRIMARY KEY,       -- Уникальный идентификатор (например: "manga-drama-v1")
  name TEXT NOT NULL,        -- Читаемое название (например: "Манга-драма v1")
  description TEXT,          -- Описание шаблона
  category TEXT,             -- Категория (например: "Развлекательное")
  is_default INTEGER DEFAULT 0,
  archived INTEGER DEFAULT 0,
  created_at TEXT,
  updated_at TEXT
}
```

**Новая таблица `template_prompts`:**
```sql
template_prompts {
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  template_id TEXT NOT NULL,
  prompt_name TEXT NOT NULL,        -- Например: "stage_1_writer", "stage_1_extractor_story", "stage_2_scenes", "stage_2_scenes_split"
  prompt_text TEXT NOT NULL,        -- Текст промпта
  language TEXT DEFAULT 'ru',       -- Язык: 'ru', 'en'
  description TEXT,                 -- Описание промпта (для UI)
  sort_order INTEGER DEFAULT 0,
  FOREIGN KEY (template_id) REFERENCES templates(id)
}
```

**Новая таблица `template_settings`:**
```sql
template_settings {
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  template_id TEXT NOT NULL,
  setting_key TEXT NOT NULL,        -- Например: "visual_style", "camera_motion", "voice_style"
  setting_value TEXT NOT NULL,      -- Значение
  FOREIGN KEY (template_id) REFERENCES templates(id)
}
```

### 2. UI - НОВАЯ ЛОГИКА

**Кнопка в карточке шаблонов:**
```html
<!-- Было: -->
<button onclick="openTemplatesModal()">➕ Новый шаблон</button>

<!-- Стало: -->
<button onclick="openTemplatesList()">📋 Открыть шаблоны</button>
<button onclick="createNewTemplate()">➕ Новый шаблон</button>
```

**Templates List Modal:**
```html
<div class="modal-overlay" id="templates-modal">
  <div class="modal-box">
    <div class="modal-head">
      <span class="modal-title">🎭 Список шаблонов</span>
      <button class="modal-close" onclick="closeTemplatesModal()">✕</button>
    </div>
    <div class="modal-body" id="templates-list-container">
      <!-- Список шаблонов с кнопками "Выбрать" и "Редактировать" -->
    </div>
    <div class="modal-footer">
      <button onclick="createNewTemplate()">➕ Создать пустой шаблон</button>
      <button onclick="closeTemplatesModal()">✕ Закрыть</button>
    </div>
  </div>
</div>
```

**Edit Template Modal - НОВАЯ РАЗМЕТКА:**
```html
<div class="modal-overlay" id="edit-template-modal">
  <div class="modal-box">
    <div class="modal-head">
      <span class="modal-title">Редактор шаблона</span>
      <button class="modal-close" onclick="closeEditTemplateModal()">✕</button>
    </div>
    <div class="modal-body">
      <!-- Общие данные -->
      <input type="hidden" id="edit-template-id">
      
      <div class="form-row">
        <label>Название</label>
        <input type="text" id="edit-template-name">
      </div>
      
      <div class="form-row">
        <label>Категория</label>
        <input type="text" id="edit-template-category">
      </div>
      
      <div class="form-row">
        <label>Описание</label>
        <textarea id="edit-template-description"></textarea>
      </div>

      <!-- БЛОК: ДОБАВЛЕНИЕ ПРОМПТОВ -->
      <div class="prompts-section">
        <div class="section-header">
          <span>📝 Промпты</span>
          <button onclick="addPromptRow()">➕ Добавить промпт</button>
        </div>
        
        <div id="prompts-container">
          <!-- Промпты добавляются динамически -->
          <div class="prompt-row" data-prompt-id="1">
            <select class="prompt-name">
              <option value="stage_1_writer">Stage 1 Writer (Общий)</option>
              <option value="stage_1_writer_story">Stage 1 Writer (Story)</option>
              <option value="stage_1_writer_episode">Stage 1 Writer (Episode)</option>
              <option value="stage_1_writer_polish">Stage 1 Writer (Polish)</option>
              <option value="stage_1_extractor">Stage 1 Extractor</option>
              <option value="stage_2_scenes">Stage 2 Scenes</option>
              <option value="stage_2_scenes_split">Stage 2 Scenes (Split)</option>
              <option value="custom_prompt_1">Пользовательский 1</option>
              <!-- Можно добавить ещё... -->
            </select>
            
            <select class="prompt-lang">
              <option value="ru">RU</option>
              <option value="en">EN</option>
            </select>
            
            <textarea class="prompt-text"></textarea>
            
            <button class="btn-remove" onclick="removePromptRow(this)">🗑️</button>
          </div>
        </div>
      </div>

      <!-- БЛОК: НАСТРОЙКИ -->
      <div class="settings-section">
        <div class="section-header">
          <span>⚙️ Настройки</span>
          <button onclick="addSettingRow()">➕ Добавить настройку</button>
        </div>
        
        <div id="settings-container">
          <div class="setting-row">
            <input type="text" class="setting-key" placeholder="Ключ (например: visual_style)">
            <input type="text" class="setting-value" placeholder="Значение">
            <button class="btn-remove" onclick="removeSettingRow(this)">🗑️</button>
          </div>
        </div>
      </div>

      <!-- Кнопки сохранения -->
      <div class="modal-actions">
        <button onclick="deleteCurrentTemplate()">🗑️ Удалить</button>
        <button onclick="saveTemplate()">💾 Сохранить</button>
      </div>
    </div>
  </div>
</div>
```

### 3. API - НОВЫЕ ЭНДПОИНТЫ

**GET /api/templates** - Список всех шаблонов (с подсчётом промптов)

**POST /api/templates** - Создание нового шаблона
```json
{
  "id": "new-template-id",
  "name": "Новый шаблон",
  "description": "Описание",
  "category": "Развлекательное"
}
```

**POST /api/templates/:id/prompts** - Добавление промпта к шаблону
```json
{
  "prompt_name": "stage_1_writer",
  "prompt_text": "Текст промпта...",
  "language": "ru",
  "description": "Общий промпт для генерации сценария"
}
```

**PATCH /api/templates/:id/prompts/:prompt_id** - Изменение промпта

**DELETE /api/templates/:id/prompts/:prompt_id** - Удаление промпта

**GET /api/templates/:id/settings** - Получение настроек шаблона

**POST /api/templates/:id/settings** - Добавление/изменение настроек

**POST /api/templates/:id/apply** - Применение шаблона

### 4. Stage 1 и Stage 2 - ЗАГРУЗКА ПРОМПТОВ

**Стратегия загрузки:**

1. **Приоритет 1:** Проверить, есть ли активный шаблон
2. **Приоритет 2:** Загрузить все промпты из `template_prompts` для этого шаблона
3. **Приоритет 3:** Если промпта нет - использовать дефолтный (из файла или жёстко закодированный)
4. **Приоритет 4:** Если промпта нет и дефолтный тоже нет - ошибка

**Пример загрузки Stage 1:**
```python
# Загружаем все промпты для активного шаблона
template_prompts = db.query("""
    SELECT prompt_name, prompt_text, language, description
    FROM template_prompts
    WHERE template_id = ? AND archived = 0
""", (active_template_id,))

# Преобразуем в dict
prompts_dict = {p["prompt_name"]: p["prompt_text"] for p in template_prompts}

# Используем промпты
story_prompt = prompts_dict.get("stage_1_writer", STORY_PROMPT_DEFAULT)
extractor_prompt = prompts_dict.get("stage_1_extractor", EXTRACTOR_PROMPT_DEFAULT)
```

**Пример загрузки Stage 2:**
```python
scenes_prompt = prompts_dict.get("stage_2_scenes", SCENES_PROMPT_DEFAULT)
```

### 5. ВАЖНЫЕ МОМЕНТЫ

**Допустимое количество промптов:**
- Для Stage 1: сколько угодно (stage_1_writer, stage_1_writer_story, stage_1_writer_episode, stage_1_writer_polish, stage_1_extractor, stage_1_extractor_characters, stage_1_extractor_visual_style и т.д.)
- Для Stage 2: сколько угодно (stage_2_scenes, stage_2_scenes_split, stage_2_scenes_detailed и т.д.)
- Можно добавить новые промпты в UI через кнопку "➕ Добавить промпт"

**Разделение промптов:**
- Если есть `stage_1_writer` - он используется как общий для всех шагов (backward compatibility)
- Если есть `stage_1_writer_story`, `stage_1_writer_episode`, `stage_1_writer_polish` - они используются для соответствующих шагов
- Если есть `stage_2_scenes` - используется для Stage 2
- Если есть `stage_2_scenes_split` - можно использовать альтернативный формат

---

## 📝 АЛГОРИТМ РАБОТЫ

### Создание нового шаблона:

1. Пользователь нажимает "➕ Новый шаблон"
2. Открывается Edit Template Modal с пустыми полями
3. Пользователь заполняет:
   - Название
   - Категорию
   - Описание
   - Добавляет промпты через "➕ Добавить промпт"
   - Добавляет настройки через "➕ Добавить настройку"
4. Нажимает "💾 Сохранить"
5. Шаблон сохраняется в БД

### Выбор шаблона:

1. Пользователь нажимает "📋 Открыть шаблоны"
2. Открывается Templates List Modal с списком всех шаблонов
3. Пользователь выбирает шаблон и нажимает "Выбрать"
4. Шаблон применяется (обновляется `active_template_id` в settings)
5. Модалка закрывается

### Редактирование шаблона:

1. В списке шаблонов есть кнопка "⚙️ Редактировать"
2. Открывается Edit Template Modal с данными шаблона
3. Пользователь изменяет данные и нажимает "💾 Сохранить"

---

## 🎨 UI МАКЕТЫ (ТЕКСТОВЫЕ)

### Карточка "🎭 Prompt Templates" (sidebar):

```
🎭 Prompt Templates
┌─────────────────────────────────────────┐
│ 📋 Открыть шаблоны        ➕ Новый шаблон│
├─────────────────────────────────────────┤
│ 1. Манга-драма v1 (Развлекательное)    │
│    5 промптов 2 настройки              │
│    [⚙️ Редактировать] [🔄 Дублировать] │
│                                         │
│ 2. Трейлер-хоррор (Ужасы)               │
│    6 промптов 3 настройки               │
│    [⚙️ Редактировать] [🔄 Дублировать] │
└─────────────────────────────────────────┘
```

### Templates List Modal:

```
🎭 Список шаблонов                    [✕]
┌─────────────────────────────────────────┐
│ 1. Манга-драма v1                       │
│    Развлекательное | 5 промптов        │
│    [Выбрать] [⚙️ Редактировать]        │
├─────────────────────────────────────────┤
│ 2. Трейлер-хоррор                       │
│    Ужасы | 6 промптов                   │
│    [Выбрать] [⚙️ Редактировать]        │
├─────────────────────────────────────────┤
│ [➕ Создать пустой шаблон]              │
│ [✕ Закрыть]                            │
└─────────────────────────────────────────┘
```

### Edit Template Modal:

```
Редактор шаблона                      [✕]
┌─────────────────────────────────────────┐
│ Название: ____________________________  │
│ Категория: ___________________________  │
│ Описание:                               │
│ ┌─────────────────────────────────────┐ │
│ │     Текст описания шаблона...       │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ 📝 Промпты                 [➕ Добавить]│
│ ┌─────────────────────────────────────┐ │
│ │ [Stage 1 Writer] [RU]               │ │
│ │ ┌─────────────────────────────────┐ │ │
│ │ │ Текст промпта...                │ │ │
│ │ └─────────────────────────────────┘ │ │
│ │                                  [🗑️] │ │
│ ├─────────────────────────────────────┤ │
│ │ [Stage 1 Extractor] [EN]            │ │
│ │ ┌─────────────────────────────────┐ │ │
│ │ │ Текст промпта...                │ │ │
│ │ └─────────────────────────────────┘ │ │
│ │                                  [🗑️] │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ⚙️ Настройки               [➕ Добавить]│
│ ┌─────────────────────────────────────┐ │
│ │ [visual_style] [___________]    [🗑️]│ │
│ ├─────────────────────────────────────┤ │
│ │ [camera_motion] [___________]   [🗑️]│ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [🗑️ Удалить]               [💾 Сохранить]
└─────────────────────────────────────────┘
```

---

## 📊 МИГРАЦИЯ ДАННЫХ

**При первом запуске новой версии:**

1. Создать новые таблицы `template_prompts` и `template_settings`
2. Прочитать старые шаблоны из `templates.prompts_json`
3. Разбить JSON на отдельные записи в `template_prompts`
4. Сохранить в `settings` флаг `database_v2_migrated = true`

---

## ✅ КРИТЕРИИ ГОДНОСТИ

1. ✅ Можно создать новый шаблон с любым количеством промптов
2. ✅ Каждый промпт имеет своё поле в UI (не в одной ячейке)
3. ✅ Можно добавлять/удалять промпты через кнопки в UI
4. ✅ Можно создать пустой шаблон
5. ✅ Можно выбрать шаблон из списка
6. ✅ Stage 1 и Stage 2 загружают промпты из шаблона
7. ✅ Backward compatibility: если промпта нет, используется дефолтный
8. ✅ База данных нормализована (нет JSON в ячейках)

---

## 🚀 ПОРЯДОК РЕАЛИЗАЦИИ

**Этап 1: База данных**
1. Создать новые таблицы `template_prompts` и `template_settings`
2. Написать миграцию данных
3. Протестировать

**Этап 2: API**
1. Написать новые endpoints
2. Протестировать через curl/Postman

**Этап 3: UI**
1. Переделать кнопки и модалки
2. Добавить динамическое добавление промптов
3. Протестировать

**Этап 4: Stage 1/2**
1. Изменить загрузку промптов
2. Протестировать с новой БД

**Этап 5: UI-модалки**
1. Templates List Modal
2. Edit Template Modal с новой разметкой
