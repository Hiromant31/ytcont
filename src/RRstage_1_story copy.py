import os
import json
import time
import re
import traceback
from pathlib import Path
from dotenv import load_dotenv
from .template_manager import get_active_template
import openai

load_dotenv()


# ─────────────────────────────────────────────
#  STORY PIPELINE PROMPTS
# ─────────────────────────────────────────────

STORY_PROMPT = """
Ты — сценарист сериалов короткого формата.

На основе идеи создай цельную историю из {NUM_EPISODES} эпизодов по 60 секунд каждый.

Требования:
- 2–3 главных героя (отдельные личности)
- ГРУППЫ ЛЮДЕЙ (семья, толпа, банда, команда) = ОДИН персонаж
- один центральный конфликт
- чёткая арка: завязка → эскалация → развязка
- обязательно:
  - скрытая правда
  - поворот в середине
  - сильный финальный удар

Формат:

TITLE:

CHARACTERS:
- имя + роль (если это группа — указать "Семья Ивановых", "Толпа зевак", "Банда байкеров")

CORE CONFLICT:

EPISODE PLAN:

EP1 (60 сек):
EP2 (60 сек):
EP3 (60 сек):

IMPORTANT:
- только структура, без художественного текста
"""

EPISODE_PROMPT = """
Ты — Story Engine для коротких видео (СТРОГО 60 секунд).

Вот структура истории:
{MASTER_STORY}

Напиши эпизод: {EPISODE_NUMBER}

Длина: 100–120 слов (это ~60 секунд озвучки)

СТРУКТУРА:
HOOK: (0-3 сек)
START: (3-15 сек)
BUILD: (15-45 сек)
IMPACT: (45-70 сек)
END: (70-90 сек)

ТРЕБОВАНИЯ:
- связный рассказ (не обрывки)
- предложения 5–10 слов
- без диалогов
- быстрый темп
- минимум 1 поворот
- СТРОГО 60 секунд при озвучке

ЗАПРЕТ:
- не задавать вопросы
- не просить данные
"""

POLISH_PROMPT = """
Ты — редактор voice-over сценариев.

Перепиши текст так, чтобы он идеально звучал вслух за 60 секунд.

Требования:
- сохранить смысл 100%
- убрать обрывки
- сделать плавный рассказ
- итоговый текст = 100-120 слов (60 секунд озвучки)

Формат сохранить:

TITLE:
HOOK:
START:
BUILD:
IMPACT:
END:
"""


# ─────────────────────────────────────────────
#  SETTINGS / PROMPTS LOADERS
# ─────────────────────────────────────────────

def load_settings():
    if os.path.exists("settings.json"):
        with open("settings.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "ai_settings": {
            "text": {
                "api_url":   "https://ai.api.cloud.yandex.net/v1",
                "api_key":   "",
                "folder_id": "",
                "model":     "gemma-3-27b-it/latest",
                "provider":  "yandex"
            }
        },
        "prompts": {
            "stage_1_writer":    "",
            "stage_1_extractor": ""
        }
    }


# ─────────────────────────────────────────────
#  PROMPT SPLITTER (разделяет stage_1_writer на 3 части)
# ─────────────────────────────────────────────

def _split_writer_prompt(text: str) -> dict:
    """
    Разделяет единый промпт stage_1_writer на 3 части:
    - story: для генерации master story
    - episode: для генерации эпизодов
    - polish: для полиша под озвучку
    
    Формат: "---STORY---\n...\n---EPISODE---\n...\n---POLISH---\n..."
    """
    result = {
        "story": "",
        "episode": "",
        "polish": ""
    }
    
    # Ищем разделители
    parts = re.split(r'---(?:STORY|EPISODE|POLISH)---\s*\n?', text, flags=re.IGNORECASE)
    
    # parts[0] = текст до первого разделителя (или весь текст если нет разделителей)
    # parts[1] = текст после ---STORY--- до ---EPISODE---
    # parts[2] = текст после ---EPISODE--- до ---POLISH---
    # parts[3] = текст после ---POLISH---
    
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


