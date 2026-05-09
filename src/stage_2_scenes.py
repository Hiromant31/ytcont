import os
import json
import time
import re
from pathlib import Path
from dotenv import load_dotenv
import openai

load_dotenv()


# ─────────────────────────────────────────────
#  TEMPLATE MANAGER IMPORT (fallback)
# ─────────────────────────────────────────────

try:
    from .template_manager import get_active_template, get_template
except ImportError:
    def get_active_template():
        return None
    def get_template(template_id):
        return None


# ─────────────────────────────────────────────
#  JSON REPAIR UTILITIES (скопировано из stage_1_story)
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

    # Дописываем закрывающие скобки
    closing = {'{': '}', '[': ']'}
    for opener in reversed(stack):
        text += closing[opener]

    return text


def repair_truncated_json(raw_text: str):
    """
    Универсальная функция починки JSON:
    1. Удаляет Markdown-обертку
    2. Ищет полный корневой объект/массив
    3. Если не найден — чинит обрыв
    4. Парсит результат
    """
    text = _strip_markdown(raw_text)
    
    # Попытка 1: найти уже полный JSON
    pos = _find_last_complete_root(text)
    if pos >= 0:
        text = text[:pos+1]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    
    # Попытка 2: чинить обрыв
    text_fixed = _close_open_structure(text)
    try:
        return json.loads(text_fixed)
    except json.JSONDecodeError as e:
        raise ValueError(f"Не удалось распарсить JSON даже после починки:\n{text_fixed[:500]}\nОшибка: {e}")


# ─────────────────────────────────────────────
#  MAIN STAGE 2 FUNCTIONS
# ─────────────────────────────────────────────

def run_stage_2(ai_settings=None, prompts=None, num_episodes=None):
    print(f"🎬 Stage 2: Режиссер начинает планирование кадров...")

    # 1. Настройки AI (универсально как в Stage 1)
    settings = load_settings()
    ai_text = ai_settings["text"] if ai_settings and "text" in ai_settings else settings.get("ai_settings", {}).get("text", {})

    api_url   = ai_text.get("api_url", "https://ai.api.cloud.yandex.net/v1")
    api_key   = ai_text.get("api_key", "")
    folder_id = ai_text.get("folder_id", "")
    model     = ai_text.get("model", "gemma-3-27b-it/latest")
    is_yandex = "yandex" in api_url.lower() or "ai.api.cloud.yandex" in api_url

    if not api_key:
        print("❌ Ошибка: Не задан api_key")
        return False

    # Клиент
    client = openai.OpenAI(api_key=api_key, base_url=api_url, project=folder_id if is_yandex else None)

    # 2. Загрузка данных и промптов
    try:
        with open("data/1_base_structure.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        # Поддержка обоих форматов: старый (episodes) и новый (episodes_final)
        episodes = data.get("episodes_final", data.get("episodes", {}))
        
        # Загружаем visual_config
        with open("data/visual_config.json", "r", encoding="utf-8") as f:
            visual_config = json.load(f)
        
        # Нормализация visual_config
        visual_config = normalize_visual_config(visual_config)
        char_data = visual_config.get("characters", {})
        visual_style = visual_config.get("visual_style", "Not specified")
        
        # Берем промпт из UI или из файла
        system_instruction = prompts.get("stage_2_scenes", "") if prompts else ""

        # Если промпт не найден, пробуем из шаблона (V2 структура)
        if not system_instruction:
            try:
                active_template = get_active_template()
                if active_template and not active_template.get("from_legacy"):
                    template_id = active_template.get("id")
                    if template_id:
                        from .template_manager import get_template_prompts
                        prompts_from_db = get_template_prompts(template_id)
                        if prompts_from_db:
                            prompts_dict = {p["prompt_name"]: p["prompt_text"] for p in prompts_from_db}
                            system_instruction = prompts_dict.get("stage_2_scenes", "")
                            if system_instruction:
                                print(f"   🎭 Используем промпт из шаблона (V2): {template_id}")
                            else:
                                print(f"   ⚠️  stage_2_scenes не найден в шаблоне")
                        else:
                            # Fallback к старой структуре
                            template_prompts = json.loads(active_template.get("prompts_json", "{}"))
                            system_instruction = template_prompts.get("stage_2_scenes", "")
                            if system_instruction:
                                print(f"   🎭 Используем промпт из шаблона: {active_template.get('id', 'unknown')}")
                    else:
                        # Fallback к старой структуре
                        template_prompts = json.loads(active_template.get("prompts_json", "{}"))
                        system_instruction = template_prompts.get("stage_2_scenes", "")
            except Exception as e:
                print(f"   ⚠️  Ошибка загрузки промпта из шаблона: {e}")

        # Fallback к файлу
        if not system_instruction:
            system_instruction = Path("prompts/stage_2_scenes.txt").read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ Ошибка загрузки данных: {e}")
        return False

    char_names = list(char_data.keys())
    production_map = {"episodes": {}}

    # 3. Цикл по эпизодам
    for ep_key, ep_text in episodes.items():
        print(f"🎥 Планируем кадры для {ep_key} (целевое время: 60 сек)...")
        
        # Формируем список персонажей для промпта
        main_char = char_names[0] if len(char_names) > 0 else "N/A"
        supporting = char_names[1:] if len(char_names) > 1 else []
        
        # Расширенный промпт с акцентом на таймлимит
        prompt_input = f"""TEXT: {ep_text}

CHARACTERS:
[MAIN_1] = {main_char}
{f"[MAIN_2] = {supporting[0]}" if len(supporting) > 0 else ""}
{f"[MAIN_3] = {supporting[1]}" if len(supporting) > 1 else ""}

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
"""
        
        try:
            if is_yandex:
                response = client.responses.create(
                    model=f"gpt://{folder_id}/{model}",
                    temperature=0.2,
                    instructions=system_instruction,
                    input=prompt_input,
                    max_output_tokens=4000
                )
                raw_res = response.output_text
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt_input}
                    ],
                    temperature=0.2
                )
                raw_res = response.choices[0].message.content

            # Используем встроенный парсер
            scenes_data = repair_truncated_json(raw_res)
            
            # Валидация
            if not isinstance(scenes_data, dict) or "scenes" not in scenes_data:
                print(f"⚠️ Некорректная структура ответа для {ep_key}, создаю fallback")
                scenes_data = {"scenes": []}
            
            production_map["episodes"][ep_key] = scenes_data.get("scenes", [])
            
            # Статистика
            scene_count = len(production_map["episodes"][ep_key])
            print(f"   ✓ Создано сцен: {scene_count} (~{scene_count * 5} сек при 5 сек/сцену)")
            
            time.sleep(1)

        except Exception as e:
            print(f"❌ Ошибка на {ep_key}: {e}")
            return False

    # Добавляем метаданные
    production_map["characters_metadata"] = char_data
    production_map["visual_style"] = visual_style
    
    os.makedirs("data", exist_ok=True)
    with open("data/2_production_map.json", "w", encoding="utf-8") as f:
        json.dump(production_map, f, ensure_ascii=False, indent=2)

    print(f"✅ Stage 2 завершен → data/2_production_map.json")
    return True


