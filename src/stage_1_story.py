import os
import json
import time
import re
import traceback
from pathlib import Path
from dotenv import load_dotenv
import openai

load_dotenv()


# ─────────────────────────────────────────────
#  STORY PIPELINE PROMPTS
# ─────────────────────────────────────────────

STORY_PROMPT = """
Ты — сценарист сериалов короткого формата.

На основе идеи создай цельную историю из 3 эпизодов.

Требования:
- 2–3 главных героя
- один центральный конфликт
- чёткая арка: завязка → эскалация → развязка
- обязательно:
  - скрытая правда
  - поворот в середине
  - сильный финальный удар

Формат:

TITLE:

CHARACTERS:
- имя + роль

CORE CONFLICT:

EPISODE PLAN:

EP1:
EP2:
EP3:

IMPORTANT:
- только структура, без художественного текста
"""

EPISODE_PROMPT = """
Ты — Story Engine для коротких видео (60 секунд).

Вот структура истории:
{MASTER_STORY}

Напиши эпизод: {EPISODE_NUMBER}

Длина: 100–120 слов

СТРУКТУРА:
HOOK:
START:
BUILD:
IMPACT:
END:

ТРЕБОВАНИЯ:
- связный рассказ (не обрывки)
- предложения 5–10 слов
- без диалогов
- быстрый темп
- минимум 1 поворот

ЗАПРЕТ:
- не задавать вопросы
- не просить данные
"""

POLISH_PROMPT = """
Ты — редактор voice-over сценариев.

Перепиши текст так, чтобы он идеально звучал вслух.

Требования:
- сохранить смысл 100%
- убрать обрывки
- сделать плавный рассказ

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
    Для массива — извлекает только полностью закрытые объекты верхнего уровня.
    """
    items = []
    depth = 0
    start = None
    for i, ch, in_str in _walk(text):
        if in_str:
            continue
        if depth == 0 and ch == '{':
            depth = 1
            start = i
        elif depth == 1 and ch == '{':
            depth += 1
        elif depth == 1 and ch == '}':
            depth = 0
            if start is not None:
                items.append(text[start:i + 1])
                start = None
        elif depth > 1:
            if ch in '{[':
                depth += 1
            elif ch in '}]':
                depth -= 1
    return items


def repair_truncated_json(raw: str):
    """
    Пытается восстановить обрезанный/кривой JSON от AI.
    Возвращает распарсенный Python-объект или бросает ValueError.

    Стратегии (в порядке приоритета):
      1. Прямой парсинг (если JSON уже валиден).
      2. Усечь до последнего полностью закрытого корневого элемента.
      3. Закрыть незакрытые структуры (откат до последней запятой + закрытие скобок).
      4. Для массивов — собрать только полные элементы.
    """
    raw = _strip_markdown(raw)

    # 1. Прямой парсинг
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. Усечь до последнего полностью закрытого корневого элемента
    last_pos = _find_last_complete_root(raw)
    if last_pos > 0:
        candidate = raw[:last_pos + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 3. Закрыть незакрытые структуры
    candidate = _close_open_structure(raw)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # 4. Для массивов — собрать только полные элементы
    if raw.lstrip().startswith('['):
        items = _extract_complete_array_items(raw)
        if items:
            candidate = '[' + ','.join(items) + ']'
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

    raise ValueError(
        f"Не удалось восстановить JSON.\n"
        f"Начало: {raw[:300]}\n"
        f"Конец:  ...{raw[-150:]}"
    )


# ─────────────────────────────────────────────
#  AI EXTRACTOR WITH RETRY
# ─────────────────────────────────────────────

def call_ai_extractor(client, is_yandex, folder_id, model,
                      system_prompt, user_text, max_tokens=3000):
    """
    Вызывает AI для получения JSON.
    2 попытки: при неудаче просит сократить вывод.
    """
    MAX_RETRIES  = 2
    current_user = user_text

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"   ∟ Попытка {attempt}/{MAX_RETRIES}...")
        try:
            if is_yandex:
                response = client.responses.create(
                    model=f"gpt://{folder_id}/{model}",
                    temperature=0.1,
                    instructions=system_prompt,
                    input=current_user,
                    max_output_tokens=max_tokens
                )
                raw_res = response.output_text.strip()
            else:
                # DeepSeek reasoning поддержка
                is_deepseek = "deepseek" in model.lower()
                actual_max_tokens = max_tokens * 3 if is_deepseek else max_tokens
                
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": current_user}
                    ],
                    temperature=0.1,
                    max_tokens=actual_max_tokens
                )
                
                if not response.choices:
                    raise Exception(f"Нет choices в ответе: {response}")
                
                choice = response.choices[0]
                msg = choice.message
                
                # 1. Проверка на обрыв по лимиту токенов
                if choice.finish_reason == 'length':
                    raise Exception(f"Не хватило max_tokens ({max_tokens}). Ответ или этап размышлений (reasoning) оборвался.")
                
                # 2. Проверка на пустой content из-за ухода в reasoning
                if msg is None or msg.content is None:
                    reasoning = getattr(msg, 'reasoning', 'Нет данных reasoning')
                    raise Exception(f"Нет content в ответе. Возможно, модель ушла в reasoning и не успела дать ответ: {reasoning}")
                
                raw_res = str(msg.content).strip()
                if not raw_res:
                    raise Exception("Пустой content в ответе")

            print(f"   ∟ Получено {len(raw_res)} символов, парсим...")
            parsed = repair_truncated_json(raw_res)
            print("   ✓ JSON успешно распарсен")
            return parsed

        except ValueError as e:
            print(f"   ⚠️ Ошибка JSON (попытка {attempt}):\n{e}")
            if attempt < MAX_RETRIES:
                current_user = (
                    "КРИТИЧНО: предыдущий ответ был обрезан или невалиден.\n"
                    "Обязательные правила:\n"
                    "1. ТОЛЬКО JSON — никакого текста вокруг, никаких ``` блоков.\n"
                    "2. Все строки — в ОДНУ строку, без \\n внутри значений.\n"
                    "3. Описания — не более 8 слов на поле.\n"
                    "4. Никаких спецсимволов кроме букв, цифр, пробела, точки.\n\n"
                    + user_text
                )
                time.sleep(2)
            else:
                raise Exception(
                    f"Не удалось получить валидный JSON после {MAX_RETRIES} попыток.\n"
                    f"Последняя ошибка: {e}"
                )
        except Exception as e:
            # API ошибки и ошибки лимита токенов прерывают выполнение,
            # так как ретрай с тем же max_tokens все равно приведет к 'length'
            raise Exception(f"Ошибка вызова API или лимитов: {e}")