def load_prompts_from_json():
    settings = load_settings()
    return {
        "writer":    settings.get("prompts", {}).get("stage_1_writer", ""),
        "extractor": settings.get("prompts", {}).get("stage_1_extractor", "")
    }


def load_prompts_from_files():
    try:
        idea          = Path("idea.txt").read_text(encoding="utf-8")
        writer_sys    = Path("prompts/writer_instruction.txt").read_text(encoding="utf-8")
        extractor_sys = Path("prompts/extractor_instruction.txt").read_text(encoding="utf-8")
        return {"writer": writer_sys, "extractor": extractor_sys, "idea": idea}
    except FileNotFoundError:
        return {"writer": "", "extractor": "", "idea": ""}


# ─────────────────────────────────────────────
#  JSON REPAIR UTILITIES
# ─────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    """Убирает ```json ... ``` обёртку если есть."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()


def _walk(text: str):
    """
    Итерируется по символам, корректно обрабатывая escape и строки.
    Yield: (index, char, in_string_before_this_char).
    Переносы строк внутри JSON-строк обрабатываются корректно.
    """
    in_string = False
    escape = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if escape:
            escape = False
            yield i, ch, in_string
            i += 1
            continue
        if in_string:
            if ch == '\\':
                escape = True
                yield i, ch, True
                i += 1
                continue
            if ch == '"':
                in_string = False
                yield i, ch, False   # закрывающая кавычка — уже вне строки
                i += 1
                continue
            yield i, ch, True
        else:
            if ch == '"':
                in_string = True
                yield i, ch, False   # открывающая кавычка
                i += 1
                continue
            yield i, ch, False
        i += 1


def _find_last_complete_root(text: str) -> int:
    """
    Возвращает позицию (включительно) последней закрывающей скобки
    верхнеуровневого объекта/массива. -1 если не найдено.
    """
    depth = 0
    last_valid = -1
    for i, ch, in_str in _walk(text):
        if in_str:
            continue
        if ch in '{[':
            depth += 1
        elif ch in '}]':
            depth -= 1
            if depth == 0:
                last_valid = i
    return last_valid


def _close_open_structure(text: str) -> str:
    """
    Если JSON обрезан на середине строки-значения:
      1. Откатывается до последней запятой перед незакрытой строкой.
      2. Дописывает нужные закрывающие скобки.
    Если JSON обрезан между элементами — просто закрывает скобки.
    """
    # Определяем есть ли незакрытая строка и где последняя запятая вне строк
    in_str = False
    str_start = -1
    last_comma_pos = -1
    prev_was_colon = False

    for i, ch, _ in _walk(text):
        if ch == '"':
            if in_str:
                in_str = False
                str_start = -1
            else:
                in_str = True
                str_start = i
            prev_was_colon = False
        elif ch == ':':
            prev_was_colon = True
        elif ch == ',':
            last_comma_pos = i
            prev_was_colon = False
        else:
            if ch not in ' \t\n\r':
                prev_was_colon = False

    # Если строка не закрыта — откатываемся до последней запятой
    if in_str and str_start >= 0:
        if last_comma_pos >= 0:
            text = text[:last_comma_pos]
        else:
            # нет запятой — обрезаем до открывающей скобки объекта/массива
            text = text[:str_start]

    text = text.rstrip()
    text = re.sub(r',\s*$', '', text)

    # Строим стек открытых скобок
    stack = []
    for i, ch, in_str in _walk(text):
        if in_str:
            continue
        if ch in '{[':
            stack.append(ch)
        elif ch in '}]':
            if stack:
                stack.pop()

    closing = ''.join('}' if c == '{' else ']' for c in reversed(stack))
    return text + closing


