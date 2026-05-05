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
    stage:              int   = 1
    idea:               str   = ""
    aspect_ratio:       str   = "9:16"
    quality:            str   = "1080p"
    codec:              str   = "libx264"
    test_mode:          bool  = False
    use_colab_whisper:  bool  = False
    use_colab_render:   bool  = False
    colab_url:          str   = ""


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
    }


@app.get("/", response_class=HTMLResponse)
async def index():
    stages_data = [
        {"icon": "✍️",  "name": name}
        for name, _ in manager.stages
    ]
    stages_json = json.dumps(stages_data)

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>STUDIO — AI Video Pipeline</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
  --bg:        #0a0a0f;
  --surface:   #111118;
  --border:    #1e1e2e;
  --accent:    #7c3aed;
  --accent2:   #06b6d4;
  --accent3:   #f59e0b;
  --text:      #e2e8f0;
  --muted:     #64748b;
  --success:   #10b981;
  --danger:    #ef4444;
  --font-head: 'Syne', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}}

body {{
  font-family: var(--font-head);
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  overflow-x: hidden;
}}

/* ── NOISE TEXTURE ── */
body::before {{
  content: '';
  position: fixed; inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: 0;
}}

/* ── LAYOUT ── */
.shell {{
  position: relative;
  z-index: 1;
  max-width: 1100px;
  margin: 0 auto;
  padding: 40px 24px 80px;
}}

/* ── HEADER ── */
header {{
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 48px;
}}
.logo-mark {{
  width: 48px; height: 48px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}}
.logo-text h1 {{
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.5px;
  background: linear-gradient(90deg, #fff 40%, var(--accent2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}
.logo-text p {{
  font-size: 12px;
  color: var(--muted);
  font-family: var(--font-mono);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}}

/* ── MAIN GRID ── */
.main-grid {{
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 24px;
  align-items: start;
}}

/* ── CARD ── */
.card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
}}
.card-title {{
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  font-family: var(--font-mono);
  margin-bottom: 16px;
}}

/* ── IDEA TEXTAREA ── */
.idea-wrap {{
  position: relative;
  margin-bottom: 24px;
}}
.idea-wrap textarea {{
  width: 100%;
  height: 110px;
  background: #0d0d16;
  border: 1px solid var(--border);
  border-radius: 12px;
  color: var(--text);
  font-family: var(--font-head);
  font-size: 15px;
  padding: 16px;
  resize: none;
  outline: none;
  transition: border-color .2s;
  line-height: 1.6;
}}
.idea-wrap textarea:focus {{ border-color: var(--accent); }}
.idea-wrap textarea::placeholder {{ color: var(--muted); }}

/* ── SETTINGS ROW ── */
.settings-row {{
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}}
.field {{
  display: flex;
  flex-direction: column;
  gap: 6px;
}}
.field label {{
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  font-family: var(--font-mono);
}}
select {{
  background: #0d0d16;
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 13px;
  padding: 10px 12px;
  outline: none;
  cursor: pointer;
  transition: border-color .2s;
}}
select:focus {{ border-color: var(--accent); }}

/* ── TOGGLE SWITCH ── */
.toggle-row {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
}}
.toggle-row label {{ font-size: 13px; color: var(--text); cursor: pointer; }}
.toggle {{
  position: relative;
  width: 40px; height: 22px;
  flex-shrink: 0;
}}
.toggle input {{ opacity: 0; width: 0; height: 0; }}
.slider {{
  position: absolute; inset: 0;
  background: var(--border);
  border-radius: 22px;
  cursor: pointer;
  transition: .25s;
}}
.slider::before {{
  content: '';
  position: absolute;
  width: 16px; height: 16px;
  left: 3px; bottom: 3px;
  background: #fff;
  border-radius: 50%;
  transition: .25s;
}}
.toggle input:checked + .slider {{ background: var(--accent); }}
.toggle input:checked + .slider::before {{ transform: translateX(18px); }}

