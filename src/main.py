from fastapi import FastAPI, BackgroundTasks, Body
from fastapi.responses import HTMLResponse
from orchestrator import manager
from pydantic import BaseModel

app = FastAPI()

class StartRequest(BaseModel):
    stage: int = 1

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Video Studio</title>
        <style>
            :root {
                --bg: #fdf6f0;
                --card: #ffffff;
                --accent: #a8dadc;
                --text: #457b9d;
                --error: #e63946;
                --success: #a7c957;
                --border: #f1faee;
            }
            body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: #1d3557; padding: 40px; }
            .container { max-width: 900px; margin: 0 auto; background: var(--card); padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }
            h1 { text-align: center; color: var(--text); font-weight: 300; margin-bottom: 30px; }
            
            /* Прогресс бар */
            .progress-container { background: var(--border); height: 12px; border-radius: 10px; margin: 20px 0; overflow: hidden; }
            #progress-bar { background: var(--accent); width: 0%; height: 100%; transition: width 0.5s ease; }
            
            /* Сетка этапов */
            .stages-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
            .stage-card { background: var(--border); padding: 15px; border-radius: 12px; border: 2px solid transparent; transition: 0.3s; position: relative;}
            .stage-card.active { border-color: var(--accent); background: #fff; transform: translateY(-3px); }
            .stage-card h3 { margin: 0 0 10px 0; font-size: 14px; color: var(--text); }
            
            button { background: var(--accent); border: none; color: #1d3557; padding: 8px 15px; border-radius: 8px; cursor: pointer; font-size: 12px; transition: 0.2s; }
            button:hover { filter: brightness(0.9); }
            button.main-btn { background: var(--text); color: white; padding: 15px 30px; font-size: 16px; width: 100%; border-radius: 12px; margin-top: 10px;}

            /* Логи */
            #logs { background: #f8f9fa; border-radius: 12px; padding: 20px; height: 350px; overflow-y: auto; font-family: 'Consolas', monospace; font-size: 13px; color: #333; line-height: 1.6; border: 1px solid #eee; }
            .log-entry { border-bottom: 1px solid #f0f0f0; padding: 4px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎬 Video AI Pipeline</h1>
            
            <div id="status-text" style="text-align: center; font-weight: bold; margin-bottom: 5px;">Ожидание</div>
            <div class="progress-container">
                <div id="progress-bar"></div>
            </div>

            <div class="stages-grid">
                """ + "".join([f"""
                <div class="stage-card" id="card-{i+1}">
                    <h3>Этап {i+1}: {name}</h3>
                    <button onclick="startFrom({i+1})">Начать с этого</button>
                </div>
                """ for i, (name, _) in enumerate(manager.stages)]) + """
            </div>

            <button class="main-btn" onclick="startFrom(1)">ЗАПУСТИТЬ ВЕСЬ ЦИКЛ</button>

            <h3>Консоль логов:</h3>
            <div id="logs"></div>
        </div>

        <script>
            async function updateStatus() {
                const r = await fetch('/status');
                const data = await r.json();
                
                document.getElementById('status-text').innerText = data.status;
                const progress = (data.stage / 8) * 100;
                document.getElementById('progress-bar').style.width = progress + '%';

                // Подсветка карточек
                document.querySelectorAll('.stage-card').forEach((card, idx) => {
                    card.classList.toggle('active', (idx + 1) === data.stage);
                });

                // Обновление логов
                const logDiv = document.getElementById('logs');
                const isAtBottom = logDiv.scrollHeight - logDiv.clientHeight <= logDiv.scrollTop + 1;
                logDiv.innerHTML = data.logs.map(l => `<div class="log-entry">${l}</div>`).join('');
                if (isAtBottom) logDiv.scrollTop = logDiv.scrollHeight;
            }

            async function startFrom(stageNum) {
                await fetch('/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({stage: stageNum})
                });
            }

            setInterval(updateStatus, 1500);
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    return {
        "status": manager.status,
        "stage": manager.current_stage_idx,
        "logs": manager.logs
    }

@app.post("/start")
async def start_task(req: StartRequest, background_tasks: BackgroundTasks):
    if not manager.is_running:
        background_tasks.add_task(manager.run_pipeline, start_from=req.stage)
        return {"message": f"Started from stage {req.stage}"}
    return {"message": "Already running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)