def _extract_complete_array_items(text: str) -> list:
    """
    Извлекает полностью закрытые элементы из массива.
    Возвращает список, даже если массив не закрыт до конца.
    """
    text = text.strip()
    if not text.startswith('['):
        raise ValueError("Массив должен начинаться с '['")

    result = []
    depth = 0
    current_item = []
    in_string = False
    escape = False

    for i, ch in enumerate(text):
        if escape:
            current_item.append(ch)
            escape = False
            continue
        
        if in_string:
            current_item.append(ch)
            if ch == '\\':
                escape = True
            elif ch == '"':
                in_string = False
            continue
            
        if ch == '"':
            in_string = True
            current_item.append(ch)
            continue
            
        if ch in '{[':
            depth += 1
            current_item.append(ch)
        elif ch in '}]':
            depth -= 1
            current_item.append(ch)
            if depth == 0 and ch == '}':
                # Конец объекта
                item_str = ''.join(current_item).strip()
                if item_str:
                    try:
                        result.append(json.loads(item_str))
                    except:
                        pass
                current_item = []
        elif ch == ',' and depth == 1:
            # Запятая между элементами массива
            continue
        elif depth > 0:
            current_item.append(ch)
            
    return result


def repair_truncated_json(raw_text: str):
    """
    Универсальный парсер JSON который обрабатывает:
    1. Markdown обёртки ```json```
    2. Обрезанные объекты/массивы
    3. Незакрытые строки
    4. Массивы с неполными элементами
    
    Возвращает распарсенный JSON dict/list или бросает исключение.
    """
    text = _strip_markdown(raw_text)
    
    # Попытка прямого парсинга
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Находим последнюю закрытую структуру
    last_close = _find_last_complete_root(text)
    if last_close >= 0:
        candidate = text[:last_close+1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    
    # Пробуем закрыть структуру
    closed = _close_open_structure(text)
    try:
        return json.loads(closed)
    except json.JSONDecodeError:
        pass
    
    # Если это массив — извлекаем полные элементы
    if text.strip().startswith('['):
        try:
            items = _extract_complete_array_items(text)
            if items:
                return items
        except:
            pass
    
    raise ValueError(f"Не удалось распарсить JSON после всех попыток восстановления")


# ─────────────────────────────────────────────
#  AI API CALLS
# ─────────────────────────────────────────────

def call_ai_extractor(client, is_yandex, folder_id, model, system_prompt, user_text, max_tokens=3000, max_retries=2):
    """
    Вызывает AI для извлечения визуального конфига с поддержкой retry.
    Возвращает dict с keys: characters, visual_style
    """
    for attempt in range(max_retries):
        try:
            print(f"   🔄 Попытка {attempt + 1}/{max_retries}")
            
            raw_response = call_ai_text(
                client=client,
                is_yandex=is_yandex,
                folder_id=folder_id,
                model=model,
                system_prompt=system_prompt,
                user_input=user_text,
                max_tokens=max_tokens
            )
            
            # Парсим JSON
            parsed = repair_truncated_json(raw_response)
            
            # Валидация структуры
            if not isinstance(parsed, dict):
                raise ValueError(f"Ожидался dict, получен {type(parsed).__name__}")
            
            if "characters" not in parsed:
                raise ValueError("Отсутствует ключ 'characters' в ответе")
            
            # Нормализация characters
            chars = parsed["characters"]
            if isinstance(chars, list):
                # Преобразуем список в словарь
                normalized_chars = {}
                for i, item in enumerate(chars):
                    if isinstance(item, dict) and "name" in item:
                        normalized_chars[item["name"]] = item.get("description", str(item))
                    elif isinstance(item, dict):
                        normalized_chars[f"Character_{i+1}"] = str(item)
                    else:
                        normalized_chars[f"Character_{i+1}"] = str(item)
                parsed["characters"] = normalized_chars
            elif not isinstance(chars, dict):
                parsed["characters"] = {}
            
            # Добавляем visual_style если отсутствует
            if "visual_style" not in parsed:
                parsed["visual_style"] = "Not specified"
            
            print(f"   ✅ Успешный парсинг (попытка {attempt + 1})")
            return parsed
            
        except Exception as e:
            print(f"   ❌ Ошибка на попытке {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2)


def call_ai_text(client, is_yandex, folder_id, model, system_prompt, user_input, max_tokens=4000):
    """
    Универсальный вызов AI для получения текста.
    Поддерживает Yandex и OpenAI совместимые API.
    """
    try:
        if is_yandex:
            response = client.responses.create(
                model=f"gpt://{folder_id}/{model}",
                temperature=0.7,
                instructions=system_prompt,
                input=user_input,
                max_output_tokens=max_tokens
            )
            result = response.output_text
        else:
            # DeepSeek reasoning поддержка: увеличиваем токены для моделей с reasoning
            is_deepseek = "deepseek" in model.lower()
            actual_max_tokens = max_tokens * 3 if is_deepseek else max_tokens
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.7,
                max_tokens=actual_max_tokens
            )
            
            if not response.choices:
                raise Exception(f"Нет choices в ответе: {response}")
                
            choice = response.choices[0]
            msg = choice.message
            
            # Проверка на обрыв по лимиту токенов
            if choice.finish_reason == 'length':
                raise Exception(f"Не хватило max_tokens ({max_tokens}). Модель оборвала ответ на полуслове или не успела закончить reasoning.")
                
            if msg is None or msg.content is None:
                # Включаем содержимое reasoning в ошибку для отладки
                reasoning = getattr(msg, 'reasoning', 'Нет данных reasoning')
                raise Exception(f"Нет content в ответе. Возможно, модель ушла в reasoning: {reasoning}")
                
            result = str(msg.content)

        return result.strip() if result else ""
    except Exception as e:
        raise Exception(f"AI ошибка: {e}")

# ─────────────────────────────────────────────
#  MAIN STAGE 1
# ─────────────────────────────────────────────

def run_stage_1(ai_settings=None, prompts=None, num_episodes=3):
    """Stage 1: Генерация сценария + извлечение визуального конфига."""
    print(f"🚀 Запуск Stage 1: Генерация истории ({num_episodes} эпизодов)...")

    # ── Настройки AI ──
    settings = load_settings()

    if ai_settings and "text" in ai_settings:
        ai_text = ai_settings["text"]
        print("   Используем переданные настройки AI")
    else:
        ai_text = settings.get("ai_settings", {}).get("text", {})
        print("   Используем настройки из settings.json")

    api_url   = ai_text.get("api_url",   "https://ai.api.cloud.yandex.net/v1")
    api_key   = ai_text.get("api_key",   "")
    folder_id = ai_text.get("folder_id", "")
    model     = ai_text.get("model",     "gemma-3-27b-it/latest")
    is_yandex = "yandex" in api_url.lower() or "ai.api.cloud.yandex" in api_url

    # ── ЗАГРУЗКА ПРОМПТОВ ИЗ ШАБЛОНА (ПРИОРИТЕТ V2) ──
    template_prompts_v2 = None
    
    # Сначала пробуем получить активный шаблон (V2 структура)
    active_template = get_active_template()
    if active_template and not active_template.get("from_legacy"):
        template_id = active_template.get("id")
        if template_id:
            try:
                from .template_manager import get_template_prompts, get_template_settings
                template_prompts_v2 = get_template_prompts(template_id)
                template_settings = get_template_settings(template_id)
                
                if template_prompts_v2:
                    print(f"   🎭 Загружен шаблон (V2): {template_id}")
                    print(f"   📝 Промптов найдено: {len(template_prompts_v2)}")
                    
                    # Преобразуем список в dict
                    prompts_from_db = {p["prompt_name"]: p["prompt_text"] for p in template_prompts_v2}
                    prompts_dict = {
                        "writer":    prompts_from_db.get("stage_1_writer", ""),
                        "extractor": prompts_from_db.get("stage_1_extractor", "")
                    }
                    print("   ✅ Промпты загружены из новых таблиц")
                else:
                    # Fallback к старой структуре
                    template_prompts = json.loads(active_template.get("prompts_json", "{}"))
                    prompts_dict = {
                        "writer":    template_prompts.get("stage_1_writer", ""),
                        "extractor": template_prompts.get("stage_1_extractor", "")
                    }
                    print("   ⚠️  Используем старую структуру prompts_json")
            except Exception as e:
                print(f"   ⚠️  Ошибка загрузки шаблона: {e}")
                prompts_dict = load_prompts_from_json()
        else:
            prompts_dict = load_prompts_from_json()
    else:
        prompts_dict = load_prompts_from_json()

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

    # ── Идея ──
    try:
        idea = Path("idea.txt").read_text(encoding="utf-8")
        prompts_dict["idea"] = idea
    except FileNotFoundError:
        print("❌ Ошибка: Не найден idea.txt")
        return False

    # ── Валидация ──
    if not api_key:
        print("❌ Ошибка: Не задан api_key в настройках AI")
        return False
    if is_yandex and not folder_id:
        print("❌ Ошибка: Для Yandex AI нужен folder_id")
        return False
    if not is_yandex:
        print("ℹ️  non-Yandex API — folder_id не требуется")

    # ── Клиент ──
    try:
        if is_yandex:
            client = openai.OpenAI(api_key=api_key, base_url=api_url, project=folder_id)
            print("   ✓ Подключено к Yandex AI API")
        else:
            client = openai.OpenAI(api_key=api_key, base_url=api_url)
            print(f"   ✓ Подключено к API: {api_url}")
    except Exception as e:
        print(f"❌ Ошибка инициализации клиента: {e}")
        return False

    # ─────────────────────────────────────────────
    #  NEW STORY PIPELINE ({num_episodes} episodes × 60 seconds)
    # ─────────────────────────────────────────────
    episodes_raw = {}   # Новое: для хранения сырых текстов
    episodes_final = {} # Для финальных

    print(f"🧠 Генерируем master story ({num_episodes} эпизодов по 60 сек)...")

    # Используем промпт из шаблона (или дефолтный)
    story_prompt = prompts_dict.get("writer_story", STORY_PROMPT)
    story_prompt_dynamic = story_prompt.replace("{NUM_EPISODES}", str(num_episodes))
    master_story = call_ai_text(
        client,
        is_yandex,
        folder_id,
        model,
        story_prompt_dynamic,
        prompts_dict.get("idea", ""),
        max_tokens=4000
    )

    print("   ✓ Master story готов")

    episodes = {}

    print("✍️ Генерируем эпизоды (каждый 60 секунд)...")

    for i in range(1, num_episodes + 1):
        print(f"   ∟ episode_{i} (таймлимит: 60 сек)...")

        # Генерация эпизода
        episode_prompt = prompts_dict.get("writer_episode", EPISODE_PROMPT)
        episode_raw = call_ai_text(
            client,
            is_yandex,
            folder_id,
            model,
            episode_prompt.format(
                MASTER_STORY=master_story,
                EPISODE_NUMBER=i
            ),
            "",
            max_tokens=4000
        )
        episodes_raw[f"episode_{i}"] = episode_raw # Сохраняем сырой

        # Полиш под озвучку
        polish_prompt = prompts_dict.get("writer_polish", POLISH_PROMPT)
        episode_final = call_ai_text(
            client,
            is_yandex,
            folder_id,
            model,
            polish_prompt,
            episode_raw,
            max_tokens=4000
        )

        episodes_final[f"episode_{i}"] = episode_final # Сохраняем финальный

        time.sleep(1)

    # сохраняем
    os.makedirs("data", exist_ok=True)

    with open("data/1_base_structure.json", "w", encoding="utf-8") as f:
        json.dump({
            "master_story": master_story,
            "episodes_raw": episodes_raw,     # Новое поле
            "episodes_final": episodes_final  # Обновленное поле
        }, f, ensure_ascii=False, indent=2)

    print("   ✓ Pipeline завершён → data/1_base_structure.json")

    # ── 3. ЭКСТРАКТОР ──
    print("\n" + "="*60)
    print("👤 [EXTRACTOR MODULE] Извлекаем персонажей и визуальный стиль...")
    print("="*60)
    
    # Собираем весь текст сценария для анализа
    full_text = "\n\n".join(episodes_final.values())
    print(f"📝 [EXTRACTOR] Анализируемый текст: {len(full_text)} символов")
    print(f"   Эпизодов: {len(episodes_final)}")
    
    # Формируем системный промпт для экстрактора
    extractor_system = (
        prompts_dict["extractor"].strip()
        + "\n\n"
        "=== СТРОГИЕ ПРАВИЛА ФОРМАТА ===\n"
        "- Верни ТОЛЬКО JSON, без текста вокруг, без ``` блоков.\n"
        "- Структура JSON должна быть такой:\n"
        '  {\n'
        '    "characters": {\n'
        '      "Имя_Персонажа": "Описание внешности (120-150 символов)",\n'
        '      "Другой_Персонаж": "Описание"\n'
        '    },\n'
        '    "visual_style": "Описание общего визуального стиля сцен"\n'
        '  }\n'
        "- Все строковые значения — в ОДНУ строку (без символов переноса строки внутри).\n"
        "- Описания персонажей — максимум 150 символов.\n"
        "- Никаких спецсимволов кроме букв, цифр, пробела, точки, запятой.\n"
        "- ⚠️ ВАЖНО: ГРУППЫ ЛЮДЕЙ (семья, толпа, банда, команда) = ОДИН персонаж.\n"
        "  Пример: если в сценарии 'семья из 5 человек' — это ОДИН персонаж 'Семья_Ивановых'.\n"
        "- Максимум 2-3 персонажа (включая группы).\n"
    )

    extractor_user = (
        "Проанализируй сценарий и верни ТОЛЬКО JSON (без пояснений):\n\n"
        + full_text
    )
    
    print("🤖 [EXTRACTOR] Отправка запроса к AI...")

    try:
        visual_config = call_ai_extractor(
            client=client,
            is_yandex=is_yandex,
            folder_id=folder_id,
            model=model,
            system_prompt=extractor_system,
            user_text=extractor_user,
            max_tokens=3000
        )
        
        print(f"✅ [EXTRACTOR] AI вернул данные")
        print(f"   Тип результата: {type(visual_config).__name__}")
        if isinstance(visual_config, dict):
            print(f"   Ключи: {list(visual_config.keys())}")
            if "characters" in visual_config:
                chars = visual_config["characters"]
                if isinstance(chars, dict):
                    print(f"   Персонажей найдено: {len(chars)}")
                    for name in chars.keys():
                        print(f"      - {name}")
        
        # Сохраняем результат
        with open("data/visual_config.json", "w", encoding="utf-8") as f:
            json.dump(visual_config, f, ensure_ascii=False, indent=2)
        
        print(f"💾 [EXTRACTOR] Сохранено в data/visual_config.json")
        print("\n✅ Stage 1 успешно завершён.")
        return True

    except Exception as e:
        print(f"\n❌ [EXTRACTOR ERROR] Ошибка экстрактора: {e}")
        traceback.print_exc()
        
        # Создаём резервный файл с пустыми персонажами
        print("⚠️ [EXTRACTOR] Создаём fallback файл...")
        fallback_config = {
            "characters": {},
            "visual_style": "Unknown",
            "error": "Extractor failed"
        }
        with open("data/visual_config.json", "w", encoding="utf-8") as f:
            json.dump(fallback_config, f, ensure_ascii=False, indent=2)
        
        return False


if __name__ == "__main__":
    run_stage_1()