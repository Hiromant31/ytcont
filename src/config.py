import os
import json
from pydantic import BaseModel
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Модель данных для запуска пайплайна
class StartRequest(BaseModel):
    stage:              int   = 1
    idea:               str   = ""
    num_episodes:       int   = 3
    aspect_ratio:       str   = "9:16"
    quality:            str   = "1080p"
    codec:              str   = "libx264"
    test_mode:          bool  = False
    use_colab_whisper:  bool  = False
    use_colab_render:   bool  = False
    colab_url:          str   = ""
    auto_continue:      bool  = True
    ai_settings:        dict  = None
    prompts:            dict  = None

def get_default_settings():
    """Возвращает базовые настройки из файла или значения по умолчанию."""
    if os.path.exists("settings.json"):
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
            
    return {
        "aspect_ratio": "9:16",
        "quality": "1080p",
        "codec": "libx264",
        "test_mode": False,
        "use_colab_whisper": False,
        "use_colab_render": False,
        "colab_url": "",
        "auto_continue": True,
        "ai_settings": {
            "text": {
                "api_url": "https://ai.api.cloud.yandex.net/v1",
                "api_key": "",
                "folder_id": "",
                "model": "gemma-3-27b-it/latest"
            }
        },
        "prompts": {
            "stage_1_writer": "",
            "stage_1_extractor": "",
            "stage_2_scenes": ""
        }
    }