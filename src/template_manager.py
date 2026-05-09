"""
Template Manager Module

Управление шаблонами промптов через SQLite БД.
Поддержка версионирования, дублирования, архивации.
"""

import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any


# Path to database
DB_PATH = Path("data/ytcont.db")


def get_db_connection():
    """Получить соединение с SQLite БД."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализировать базу данных и создать таблицы."""
    os.makedirs("data", exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Таблица templates
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS templates (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        category TEXT,
        
        prompts_json TEXT NOT NULL,
        settings_json TEXT,
        
        created_at TEXT,
        updated_at TEXT,
        
        is_default INTEGER DEFAULT 0,
        archived INTEGER DEFAULT 0
    )
    """)
    
    # Таблица template_versions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS template_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        
        prompts_json TEXT NOT NULL,
        settings_json TEXT,
        
        created_at TEXT NOT NULL,
        
        FOREIGN KEY (template_id) REFERENCES templates(id)
    )
    """)
    
    conn.commit()
    conn.close()


def check_db_exists() -> bool:
    """Проверить существование БД."""
    return DB_PATH.exists()


def create_template(
    template_id: str,
    name: str,
    description: str = "",
    category: str = "",
    prompts_json: str = "{}",
    settings_json: str = "{}",
    is_default: bool = False
) -> bool:
    """
    Создать новый шаблон.
    
    Args:
        template_id: Уникальный идентификатор (например, "manga-drama")
        name: Название для UI
        description: Описание шаблона
        category: Категория (Развлекательное, Криминал и т.д.)
        prompts_json: JSON со строками промптов
        settings_json: JSON с настройками (visual_style и т.д.)
        is_default: Флаг дефолтного шаблона
        
    Returns:
        True при успехе, False при ошибке
    """
    if not check_db_exists():
        init_db()
    
    now = datetime.now().isoformat()
    
    # Если это дефолтный шаблон, сбросить флаг у остальных
    if is_default:
        reset_default_template()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        INSERT INTO templates 
        (id, name, description, category, prompts_json, settings_json, created_at, updated_at, is_default, archived)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            template_id,
            name,
            description,
            category,
            prompts_json,
            settings_json,
            now,
            now,
            1 if is_default else 0
        ))
        
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """
    Получить шаблон по ID.
    
    Args:
        template_id: ID шаблона
        
    Returns:
        Dict с данными шаблона или None
    """
    if not check_db_exists():
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM templates WHERE id = ? AND archived = 0", (template_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_all_templates(
    archived: bool = False,
    category: str = None,
    search: str = None
) -> List[Dict[str, Any]]:
    """
    Получить список всех шаблонов.
    
    Args:
        archived: Включить архивные шаблоны
        category: Фильтр по категории
        search: Поиск по названию/описанию
        
    Returns:
        Список шаблонов
    """
    if not check_db_exists():
        return []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM templates WHERE archived = ?"
    params = [0 if not archived else 1]
    
    if category:
        query += " AND category = ?"
        params.append(category)
    
    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    
    query += " ORDER BY updated_at DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def update_template(
    template_id: str,
    name: str = None,
    description: str = None,
    category: str = None,
    prompts_json: str = None,
    settings_json: str = None,
    archived: bool = None
) -> bool:
    """
    Обновить шаблон (PATCH-style).
    
    Args:
        template_id: ID шаблона
        name: Новое название (опционально)
        description: Новое описание (опционально)
        category: Новая категория (опционально)
        prompts_json: Новые промпты (опционально)
        settings_json: Новые настройки (опционально)
        archived: Состояние архива (опционально)
        
    Returns:
        True при успехе
    """
    if not check_db_exists():
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Получаем текущие данные
    cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return False
    
    current = dict(row)
    
    # Формируем UPDATE
    updates = []
    params = []
    
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    else:
        params.append(current["name"])
    
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    else:
        params.append(current["description"])
    
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    else:
        params.append(current["category"])
    
    if prompts_json is not None:
        updates.append("prompts_json = ?")
        params.append(prompts_json)
    else:
        params.append(current["prompts_json"])
    
    if settings_json is not None:
        updates.append("settings_json = ?")
        params.append(settings_json)
    else:
        params.append(current["settings_json"])
    
    if archived is not None:
        updates.append("archived = ?")
        params.append(1 if archived else 0)
    else:
        params.append(current["archived"])
    
    now = datetime.now().isoformat()
    updates.append("updated_at = ?")
    params.append(now)
    
    params.append(template_id)
    
    query = f"UPDATE templates SET {', '.join(updates)} WHERE id = ?"
    
    try:
        cursor.execute(query, params)
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def delete_template(template_id: str) -> bool:
    """
    Удалить шаблон.
    
    Args:
        template_id: ID шаблона
        
    Returns:
        True при успехе
    """
    if not check_db_exists():
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        conn.close()