/* ── COLAB SECTION ── */
.colab-section {{
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  margin-top: 16px;
  background: #0d0d16;
}}
.colab-header {{
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-family: var(--font-mono);
  color: var(--accent2);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.colab-dot {{
  width: 7px; height: 7px;
  background: var(--accent2);
  border-radius: 50%;
  animation: pulse 2s infinite;
}}
@keyframes pulse {{
  0%, 100% {{ opacity: 1; }}
  50%       {{ opacity: 0.3; }}
}}
.colab-url-wrap {{
  margin-top: 12px;
}}
.colab-url-wrap label {{
  font-size: 11px;
  color: var(--muted);
  font-family: var(--font-mono);
  display: block;
  margin-bottom: 6px;
}}
.colab-url-wrap input {{
  width: 100%;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--accent2);
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 10px 12px;
  outline: none;
  transition: border-color .2s;
}}
.colab-url-wrap input:focus {{ border-color: var(--accent2); }}
.colab-toggles {{
  display: flex;
  flex-direction: column;
  gap: 4px;
}}

/* ── RUN BUTTON ── */
.run-btn {{
  width: 100%;
  padding: 16px;
  background: linear-gradient(135deg, var(--accent), #5b21b6);
  border: none;
  border-radius: 12px;
  color: #fff;
  font-family: var(--font-head);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.04em;
  cursor: pointer;
  margin-top: 20px;
  transition: opacity .2s, transform .1s;
  position: relative;
  overflow: hidden;
}}
.run-btn:hover  {{ opacity: 0.9; }}
.run-btn:active {{ transform: scale(0.99); }}
.run-btn::after {{
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 40%, rgba(255,255,255,0.08));
}}

/* ── SIDEBAR ── */
.sidebar {{ display: flex; flex-direction: column; gap: 16px; }}

/* ── PIPELINE ── */
.pipeline {{ display: flex; flex-direction: column; gap: 4px; }}
.stage-item {{
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: background .15s;
  border: 1px solid transparent;
}}
.stage-item:hover {{ background: rgba(124,58,237,0.08); border-color: rgba(124,58,237,0.2); }}
.stage-item.active {{
  background: rgba(124,58,237,0.12);
  border-color: var(--accent);
}}
.stage-num {{
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--muted);
  width: 18px;
  text-align: right;
  flex-shrink: 0;
}}
.stage-icon {{ font-size: 16px; flex-shrink: 0; }}
.stage-name {{ font-size: 13px; font-weight: 600; flex: 1; }}
.stage-badge {{
  font-size: 9px;
  font-family: var(--font-mono);
  background: rgba(6,182,212,0.15);
  color: var(--accent2);
  border: 1px solid rgba(6,182,212,0.3);
  border-radius: 4px;
  padding: 2px 6px;
}}
.stage-run-btn {{
  font-size: 11px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--muted);
  padding: 3px 8px;
  cursor: pointer;
  font-family: var(--font-mono);
  transition: all .15s;
  white-space: nowrap;
}}
.stage-run-btn:hover {{ border-color: var(--accent); color: var(--accent); }}

/* ── LOGS ── */
.logs-wrap {{
  background: #070710;
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 0;
  overflow: hidden;
  margin-top: 24px;
}}
.logs-header {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}}
.logs-title {{
  font-size: 11px;
  font-family: var(--font-mono);
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
}}
.live-dot {{
  width: 7px; height: 7px;
  background: var(--success);
  border-radius: 50%;
  animation: pulse 1.5s infinite;
}}
.logs-body {{
  height: 280px;
  overflow-y: auto;
  padding: 16px;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.7;
  color: #94a3b8;
}}
.logs-body::-webkit-scrollbar {{ width: 4px; }}
.logs-body::-webkit-scrollbar-track {{ background: transparent; }}
.logs-body::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}
.log-line {{ padding: 1px 0; }}
.log-line.success {{ color: var(--success); }}
.log-line.error   {{ color: var(--danger); }}
.log-line.stage   {{ color: #fff; font-weight: 600; }}
.log-line.info    {{ color: var(--accent2); }}

/* ── STATUS BAR ── */
.status-bar {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  font-family: var(--font-mono);
  font-size: 12px;
}}
.status-indicator {{
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--muted);
  flex-shrink: 0;
}}
.status-indicator.running {{ background: var(--accent3); animation: pulse 1s infinite; }}
.status-indicator.done    {{ background: var(--success); }}
.status-indicator.error   {{ background: var(--danger); }}
.status-text {{ color: var(--muted); }}

