import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from orchestrator import manager
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

class StartRequest(BaseModel):
    stage: int = 1
    idea: str = ""  # Новое поле для идеи

@app.get("/", response_class=HTMLResponse)
async def index():
    # Генерируем карточки этапов программно из менеджера
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
            body {{ font-family: 'Segoe UI', sans-serif; background: var(--bg); padding: 40px; color: #1d3557; }}
            .container {{ max-width: 900px; margin: 0 auto; background: var(--card); padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
            h1 {{ text-align: center; color: var(--text); }}
            .progress-container {{ background: var(--border); height: 12px; border-radius: 10px; margin: 20px 0; overflow: hidden; }}
            #progress-bar {{ background: var(--accent); width: 0%; height: 100%; transition: width 0.5s ease; }}
            .stages-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
            .stage-card {{ background: var(--border); padding: 15px; border-radius: 12px; transition: 0.3s; }}
            .stage-card.active {{ border: 2px solid var(--accent); background: #fff; transform: translateY(-3px); }}
            textarea {{ width: 100%; height: 100px; border-radius: 10px; border: 1px solid var(--accent); padding: 15px; margin-top: 10px; box-sizing: border-box; font-family: inherit; }}
            button {{ background: var(--accent); border: none; padding: 8px 15px; border-radius: 8px; cursor: pointer; }}
            .main-btn {{ background: var(--text); color: white; padding: 15px; width: 100%; border-radius: 12px; margin-top: 20px; font-size: 18px; }}
            #logs {{ background: #f8f9fa; border-radius: 12px; padding: 20px; height: 300px; overflow-y: auto; font-family: monospace; font-size: 12px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎬 Video AI Pipeline</h1>
            <div id="status-text" style="text-align: center;">Ожидание</div>
            <div class="progress-container"><div id="progress-bar"></div></div>
            
            <label><b>💡 Введи идею для видео:</b></label>
            <textarea id="idea-input" placeholder="Например: История о забытом роботе в лесу..."></textarea>

            <div class="stages-grid">{stages_html}</div>
            <button class="main-btn" onclick="startFrom(1)">🚀 ЗАПУСТИТЬ ВЕСЬ ЦИКЛ</button>
            <div id="logs"></div>
        </div>

        <script>
            async function updateStatus() {{
                const r = await fetch('/status');
                const data = await r.json();
                document.getElementById('status-text').innerText = data.status;
                document.getElementById('progress-bar').style.width = (data.stage / {len(manager.stages)}) * 100 + '%';
                document.querySelectorAll('.stage-card').forEach((c, i) => c.classList.toggle('active', i+1 === data.stage));
                document.getElementById('logs').innerHTML = data.logs.map(l => `<div>${{l}}</div>`).join('');
            }}
            async function startFrom(stageNum) {{
                const ideaText = document.getElementById('idea-input').value;
                await fetch('/start', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{stage: stageNum, idea: ideaText}})
                }});
            }}
            setInterval(updateStatus, 1500);
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    return {"status": manager.status, "stage": manager.current_stage_idx, "logs": manager.logs}

@app.post("/start")
async def start_task(req: StartRequest, background_tasks: BackgroundTasks):
    if not manager.is_running:
        background_tasks.add_task(manager.run_pipeline, start_from=req.stage, custom_idea=req.idea)
        return {"message": "Started"}
    return {"message": "Already running"}

if __name__ == "__main__":
    import uvicorn
    # Логика Ngrok для Google Colab
    if os.getenv("NGROK_AUTH_TOKEN"):
        from pyngrok import ngrok
        ngrok.set_auth_token(os.getenv("NGROK_AUTH_TOKEN"))
        public_url = ngrok.connect(8000)
        print(f"🌍 Твой интерфейс доступен по ссылке: {public_url}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)