def duplicate_template(template_id: str, new_id: str = None, new_name: str = None) -> Optional[str]:
    """
    Дублировать шаблон.
    
    Args:
        template_id: Исходный ID
        new_id: Новый ID (если None, генерируется автоматически)
        new_name: Новое название (если None, добавляется "Copy")
        
    Returns:
        Новый ID или None при ошибке
    """
    template = get_template(template_id)
    if not template:
        return None
    
    if new_id is None:
        new_id = f"{template_id}_copy_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    if new_name is None:
        new_name = f"{template['name']} (Copy)"
    
    # Создаём новый шаблон
    if create_template(
        template_id=new_id,
        name=new_name,
        description=template["description"],
        category=template["category"],
        prompts_json=template["prompts_json"],
        settings_json=template["settings_json"],
        is_default=False
    ):
        return new_id
    return None


def archive_template(template_id: str, archived: bool = True) -> bool:
    """
    Архивировать/разархивировать шаблон.
    
    Args:
        template_id: ID шаблона
        archived: True для архивации, False для восстановления
        
    Returns:
        True при успехе
    """
    return update_template(template_id, archived=archived)


def get_default_template() -> Optional[Dict[str, Any]]:
    """
    Получить дефолтный шаблон.
    
    Returns:
        Dict с данными или None
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM templates WHERE is_default = 1 AND archived = 0 LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def reset_default_template():
    """Сбросить флаг is_default у всех шаблонов."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("UPDATE templates SET is_default = 0")
        conn.commit()
    finally:
        conn.close()


def create_template_version(template_id: str) -> Optional[int]:
    """
    Создать новую версию шаблона.
    
    Args:
        template_id: ID шаблона
        
    Returns:
        ID новой версии или None
    """
    template = get_template(template_id)
    if not template:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Получаем максимальную версию
    cursor.execute("SELECT MAX(version) FROM template_versions WHERE template_id = ?", (template_id,))
    row = cursor.fetchone()
    max_version = row[0] or 0
    new_version = max_version + 1
    
    now = datetime.now().isoformat()
    
    try:
        cursor.execute("""
        INSERT INTO template_versions (template_id, version, prompts_json, settings_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (
            template_id,
            new_version,
            template["prompts_json"],
            template["settings_json"],
            now
        ))
        
        conn.commit()
        return new_version
    except Exception:
        return None
    finally:
        conn.close()


def get_template_versions(template_id: str) -> List[Dict[str, Any]]:
    """
    Получить историю версий шаблона.
    
    Args:
        template_id: ID шаблона
        
    Returns:
        Список версий
    """
    if not check_db_exists():
        return []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM template_versions WHERE template_id = ? ORDER BY version DESC",
        (template_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def restore_template_version(template_id: str, version: int) -> bool:
    """
    Восстановить шаблон из версии.
    
    Args:
        template_id: ID шаблона
        version: Номер версии
        
    Returns:
        True при успехе
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM template_versions WHERE template_id = ? AND version = ?",
        (template_id, version)
    )
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return False
    
    version_data = dict(row)
    
    try:
        cursor.execute("""
        UPDATE templates 
        SET prompts_json = ?, settings_json = ?, updated_at = ?
        WHERE id = ?
        """, (
            version_data["prompts_json"],
            version_data["settings_json"],
            datetime.now().isoformat(),
            template_id
        ))
        
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# --- Fallback to legacy system ---

def load_legacy_prompts_from_files() -> Optional[Dict[str, Any]]:
    """
    Загрузить промпты из старых txt файлов (fallback).
    
    Returns:
        Dict с промптами или None
    """
    try:
        from pathlib import Path
        
        prompts_path = Path("prompts")
        
        if not prompts_path.exists():
            return None
        
        # Сначала пробуем legacy папку
        legacy_path = prompts_path / "legacy"
        if legacy_path.exists():
            writer_path = legacy_path / "writer_instruction.txt"
            extractor_path = legacy_path / "extractor_instruction.txt"
            stage2_path = legacy_path / "stage_2_scenes.txt"
        else:
            writer_path = prompts_path / "writer_instruction.txt"
            extractor_path = prompts_path / "extractor_instruction.txt"
            stage2_path = prompts_path / "stage_2_scenes.txt"
        
        prompts = {}
        
        if writer_path.exists():
            prompts["stage_1_writer"] = writer_path.read_text(encoding="utf-8")
        if extractor_path.exists():
            prompts["stage_1_extractor"] = extractor_path.read_text(encoding="utf-8")
        if stage2_path.exists():
            prompts["stage_2_scenes"] = stage2_path.read_text(encoding="utf-8")
        
        if prompts:
            return prompts
        return None
        
    except Exception:
        return None