@media (max-width: 768px) {{
  .main-grid {{ grid-template-columns: 1fr; }}
  .settings-row {{ grid-template-columns: 1fr 1fr; }}
}}
</style>
</head>
<body>
<div class="shell">

  <header>
    <div class="logo-mark">🎬</div>
    <div class="logo-text">
      <h1>AI VIDEO STUDIO</h1>
      <p>Hybrid Pipeline · Colab GPU Mode</p>
    </div>
  </header>

  <div class="main-grid">

    <!-- ── LEFT COLUMN ── -->
    <div>

      <div class="card" style="margin-bottom:16px">
        <div class="card-title">Идея / Сценарий</div>
        <div class="idea-wrap">
          <textarea id="idea-input" placeholder="Введите тему, идею или полный сценарий ролика..."></textarea>
        </div>

        <div class="settings-row">
          <div class="field">
            <label>Формат</label>
            <select id="aspect_ratio">
              <option value="9:16">9:16 · Shorts / TikTok</option>
              <option value="16:9">16:9 · YouTube</option>
            </select>
          </div>
          <div class="field">
            <label>Качество</label>
            <select id="quality">
              <option value="1080p">1080p · Full HD</option>
              <option value="720p">720p · HD</option>
              <option value="480p">480p · SD</option>
              <option value="360p">360p · Low</option>
              <option value="240p">240p · Min</option>
            </select>
          </div>
          <div class="field">
            <label>Кодек</label>
            <select id="codec">
              <option value="libx264">CPU · libx264</option>
              <option value="h264_nvenc">GPU · h264_nvenc</option>
            </select>
          </div>
        </div>

        <div class="toggle-row">
          <label class="toggle">
            <input type="checkbox" id="test_mode">
            <span class="slider"></span>
          </label>
          <label for="test_mode">🧪 Тестовый режим <span style="color:var(--muted);font-size:12px">(первые 15 сек)</span></label>
        </div>

        <!-- COLAB SECTION -->
        <div class="colab-section">
          <div class="colab-header">
            <div class="colab-dot"></div>
            Google Colab · Cloud GPU
          </div>

          <div class="colab-toggles">
            <div class="toggle-row">
              <label class="toggle">
                <input type="checkbox" id="use_colab_whisper" onchange="onColabChange()">
                <span class="slider"></span>
              </label>
              <label for="use_colab_whisper">☁️ Whisper на Colab <span style="color:var(--muted);font-size:12px">(субтитры)</span></label>
            </div>
            <div class="toggle-row">
              <label class="toggle">
                <input type="checkbox" id="use_colab_render" onchange="onColabChange()">
                <span class="slider"></span>
              </label>
              <label for="use_colab_render">☁️ Рендер на Colab <span style="color:var(--muted);font-size:12px">(GPU FFmpeg)</span></label>
            </div>
          </div>

          <div class="colab-url-wrap" id="colab_url_wrap" style="display:none">
            <label>Ngrok URL из Colab:</label>
            <input type="text" id="colab_url" placeholder="https://xxxx-xxxx.ngrok-free.app">
          </div>
        </div>

        <button class="run-btn" onclick="startFrom(1)">▶ ЗАПУСТИТЬ ПОЛНЫЙ ЦИКЛ</button>
      </div>

      <!-- LOGS -->
      <div class="logs-wrap">
        <div class="logs-header">
          <div class="live-dot"></div>
          <span class="logs-title">Pipeline Logs</span>
        </div>
        <div class="logs-body" id="logs">
          <div class="log-line" style="color:var(--muted)">Ожидание запуска...</div>
        </div>
      </div>

    </div>

    <!-- ── SIDEBAR ── -->
    <div class="sidebar">

      <div class="card">
        <div class="card-title">Статус</div>
        <div class="status-bar">
          <div class="status-indicator" id="status-dot"></div>
          <span class="status-text" id="status-text">Ожидание</span>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Pipeline · Этапы</div>
        <div class="pipeline" id="pipeline"></div>
      </div>

    </div>
  </div>

</div>

<script>
const STAGES = {stages_json};

const STAGE_ICONS = ["✍️","🎬","👤","🖼️","🔊","📝","📋","🎞️"];
const COLAB_STAGES = [5, 7]; // субтитры и рендер (0-indexed)

// ── INIT PIPELINE ──
function buildPipeline() {{
  const el = document.getElementById('pipeline');
  el.innerHTML = STAGES.map((s, i) => {{
    const isColab = COLAB_STAGES.includes(i);
    return `
      <div class="stage-item" id="stage-${{i+1}}" onclick="">
        <span class="stage-num">${{i+1}}</span>
        <span class="stage-icon">${{STAGE_ICONS[i] || '⚙️'}}</span>
        <span class="stage-name">${{s.name}}</span>
        ${{isColab ? '<span class="stage-badge">COLAB</span>' : ''}}
        <button class="stage-run-btn" onclick="event.stopPropagation();startFrom(${{i+1}})">▶</button>
      </div>`;
  }}).join('');
}}

