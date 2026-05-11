import os
import json
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .orchestrator import manager
from .template_manager import (
    get_all_templates, get_template, create_template, update_template,
    delete_template, duplicate_template, archive_template,
    get_default_template, create_template_version, get_template_versions,
    restore_template_version, export_template, import_template
)
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# Стало (динамическое определение пути):
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

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


@app.get("/settings")
async def get_settings():
    if os.path.exists("settings.json"):
        with open("settings.json", "r", encoding="utf-8") as f:
            return json.load(f)
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


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    stages_data = [
        {"icon": "✍️", "name": name}
        for name, _ in manager.stages
    ]
    return templates.TemplateResponse("index.html", {
        "request": request,
        "stages": stages_data
    })


@app.get("/api/templates")
async def api_get_templates():
    try:
        templates = get_all_templates()
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates")
async def api_create_template(data: dict):
    try:
        template_id = create_template(
            name=data.get("name", "Новый шаблон"),
            settings_json=data.get("settings_json", "{}"),
            prompts_json=data.get("prompts_json", "{}")
        )
        if not template_id:
            raise HTTPException(status_code=500, detail="Failed to create template")
        return {"success": True, "template_id": template_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/templates/{template_id}")
async def api_get_template(template_id: str):
    try:
        template = get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return template
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/templates/{template_id}")
async def api_update_template(template_id: str, data: dict):
    try:
        template = get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        success = update_template(
            template_id=template_id,
            name=data.get("name"),
            settings_json=data.get("settings_json"),
            prompts_json=data.get("prompts_json")
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update template")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/templates/{template_id}")
async def api_delete_template(template_id: str):
    try:
        template = get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        success = delete_template(template_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete template")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates/{template_id}/duplicate")
async def api_duplicate_template(template_id: str):
    try:
        template = get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        new_id = duplicate_template(template_id)
        if not new_id:
            raise HTTPException(status_code=500, detail="Failed to duplicate template")
        return {"success": True, "template_id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates/{template_id}/archive")
async def api_archive_template(template_id: str):
    try:
        template = get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        success = archive_template(template_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to archive template")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates/{template_id}/export")
async def api_export_template(template_id: str):
    try:
        template = get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        export_data = export_template(template_id)
        if not export_data:
            raise HTTPException(status_code=500, detail="Failed to export template")
        return export_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates/import")
async def api_import_template(data: dict):
    try:
        template_id = import_template(data)
        if not template_id:
            raise HTTPException(status_code=500, detail="Failed to import template")
        return {"success": True, "template_id": template_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates/{template_id}/apply")
async def api_apply_template(template_id: str):
    try:
        template = get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Читаем текущий settings.json
        if os.path.exists("settings.json"):
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
        else:
            settings = {}

        # Применяем промпты из шаблона
        if template.get("prompts_json"):
            try:
                prompts_data = json.loads(template["prompts_json"])
                settings["prompts"] = prompts_data
            except Exception:
                pass

        # Если есть visual_style в settings_json, применяем его
        if template.get("settings_json"):
            try:
                settings_data = json.loads(template["settings_json"])
                if "visual_style" in settings_data:
                    settings["visual_style"] = settings_data["visual_style"]
            except Exception:
                pass

        # Сохраняем
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)

        return {"success": True, "template_id": template_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates/{template_id}/version")
async def api_create_version(template_id: str):
    try:
        template = get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        version_id = create_template_version(template_id)
        if not version_id:
            raise HTTPException(status_code=500, detail="Failed to create version")
        return {"success": True, "version": version_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/templates/{template_id}/versions")
async def api_get_versions(template_id: str):
    try:
        template = get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        versions = get_template_versions(template_id)
        return {"versions": versions}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates/{template_id}/restore/{version}")
async def api_restore_version(template_id: str, version: int):
    try:
        template = get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        success = restore_template_version(template_id, version)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to restore version")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/db/status")
async def api_db_status():
    try:
        from .template_manager import check_db_exists
        return {"exists": check_db_exists(), "path": "data/ytcont.db"}
    except Exception as e:
        return {"exists": False, "path": "data/ytcont.db", "error": str(e)}


@app.post("/start")
async def start_task(req: StartRequest, background_tasks: BackgroundTasks):
    with open("settings.json", "w", encoding="utf-8") as f:
        json.dump(req.model_dump(), f, indent=4, ensure_ascii=False)
    background_tasks.add_task(
        manager.run_pipeline,
        start_from=req.stage,
        custom_idea=req.idea,
        num_episodes=req.num_episodes,
        ai_settings=req.ai_settings,
        prompts=req.prompts,
        auto_continue=req.auto_continue
    )
    return {"status": "started"}


@app.post("/save-ai-settings")
async def save_ai_settings(data: dict):
    try:
        if os.path.exists("settings.json"):
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
        else:
            settings = {}
        if "ai_settings" not in settings:
            settings["ai_settings"] = {}
        if "text" in data:
            settings["ai_settings"]["text"] = data["text"]
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        return {"message": "Настройки AI сохранены в settings.json"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/episodes")
async def get_episodes():
    try:
        response_data = {
            "master_story": None,
            "episodes_raw": None,
            "episodes_final": None,
            "stage_2": None
        }
        
        # Загружаем Stage 1 (Сценарий)
        base_path = "data/1_base_structure.json"
        if os.path.exists(base_path):
            with open(base_path, "r", encoding="utf-8") as f:
                d1 = json.load(f)
                response_data["master_story"] = d1.get("master_story")
                response_data["episodes_raw"] = d1.get("episodes_raw")
                response_data["episodes_final"] = d1.get("episodes_final")
        
        # Загружаем Stage 2 (Раскадровка)
        prod_path = "data/2_production_map.json"
        if os.path.exists(prod_path):
            with open(prod_path, "r", encoding="utf-8") as f:
                data = json.load(f)
               
            
            result_s2 = {}
            for ep, scenes in data.get("episodes", {}).items():
                content = ""
                for idx, s in enumerate(scenes):
                    # Поддержка разных форматов полей
                    action = s.get('action', s.get('audio_segment', ''))
                    visual = s.get('visual', s.get('visual_prompt', ''))
                    content += f"🎬 Сцена {idx+1}:\n"
                    content += f"[Действие]: {action}\n"
                    content += f"[Визуал]: {visual}\n"
                    content += "-------------------\n"
                result_s2[ep] = content
            response_data["stage_2"] = result_s2

        if not response_data["master_story"] and not response_data["stage_2"]:
            return {"error": "Данные не найдены. Запустите генерацию."}

        return response_data
    except Exception as e:
        return {"error": str(e)}


@app.get("/episodes/refresh")
async def refresh_episodes():
    """Эндпоинт для внешнего вызова обновления данных (Stage 1/2 завершились)"""
    try:
        return await get_episodes()
    except Exception as e:
        return {"error": str(e)}


async def save_prompt(data: dict, stage_2_scenes: str = None):
    try:
        if os.path.exists("settings.json"):
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
        else:
            settings = {}

        if "prompts" not in settings:
            settings["prompts"] = {}

        # Обновляем stage_1_writer и stage_2_scenes
        if "stage_1_writer" in data:
            settings["prompts"]["stage_1_writer"] = data["stage_1_writer"]
        if stage_2_scenes:
            settings["prompts"]["stage_2_scenes"] = stage_2_scenes

        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)

        return {"message": "Промпт сохранён в settings.json"}
    except Exception as e:
        return {"error": str(e)}, 500


@app.post("/save-prompt")
async def post_save_prompt(data: dict):
    return await save_prompt(data)


@app.post("/save-prompt-stage2")
async def post_save_prompt_stage2(data: dict):
    return await save_prompt({}, stage_2_scenes=data.get("stage_2_scenes"))


@app.get("/status")
async def get_status():
    return {"stage": manager.current_stage_idx, "logs": manager.logs}


if __name__ == "__main__":
    import uvicorn
    import subprocess
    import time
    import os
    
    # Проверяем, запущен ли через python -m uvicorn
    run_via_uvicorn = os.environ.get("RUN_VIA_UVICORN") == "true"
    
    if run_via_uvicorn:
        # Просто запускаем сервер
        uvicorn.run(app, host="127.0.0.1", port=8000)
    else:
        # Запуск через run.py с cloudflared
        print("🚀 Запуск сервера с Cloudflare Tunnel...")
        print(f"   Текущий каталог: {os.getcwd()}")
        print("   Доступно на http://127.0.0.1:8000")
        
        # Запускаем сервер
        server = subprocess.Popen([
            "uvicorn", "src.main:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--reload",
            "--no-access-log",
            "--log-level", "warning"
        ], cwd=os.path.dirname(os.path.abspath(__file__)))
        
        # Ждём запуска сервера
        time.sleep(2)
        
        # Запускаем cloudflared tunnel
        try:
            tunnel = subprocess.Popen([
                "cloudflared", "tunnel", "--url", "http://127.0.0.1:8000"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("   🌍 Cloudflare Tunnel запущен")
            print("   (для публичного доступа откройте URL из логов cloudflared)")
        except FileNotFoundError:
            print("   ⚠️  cloudflared не найден в PATH")
            print("   Установите cloudflared или используйте локальный доступ")
        except Exception as e:
            print(f"   ⚠️  Ошибка запуска cloudflared: {e}")
        
        # Ждём завершения сервера
        try:
            server.wait()
        except KeyboardInterrupt:
            print("\n🛑 Остановка...")
            server.terminate()
            try:
                tunnel.terminate()
            except:
                pass