def load_legacy_settings() -> Optional[Dict[str, Any]]:
    """
    Загрузить settings из старого JSON.
    
    Returns:
        Dict с settings или None
    """
    try:
        if not os.path.exists("settings.json"):
            return None
        
        with open("settings.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return data
    except Exception:
        return None


# --- Main API ---

def get_active_template() -> Optional[Dict[str, Any]]:
    """
    Получить активный шаблон (из settings.json или дефолтный).
    
    Returns:
        Dict с данными шаблона или None
    """
    # 1. Проверяем settings.json
    try:
        if os.path.exists("settings.json"):
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
            
            # Новый формат с active_template_id
            if "active_template_id" in settings:
                template_id = settings["active_template_id"]
                template = get_template(template_id)
                if template:
                    return template
    except Exception:
        pass
    
    # 2. Проверяем старый формат prompts в settings
    try:
        if os.path.exists("settings.json"):
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
            
            prompts = settings.get("prompts", {})
            if prompts.get("stage_1_writer") or prompts.get("stage_1_extractor"):
                # ВозвращаемNone - это старый формат, будет обработан отдельно
                return {"prompts_json": json.dumps(prompts), "from_legacy": True}
    except Exception:
        pass
    
    # 3. Проверяем дефолтный шаблон
    template = get_default_template()
    if template:
        return template
    
    # 4. Fallback к файлам
    legacy = load_legacy_prompts_from_files()
    if legacy:
        return {"prompts_json": json.dumps(legacy), "from_legacy": True}
    
    return None


def export_template(template_id: str) -> Optional[Dict[str, Any]]:
    """
    Экспортировать шаблон в Dict (для JSON/CSV экспорта).
    
    Args:
        template_id: ID шаблона
        
    Returns:
        Dict с данными шаблона
    """
    template = get_template(template_id)
    if not template:
        return None
    
    return {
        "id": template["id"],
        "name": template["name"],
        "description": template["description"],
        "category": template["category"],
        "prompts_json": template["prompts_json"],
        "settings_json": template["settings_json"],
        "created_at": template["created_at"],
        "updated_at": template["updated_at"],
        "is_default": bool(template["is_default"]),
        "archived": bool(template["archived"])
    }


def import_template(data: Dict[str, Any], overwrite: bool = False) -> Optional[str]:
    """
    Импортировать шаблон из Dict.

    Args:
        data: Dict с данными шаблона
        overwrite: Перезаписать если exists

    Returns:
        ID шаблона или None
    """
    template_id = data.get("id")
    if not template_id:
        return None

    if not overwrite and get_template(template_id):
        return None

    create_template(
        template_id=template_id,
        name=data.get("name", template_id),
        description=data.get("description", ""),
        category=data.get("category", ""),
        prompts_json=data.get("prompts_json", "{}"),
        settings_json=data.get("settings_json", "{}"),
        is_default=data.get("is_default", False)
    )

    return template_id


# ─────────────────────────────────────────────
#  NEW V2 FUNCTIONS: Prompts & Settings per template
# ─────────────────────────────────────────────

def add_template_prompt(template_id: str, prompt_name: str, prompt_text: str, 
                        language: str = "ru", description: str = "") -> bool:
    """
    Добавить промпт к шаблону (новая структура V2).

    Args:
        template_id: ID шаблона
        prompt_name: Имя промпта (например, "stage_1_writer", "stage_2_scenes")
        prompt_text: Текст промпта
        language: Язык ("ru", "en")
        description: Описание промпта

    Returns:
        True при успехе
    """
    if not check_db_exists():
        return False

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        INSERT INTO template_prompts (template_id, prompt_name, prompt_text, language, description)
        VALUES (?, ?, ?, ?, ?)
        """, (template_id, prompt_name, prompt_text, language, description))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_template_prompt(template_id: str, prompt_name: str, 
                           prompt_text: str = None, language: str = None,
                           description: str = None) -> bool:
    """
    Обновить промпт шаблона.

    Args:
        template_id: ID шаблона
        prompt_name: Имя промпта
        prompt_text: Новый текст (опционально)
        language: Новый язык (опционально)
        description: Новое описание (опционально)

    Returns:
        True при успехе
    """
    if not check_db_exists():
        return False

    conn = get_db_connection()
    cursor = conn.cursor()

    # Получаем текущий промпт
    cursor.execute("""
        SELECT * FROM template_prompts 
        WHERE template_id = ? AND prompt_name = ?
    """, (template_id, prompt_name))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return False

    current = dict(row)

    updates = []
    params = []

    if prompt_text is not None:
        updates.append("prompt_text = ?")
        params.append(prompt_text)
    else:
        params.append(current["prompt_text"])

    if language is not None:
        updates.append("language = ?")
        params.append(language)
    else:
        params.append(current["language"])

    if description is not None:
        updates.append("description = ?")
        params.append(description)
    else:
        params.append(current["description"])

    params.append(template_id)
    params.append(prompt_name)

    query = f"UPDATE template_prompts SET {', '.join(updates)} WHERE template_id = ? AND prompt_name = ?"

    try:
        cursor.execute(query, params)
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def delete_template_prompt(template_id: str, prompt_name: str) -> bool:
    """
    Удалить промпт из шаблона.

    Args:
        template_id: ID шаблона
        prompt_name: Имя промпта

    Returns:
        True при успехе
    """
    if not check_db_exists():
        return False

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM template_prompts 
            WHERE template_id = ? AND prompt_name = ?
        """, (template_id, prompt_name))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        conn.close()