// ── COLAB URL VISIBILITY ──
function onColabChange() {{
  const w = document.getElementById('use_colab_whisper').checked;
  const r = document.getElementById('use_colab_render').checked;
  document.getElementById('colab_url_wrap').style.display = (w || r) ? 'block' : 'none';
}}

// ── LOAD SAVED SETTINGS ──
window.onload = async () => {{
  buildPipeline();
  try {{
    const r = await fetch('/settings');
    const d = await r.json();
    document.getElementById('aspect_ratio').value        = d.aspect_ratio || '9:16';
    document.getElementById('quality').value             = d.quality || '1080p';
    document.getElementById('codec').value               = d.codec || 'libx264';
    document.getElementById('test_mode').checked         = d.test_mode || false;
    document.getElementById('use_colab_whisper').checked = d.use_colab_whisper || false;
    document.getElementById('use_colab_render').checked  = d.use_colab_render  || false;
    document.getElementById('colab_url').value           = d.colab_url || '';
    onColabChange();
  }} catch(e) {{ console.warn('Settings load failed', e); }}
}};

// ── START ──
async function startFrom(stageNum) {{
  const body = {{
    stage:             stageNum,
    idea:              document.getElementById('idea-input').value,
    aspect_ratio:      document.getElementById('aspect_ratio').value,
    quality:           document.getElementById('quality').value,
    codec:             document.getElementById('codec').value,
    test_mode:         document.getElementById('test_mode').checked,
    use_colab_whisper: document.getElementById('use_colab_whisper').checked,
    use_colab_render:  document.getElementById('use_colab_render').checked,
    colab_url:         document.getElementById('colab_url').value,
  }};
  await fetch('/start', {{
    method:  'POST',
    headers: {{'Content-Type': 'application/json'}},
    body:    JSON.stringify(body),
  }});
}}

// ── LOG COLORING ──
function classifyLog(line) {{
  if (line.includes('✅') || line.includes('🎉'))  return 'success';
  if (line.includes('❌') || line.includes('⚠️')) return 'error';
  if (line.includes('━━━') || line.includes('---')) return 'stage';
  if (line.includes('☁️') || line.includes('📤') || line.includes('📥')) return 'info';
  return '';
}}

// ── POLL STATUS ──
setInterval(async () => {{
  try {{
    const r = await fetch('/status');
    const d = await r.json();

    // Logs
    const logsDiv = document.getElementById('logs');
    logsDiv.innerHTML = d.logs.map(l =>
      `<div class="log-line ${{classifyLog(l)}}">${{l}}</div>`
    ).join('');
    logsDiv.scrollTop = logsDiv.scrollHeight;

    // Active stage
    document.querySelectorAll('.stage-item').forEach((el, i) =>
      el.classList.toggle('active', i + 1 === d.stage)
    );

    // Status dot
    const dot  = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    const last = d.logs[d.logs.length - 1] || '';
    if (last.includes('❌'))             {{ dot.className='status-indicator error';   text.textContent='Ошибка'; }}
    else if (last.includes('🎉'))        {{ dot.className='status-indicator done';    text.textContent='Завершено'; }}
    else if (d.stage > 0 && !last.includes('🎉')) {{ dot.className='status-indicator running'; text.textContent='Выполняется...'; }}
    else                                 {{ dot.className='status-indicator';          text.textContent='Ожидание'; }}
  }} catch(e) {{}}
}}, 1500);
</script>
</body>
</html>"""


@app.post("/start")
async def start_task(req: StartRequest, background_tasks: BackgroundTasks):
    with open("settings.json", "w", encoding="utf-8") as f:
        json.dump(req.model_dump(), f, indent=4, ensure_ascii=False)
    background_tasks.add_task(manager.run_pipeline, start_from=req.stage, custom_idea=req.idea)
    return {"status": "started"}


@app.get("/status")
async def get_status():
    return {"stage": manager.current_stage_idx, "logs": manager.logs}


if __name__ == "__main__":
    import uvicorn
    if os.getenv("NGROK_AUTH_TOKEN"):
        from pyngrok import ngrok
        ngrok.set_auth_token(os.getenv("NGROK_AUTH_TOKEN"))
        public_url = ngrok.connect(8000).public_url
        print(f"🌍 Studio: {public_url}")
    uvicorn.run(app, host="127.0.0.1", port=8000)