def call_ai_text(client, is_yandex, folder_id, model, system_prompt, user_input, max_tokens=2000):
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

def run_stage_1(ai_settings=None, prompts=None):
    """Stage 1: Генерация сценария + извлечение визуального конфига."""
    print("🚀 Запуск Stage 1: Генерация истории...")

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

    # ── Промпты ──
    if prompts and "stage_1_writer" in prompts:
        prompts_dict = {
            "writer":    prompts.get("stage_1_writer", ""),
            "extractor": prompts.get("stage_1_extractor", "")
        }
        print("   Используем промпты из настроек")
    else:
        prompts_dict = load_prompts_from_json()
        if not prompts_dict["writer"] or not prompts_dict["extractor"]:
            print("⚠️ Промпты не найдены в settings.json, загружаю из файлов...")
            file_prompts = load_prompts_from_files()
            if not file_prompts["writer"]:
                print("❌ Ошибка: Не найден промпт writer_instruction.txt")
                return False
            prompts_dict = file_prompts

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
    #  NEW STORY PIPELINE
    # ─────────────────────────────────────────────
    episodes_raw = {}   # Новое: для хранения сырых текстов
    episodes_final = {} # Для финальных

    print("🧠 Генерируем master story...")

    master_story = call_ai_text(
        client,
        is_yandex,
        folder_id,
        model,
        STORY_PROMPT,
        prompts_dict.get("idea", ""),
        max_tokens=4000
    )

    print("   ✓ Master story готов")

    episodes = {}

    print("✍️ Генерируем эпизоды...")

    for i in range(1, 4):
        print(f"   ∟ episode_{i}...")

        # Генерация эпизода
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
        episodes_raw[f"episode_{i}"] = episode_raw # Сохраняем сырой

        # Полиш под озвучку
        episode_final = call_ai_text(
            client,
            is_yandex,
            folder_id,
            model,
            POLISH_PROMPT,
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
        '    "visual_style": "Описание общего визуального стиля"\n'
        '  }\n'
        "- Все строковые значения — в ОДНУ строку (без символов переноса строки внутри).\n"
        "- Описания персонажей — максимум 8 слов на поле.\n"
        "- Никаких спецсимволов кроме букв, цифр, пробела, точки, запятой.\n"
        "- ГРУППЫ ЛЮДЕЙ (семья, толпа, команда) считаются за ОДНО действующее лицо.\n"
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