def get_template_prompts(template_id: str) -> List[Dict[str, Any]]:
    """
    Получить все промпты шаблона.

    Args:
        template_id: ID шаблона

    Returns:
        Список промптов
    """
    if not check_db_exists():
        return []

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM template_prompts 
        WHERE template_id = ?
        ORDER BY sort_order, prompt_name
    """, (template_id,))
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_template_prompt(template_id: str, prompt_name: str) -> Optional[Dict[str, Any]]:
    """
    Получить конкретный промпт шаблона.

    Args:
        template_id: ID шаблона
        prompt_name: Имя промпта

    Returns:
        Dict с промптом или None
    """
    if not check_db_exists():
        return None

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM template_prompts 
        WHERE template_id = ? AND prompt_name = ?
    """, (template_id, prompt_name))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def add_template_setting(template_id: str, setting_key: str, setting_value: str) -> bool:
    """
    Добавить настройку к шаблону.

    Args:
        template_id: ID шаблона
        setting_key: Ключ настройки
        setting_value: Значение настройки

    Returns:
        True при успехе
    """
    if not check_db_exists():
        return False

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        INSERT INTO template_settings (template_id, setting_key, setting_value)
        VALUES (?, ?, ?)
        """, (template_id, setting_key, setting_value))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_template_setting(template_id: str, setting_key: str, 
                            setting_value: str) -> bool:
    """
    Обновить настройку шаблона.

    Args:
        template_id: ID шаблона
        setting_key: Ключ настройки
        setting_value: Новое значение

    Returns:
        True при успехе
    """
    if not check_db_exists():
        return False

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE template_settings 
            SET setting_value = ?
            WHERE template_id = ? AND setting_key = ?
        """, (setting_value, template_id, setting_key))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        conn.close()


def delete_template_setting(template_id: str, setting_key: str) -> bool:
    """
    Удалить настройку из шаблона.

    Args:
        template_id: ID шаблона
        setting_key: Ключ настройки

    Returns:
        True при успехе
    """
    if not check_db_exists():
        return False

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM template_settings 
            WHERE template_id = ? AND setting_key = ?
        """, (template_id, setting_key))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        conn.close()


def get_template_settings(template_id: str) -> Dict[str, str]:
    """
    Получить все настройки шаблона.

    Args:
        template_id: ID шаблона

    Returns:
        Dict с настройками
    """
    if not check_db_exists():
        return {}

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT setting_key, setting_value FROM template_settings 
        WHERE template_id = ?
    """, (template_id,))
    rows = cursor.fetchall()
    conn.close()

    return {row["setting_key"]: row["setting_value"] for row in rows}


def get_all_prompts_for_stage(template_id: str, stage: str) -> Dict[str, str]:
    """
    Получить все промпты для определённого этапа (stage_1, stage_2).

    Args:
        template_id: ID шаблона
        stage: Номер этапа ("1" или "2")

    Returns:
        Dict с промптами
    """
    prompts = get_template_prompts(template_id)
    
    prefix = f"stage_{stage}_"
    stage_prompts = {}
    
    for p in prompts:
        if p["prompt_name"].startswith(prefix):
            stage_prompts[p["prompt_name"]] = p["prompt_text"]
    
    return stage_prompts
