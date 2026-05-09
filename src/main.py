import os
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from fastapi.responses import JSONResponse

# Импортируем наши настройки и модели из созданного ранее config.py
from config import StartRequest, get_default_settings

app = FastAPI(title="AI Video Studio API")

# Определяем путь к текущей директории файла main.py
BASE_DIR = Path(__file__).resolve().parent

# Теперь указываем путь к static относительно main.py
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# То же самое стоит сделать для шаблонов чуть ниже:
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- ЭНДПОИНТЫ ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Создаем список этапов для интерфейса
    stages_list = [
        {"name": "Генерация сценария"},
        {"name": "Разбивка на сцены"},
        {"name": "Генерация промптов"},
        {"name": "Создание изображений"},
        {"name": "Озвучка (TTS)"},
        {"name": "Генерация видео"},
        {"name": "Сборка эпизода"},
        {"name": "Финальный монтаж"}
    ]
    
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "stages": stages_list  # ПЕРЕДАЕМ ПЕРЕМЕННУЮ В ШАБЛОН
        }
    )

@app.get("/settings")
async def get_settings():
    """Отдает текущие настройки фронтенду."""
    return JSONResponse(content=get_default_settings())

@app.post("/start")
async def start_pipeline(req: StartRequest, background_tasks: BackgroundTasks):
    """Запуск пайплайна в фоновом режиме."""
    # Здесь вызывается ваш оркестратор (manager.run_pipeline)
    # background_tasks.add_task(manager.run_pipeline, req)
    
    print(f"🚀 Запуск пайплайна: Этап {req.stage}, Идея: {req.idea[:30]}...")
    
    return {"status": "success", "message": f"Пайплайн запущен с этапа {req.stage}"}

@app.post("/update_settings")
async def update_settings(data: dict):
    """Сохранение новых настроек в JSON."""
    current = get_default_settings()
    current.update(data)
    with open("settings.json", "w", encoding="utf-8") as f:
        import json
        json.dump(current, f, indent=4, ensure_ascii=False)
    return {"status": "ok"}

@app.get("/status")
async def get_status():
    """Эндпоинт для опроса состояния пайплайна."""
    # В реальности тут должен быть запрос к manager.get_status()
    # Пока отдаем заглушку, чтобы JS не падал с 404
    return {
        "status": "idle", # или "running"
        "current_stage": 0,
        "progress": 0,
        "last_log": "Система готова"
    }

@app.get("/templates_data")
async def get_templates_data():
    """Отдает данные шаблонов для модального окна."""
    # Это данные, которые JS ждет для отрисовки модалки "Эпизоды"
    # Позже мы подключим сюда реальный template_manager
    return [
        {
            "id": "master",
            "name": "Основной сценарий",
            "content": "Здесь будет текст вашего сценария после генерации..."
        }
    ]

# --- ЗАПУСК ---

if __name__ == "__main__":
    # Запускаем локальный сервер
    print("🌍 Сервер STUDIO запущен на http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")