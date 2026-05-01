import os
import json
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from orchestrator import manager
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

class StartRequest(BaseModel):
    stage: int = 1
    idea: str = ""
    aspect_ratio: str = "9:16"  # Соотношение сторон
    quality: str = "1080p"      # Качество (высота)
    codec: str = "libx264"
    test_mode: bool = False     # Тестовый режим

@app.get("/settings")
async def get_settings():
    if os.path.exists("settings.json"):
        with open("settings.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {"aspect_ratio": "9:16", "quality": "1080p", "codec": "libx264", "test_mode": False}

@app.get("/", response_class=HTMLResponse)
async def index():
    stages_html = "".join([
        f"""<div class="stage-card" id="card-{i+1}">
            <h3>Этап {i+1}: {name}</h3>
            <button onclick="startFrom({i+1})">Начать с этого</button>
        </div>""" for i, (name, _) in enumerate(manager.stages)
    ])

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Video Studio</title>
        <style>
            :root {{ --bg: #fdf6f0; --card: #ffffff; --accent: #a8dadc; --text: #457b9d; --border: #f1faee; }}
            body {{ font-family: 'Segoe UI', sans-serif; background: var(--bg); padding: 20px; color: #1d3557; }}
            .container {{ max-width: 900px; margin: 0 auto; background: var(--card); padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
            h1 {{ text-align: center; color: var(--text); }}
            .settings-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; background: var(--border); padding: 20px; border-radius: 15px; }}
            .settings-item {{ display: flex; flex-direction: column; gap: 5px; }}
            .checkbox-item {{ flex-direction: row; align-items: center; gap: 10px; grid-column: span 2; padding: 10px; background: #fff; border-radius: 8px; }}
            select, textarea {{ padding: 10px; border-radius: 8px; border: 1px solid var(--accent); font-family: inherit; }}
            .main-btn {{ background: var(--text); color: white; padding: 15px; width: 100%; border-radius: 12px; margin-top: 10px; font-size: 18px; cursor: pointer; border: none; }}
            #logs {{ background: #f8f9fa; border-radius: 12px; padding: 15px; height: 250px; overflow-y: auto; font-family: monospace; font-size: 12px; margin-top: 20px; border: 1px solid #eee; }}
            .stages-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin-top: 20px; }}
            .stage-card {{ background: var(--border); padding: 10px; border-radius: 10px; text-align: center; font-size: 14px; }}
            .stage-card.active {{ border: 2px solid var(--accent); background: #fff; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎬 Video AI Pipeline</h1>
            
            <label><b>💡 Идея видео:</b></label><br>
            <textarea id="idea-input" style="width:100%" placeholder="О чем будет ролик?"></textarea>

            <div class="settings-grid">
                <div class="settings-item">
                    <label>Формат:</label>
                    <select id="aspect_ratio">
                        <option value="9:16">Вертикальный (9:16 - Shorts/Reels)</option>
                        <option value="16:9">Горизонтальный (16:9 - YouTube)</option>
                    </select>
                </div>
                <div class="settings-item">
                    <label>Качество:</label>
                    <select id="quality">
                        <option value="1080p">1080p (Full HD)</option>
                        <option value="720p">720p (HD)</option>
                        <option value="480p">480p (SD)</option>
                        <option value="360p">360p (Low)</option>
                        <option value="240p">240p (Draft)</option>
                    </select>
                </div>
                <div class="settings-item">
                    <label>Кодек:</label>
                    <select id="codec">
                        <option value="libx264">Процессор (libx264)</option>
                        <option value="h264_nvenc">GPU T4 (h264_nvenc)</option>
                    </select>
                </div>
                <div class="checkbox-item">
                    <input type="checkbox" id="test_mode">
                    <label for="test_mode"><b>🧪 Тестовый режим</b> (рендерить только первые 15 секунд)</label>
                </div>
            </div>

            <button class="main-btn" onclick="startFrom(1)">🚀 ЗАПУСТИТЬ ВСЁ</button>
            <div class="stages-grid">{stages_html}</div>
            <div id="logs"></div>
        </div>

        <script>
            window.onload = async () => {{
                const r = await fetch('/settings');
                const d = await r.json();
                document.getElementById('aspect_ratio').value = d.aspect_ratio || "9:16";
                document.getElementById('quality').value = d.quality || "1080p";
                document.getElementById('codec').value = d.codec || "libx264";
                document.getElementById('test_mode').checked = d.test_mode || false;
            }};

            async function startFrom(stageNum) {{
                const body = {{
                    stage: stageNum,
                    idea: document.getElementById('idea-input').value,
                    aspect_ratio: document.getElementById('aspect_ratio').value,
                    quality: document.getElementById('quality').value,
                    codec: document.getElementById('codec').value,
                    test_mode: document.getElementById('test_mode').checked
                }};
                await fetch('/start', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(body)
                }});
            }}

            setInterval(async () => {{
                const r = await fetch('/status');
                const d = await r.json();
                document.getElementById('logs').innerHTML = d.logs.map(l => `<div>${{l}}</div>`).join('');
                document.querySelectorAll('.stage-card').forEach((c, i) => c.classList.toggle('active', i+1 === d.stage));
            }}, 1500);
        </script>
    </body>
    </html>
    """

@app.post("/start")
async def start_task(req: StartRequest, background_tasks: BackgroundTasks):
    with open("settings.json", "w", encoding="utf-8") as f:
        json.dump(req.model_dump(), f, indent=4) # заменил .dict() на .model_dump() для совместимости с новыми версиями Pydantic
    background_tasks.add_task(manager.run_pipeline, start_from=req.stage, custom_idea=req.idea)
    return {"status": "started"}

@app.get("/status")
async def get_status():
    return {"stage": manager.current_stage_idx, "logs": manager.logs}

if __name__ == "__main__":
    import uvicorn
    # Логика Ngrok для Google Colab
    if os.getenv("NGROK_AUTH_TOKEN"):
        from pyngrok import ngrok
        ngrok.set_auth_token(os.getenv("NGROK_AUTH_TOKEN"))
        public_url = ngrok.connect(8000)
        print(f"🌍 Твой интерфейс доступен по ссылке: {public_url}")
        
    uvicorn.run(app, host="0.0.0.0", port=8000)