def normalize_visual_config(config):
    """
    Нормализация visual_config в единый формат dict.
    Обрабатывает случаи: list, dict, некорректные структуры.
    """
    # Случай 1: config - это список (старый формат или ошибка)
    if isinstance(config, list):
        print("⚠️ visual_config - список, преобразуем...")
        
        # Пытаемся найти персонажей в элементах списка
        result = {"characters": {}, "visual_style": "Not specified"}
        
        for item in config:
            if isinstance(item, dict):
                if "characters" in item:
                    result["characters"].update(item["characters"])
                if "visual_style" in item:
                    result["visual_style"] = item["visual_style"]
        
        # Если ничего не найдено - берем первый элемент как dict
        if not result["characters"] and len(config) > 0:
            first = config[0]
            if isinstance(first, dict):
                result = first
        
        return result
    
    # Случай 2: config - уже dict
    if isinstance(config, dict):
        # Проверяем наличие ключа characters
        if "characters" not in config:
            print("⚠️ В visual_config нет секции 'characters'")
            config["characters"] = {}
        
        # Нормализация characters
        chars = config["characters"]
        if isinstance(chars, list):
            normalized = {}
            for i, item in enumerate(chars):
                if isinstance(item, dict) and "name" in item:
                    normalized[item["name"]] = item.get("description", str(item))
                else:
                    normalized[f"Character_{i+1}"] = str(item)
            config["characters"] = normalized
        
        # Добавляем visual_style если отсутствует
        if "visual_style" not in config:
            config["visual_style"] = "Not specified"
        
        return config
    
    # Случай 3: неизвестный тип
    print(f"⚠️ Неизвестный тип visual_config: {type(config).__name__}")
    return {"characters": {}, "visual_style": "Not specified"}


def load_settings():
    """Загружает настройки из settings.json"""
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
        }
    }


if __name__ == "__main__":
    run_stage_2()
