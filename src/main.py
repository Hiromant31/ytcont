import os
import json
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse
from .orchestrator import manager
from .template_manager import (
    get_all_templates, get_template, create_template, update_template,
    delete_template, duplicate_template, archive_template,
    get_default_template, create_template_version, get_template_versions,
    restore_template_version, export_template, import_template,
    # V2 functions
    add_template_prompt, update_template_prompt, delete_template_prompt,
    get_template_prompts, add_template_setting, update_template_setting,
    delete_template_setting, get_template_settings, get_all_prompts_for_stage
)
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()


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

/* ── AI SETTINGS SECTION ── */
.ai-settings-section {{
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  margin-top: 16px;
  background: #0d0d16;
}}
.ai-settings-header {{
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-family: var(--font-mono);
  color: var(--accent3);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}}
.ai-settings-content {{
  display: none;
  flex-direction: column;
  gap: 12px;
}}
.ai-settings-section.expanded .ai-settings-content {{
  display: flex;
}}
.ai-settings-section.expanded .ai-settings-header {{
  color: var(--accent);
}}
.ai-row {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}}
.ai-row-full {{
  grid-template-columns: 1fr;
}}
.ai-field {{
  display: flex;
  flex-direction: column;
  gap: 6px;
}}
.ai-field label {{
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  font-family: var(--font-mono);
}}
.ai-field input, .ai-field select {{
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 8px 10px;
  outline: none;
  transition: border-color .2s;
}}
.ai-field input:focus, .ai-field select:focus {{ border-color: var(--accent); }}
.ai-field input.placeholder-text {{ color: var(--muted); }}

/* ── PROMPT EDITOR ── */
.prompt-editor-section {{
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  margin-top: 16px;
  background: #0d0d16;
}}
.prompt-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}}
.prompt-title {{
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-family: var(--font-mono);
  color: var(--accent2);
}}
.prompt-toggle {{
  font-size: 9px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--muted);
  padding: 4px 8px;
  cursor: pointer;
  font-family: var(--font-mono);
  transition: all .15s;
}}
.prompt-toggle:hover {{ border-color: var(--accent); color: var(--accent); }}
.prompt-content {{
  display: none;
}}
.prompt-editor-section.expanded .prompt-content {{
  display: block;
}}
.prompt-textarea {{
  width: 100%;
  height: 150px;
  background: #070710;
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 10px;
  resize: vertical;
  outline: none;
  line-height: 1.5;
}}
.prompt-textarea:focus {{ border-color: var(--accent2); }}

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

/* ── TABS ── */
.modal-tabs {{
  display: flex;
  gap: 4px;
  padding: 0 24px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}}
.tab-btn {{
  padding: 12px 16px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 11px;
  text-transform: uppercase;
  cursor: pointer;
  transition: all .2s;
}}
.tab-btn:hover {{ color: var(--text); }}
.tab-btn.active {{
  color: var(--accent);
  border-bottom-color: var(--accent);
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
.stage-item {{Mail: aiqyynf1451@outlook.com
Mail password: iLahQN616uQdk 
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

/* ── MODAL ── */
.modal-overlay {{
  display: none;
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.75);
  backdrop-filter: blur(6px);
  z-index: 1000;
  align-items: center;
  justify-content: center;
}}
.modal-overlay.open {{ display: flex; }}
.modal-box {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  width: min(780px, 95vw);
  max-height: 82vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}
.modal-head {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}}
.modal-title {{
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.3px;
}}
.modal-close {{
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--muted);
  font-size: 18px;
  width: 34px; height: 34px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all .15s;
}}
.modal-close:hover {{ border-color: var(--danger); color: var(--danger); }}
.modal-body {{
  overflow-y: auto;
  padding: 24px;
  flex: 1;
}}
.modal-body::-webkit-scrollbar {{ width: 4px; }}
.modal-body::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}
.episode-block {{
  margin-bottom: 28px;
}}
.episode-label {{
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-family: var(--font-mono);
  color: var(--accent2);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.episode-label::after {{
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}}
.episode-text {{
  font-size: 14px;
  line-height: 1.8;
  color: var(--text);
  white-space: pre-wrap;
  font-family: var(--font-head);
}}
.modal-empty {{
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 13px;
  text-align: center;
  padding: 40px 0;
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
            <label>Эпизоды</label>
            <input type="number" id="num_episodes" value="3" min="1" max="20" style="width:100%;padding:10px 12px;background:#0d0d16;border:1px solid var(--border);border-radius:8px;color:var(--text);font-family:var(--font-mono);font-size:13px;outline:none">
          </div>
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
            <label>Codec</label>
            <select id="codec">
              <option value="libx264">libx264 · H.264</option>
              <option value="libx265">libx265 · H.265</option>
              <option value="libvp9">libvp9 · VP9</option>
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

        <!-- AI SETTINGS SECTION -->
        <div class="ai-settings-section" id="ai-settings-section">
          <div class="ai-settings-header" onclick="toggleAiSettings()">
            <span>⚙️ Настройки AI (Текст)</span>
            <span style="font-size:10px;opacity:0.6">▼</span>
          </div>
          <div class="ai-settings-content">
            <div class="ai-row-full">
              <div class="ai-field">
                <label>API URL</label>
                <input type="text" id="ai_api_url" placeholder="https://ai.api.cloud.yandex.net/v1">
              </div>
            </div>
            <div class="ai-row-full">
              <div class="ai-field">
                <label>API Key</label>
                <input type="password" id="ai_api_key" placeholder="AQVN...">
              </div>
            </div>
            <div class="ai-row">
              <div class="ai-field">
                <label>Folder ID <span style="color:var(--muted);font-size:10px">(только Yandex)</span></label>
                <input type="text" id="ai_folder_id" placeholder="b1g...">
              </div>
              <div class="ai-field">
                <label>Модель</label>
                <input type="text" id="ai_model" placeholder="gemma-3-27b-it/latest">
              </div>
            </div>
            <button class="run-btn" style="margin-top:4px;padding:10px;font-size:13px" onclick="saveAiSettings()">💾 Сохранить настройки AI</button>
          </div>
        </div>

        <!-- PROMPT EDITOR SECTION -->
        <div class="prompt-editor-section" id="prompt-editor-section">
          <div class="prompt-header">
            <div class="prompt-title">📝 Промпт Stage 1 (Сценарий)</div>
            <button class="prompt-toggle" onclick="togglePromptEditor()">редактировать</button>
          </div>
          <div class="prompt-content">
            <textarea class="prompt-textarea" id="prompt_writer" placeholder="Введите промпт для генерации сценария..."></textarea>
            <button class="run-btn" style="margin-top:12px;padding:10px;font-size:13px" onclick="savePrompt()">💾 Сохранить промпт</button>
          </div>
        </div>

        <!-- PROMPT STAGE 2 SECTION -->
        <div class="prompt-editor-section" id="prompt-stage-2-section">
          <div class="prompt-header">
            <div class="prompt-title">🎬 Промпт Stage 2 (Раскадровка)</div>
            <button class="prompt-toggle" onclick="togglePromptStage2Editor()">редактировать</button>
          </div>
          <div class="prompt-content">
            <textarea class="prompt-textarea" id="prompt_stage_2" placeholder="Инструкции для режиссера..."></textarea>
            <button class="run-btn" style="margin-top:12px;padding:10px;font-size:13px" onclick="savePromptStage2()">💾 Сохранить промпт</button>
          </div>
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

        <div class="toggle-row" style="margin-top:12px">
          <label class="toggle">
            <input type="checkbox" id="auto_continue" checked>
            <span class="slider"></span>
          </label>
          <label for="auto_continue">🔄 Продолжать автоматически</label>
        </div>
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
        <button class="run-btn" style="margin-top:14px;padding:10px;font-size:13px;background:linear-gradient(135deg,#0f766e,#0891b2)" onclick="openEpisodesModal()">📖 Просмотр эпизодов</button>
      </div>

      <div class="card">
        <div class="card-title">🎭 Prompt Templates</div>
        <div style="display:flex; gap:8px; margin-bottom:12px;">
          <button onclick="openTemplatesList()" style="flex:1; padding:8px; background:transparent; border:1px solid var(--accent); border-radius:8px; color:var(--accent); cursor:pointer; font-size:13px;">📋 Открыть шаблоны</button>
          <button onclick="openCreateTemplateModal()" style="flex:1; padding:8px; background:var(--accent); border:none; border-radius:8px; color:#fff; cursor:pointer; font-size:13px;">➕ Новый шаблон</button>
          <button onclick="refreshTemplates()" style="padding:8px 12px; background:transparent; border:1px solid var(--border); border-radius:8px; color:var(--text); cursor:pointer; font-size:13px;">🔄</button>
        </div>
        <div id="templates-list" style="display:grid; gap:8px; max-height:150px; overflow-y:auto;">
          <div class="log-line" style="color:var(--muted); font-size:12px;">Загрузка шаблонов...</div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Pipeline · Этапы</div>
        <div class="pipeline" id="pipeline"></div>
      </div>

    </div>
  </div>

</div>

<!-- ── TEMPLATES MODAL ── -->
<div class="modal-overlay" id="templates-modal" onclick="closeTemplatesModal(event)">
<div class="modal-box" style="max-height:70vh;">
    <div class="modal-head">
      <span class="modal-title">🎭 Выбор шаблона</span>
      <button class="modal-close" onclick="closeTemplatesModal(event)">✕</button>
    </div>
    <div class="modal-body" id="available-templates-list" style="max-height:400px; overflow-y:auto;">
      <div class="modal-empty">Загрузка...</div>
    </div>
    <div style="padding:16px 24px; border-top:1px solid var(--border); display:flex; gap:8px; justify-content:flex-end;">
      <button class="run-btn" onclick="applySelectedTemplate()" style="padding:12px; font-size:14px; flex:1;">Применить шаблон</button>
    </div>
</div>
</div>

<!-- ── EDIT TEMPLATE MODAL ── -->
<div class="modal-overlay" id="edit-template-modal" onclick="closeEditTemplateModal(event)">
<div class="modal-box" onclick="event.stopPropagation()>
    <div class="modal-head">
      <span class="modal-title" id="edit-template-title">Редактор шаблона</span>
      <button class="modal-close" onclick="closeEditTemplateModal(event)">✕</button>
    </div>
    <div class="modal-body">
      <input type="hidden" id="edit-template-id">
      
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:12px;">
        <div>
          <label style="display:block; font-size:11px; color:var(--muted); font-family:var(--font-mono); margin-bottom:4px;">Название</label>
          <input type="text" id="edit-template-name" style="width:100%; padding:8px; background:var(--bg); border:1px solid var(--border); border-radius:6px; color:var(--text); font-family:var(--font-mono); font-size:13px;">
        </div>
        <div>
          <label style="display:block; font-size:11px; color:var(--muted); font-family:var(--font-mono); margin-bottom:4px;">Категория</label>
          <input type="text" id="edit-template-category" style="width:100%; padding:8px; background:var(--bg); border:1px solid var(--border); border-radius:6px; color:var(--text); font-family:var(--font-mono); font-size:13px;">
        </div>
      </div>
      
      <div style="margin-bottom:12px;">
        <label style="display:block; font-size:11px; color:var(--muted); font-family:var(--font-mono); margin-bottom:4px;">Описание</label>
        <textarea id="edit-template-description" style="width:100%; height:60px; padding:8px; background:var(--bg); border:1px solid var(--border); border-radius:6px; color:var(--text); font-family:var(--font-mono); font-size:13px; resize:vertical;"></textarea>
      </div>

      <!-- PROMPTS SECTION - V2 Structure -->
      <div style="margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <label style="display:block; font-size:11px; color:var(--accent2); font-family:var(--font-mono);">Prompts (V2)</label>
          <button onclick="addPromptField()" style="padding:4px 10px; font-size:10px; background:var(--accent); border:none; border-radius:4px; color:#fff; cursor:pointer;">➕ Добавить</button>
        </div>
        <div id="edit-template-prompts-container" style="display:flex; flex-direction:column; gap:8px;">
          <div style="color:var(--muted); font-size:12px;">Загрузка промптов...</div>
        </div>
      </div>

      <!-- SETTINGS SECTION - V2 Structure -->
      <div style="margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <label style="display:block; font-size:11px; color:var(--accent3); font-family:var(--font-mono);">Settings (V2)</label>
          <button onclick="addSettingField()" style="padding:4px 10px; font-size:10px; background:var(--accent3); border:none; border-radius:4px; color:#fff; cursor:pointer;">➕ Добавить</button>
        </div>
        <div id="edit-template-settings-container" style="display:flex; flex-direction:column; gap:8px;">
          <div style="color:var(--muted); font-size:12px;">Загрузка настроек...</div>
        </div>
      </div>

      <div style="display:flex; gap:8px; justify-content:flex-end;">
        <button onclick="deleteCurrentTemplate()" style="padding:8px 16px; background:transparent; border:1px solid var(--danger); border-radius:6px; color:var(--danger); cursor:pointer; font-family:var(--font-mono); font-size:12px;">🗑️ Удалить</button>
        <button onclick="saveTemplate()" style="padding:8px 16px; background:var(--accent); border:none; border-radius:6px; color:#fff; cursor:pointer; font-family:var(--font-mono); font-size:12px;">💾 Сохранить</button>
      </div>
    </div>
</div>
</div>

<!-- ── EPISODES MODAL ── -->
<div class="modal-overlay" id="episodes-modal" onclick="closeEpisodesModal(event)">
<div class="modal-box">
    <div class="modal-head">
      <span class="modal-title">📖 Просмотр данных</span>
      <div style="display:flex;gap:8px">
        <button class="modal-close" style="width:auto" onclick="refreshEpisodesModal()">🔄</button>
        <button class="modal-close" onclick="document.getElementById('episodes-modal').classList.remove('open')">✕</button>
      </div>
    </div>
    <!-- Добавляем вкладки -->
    <div class="modal-tabs">
      <button class="tab-btn active" onclick="switchTab('master')">Master Story</button>
      <button class="tab-btn" onclick="switchTab('raw')">Episodes Raw</button>
      <button class="tab-btn" onclick="switchTab('final')">Episodes Final</button>
      <button class="tab-btn" onclick="switchTab('stage2')">Stage 2 (Раскадровка)</button>
    </div>
    <div class="modal-body" id="episodes-modal-body">
      <div class="modal-empty">Загрузка...</div>
    </div>
</div>
</div>

<script>
const STAGES = {stages_json};

const STAGE_ICONS = ["✍️","🎬","👤","🖼️","🔊","📝","📋","🎞️"];
const COLAB_STAGES = [5, 7]; // субтитры и рендер (0-indexed)

// ── INIT PIPELINE ──
function buildPipeline() {{
  const stages = {stages_json};
  const el = document.getElementById('pipeline');
  if (!el) return;

  const colabStages = [5, 7]; // Индексы этапов для Colab

  el.innerHTML = stages.map((s, i) => {{
    const stageNum = i + 1;
    const isColab = colabStages.includes(stageNum);
    // Для интерполяции в JS внутри f-строки используем ${{...}}
    return `
      <div class="stage-item" id="stage-${{stageNum}}" onclick="startFrom(${{stageNum}})">
        <span class="stage-num">${{stageNum}}</span>
        <span class="stage-icon">${{s.icon || '⚙️'}}</span>
        <span class="stage-name">${{s.name}}</span>
        ${{isColab ? '<span class="stage-badge">COLAB</span>' : ''}}
        <button class="stage-run-btn">▶</button>
      </div>`;
  }}).join('');
}}


// ── TEMPLATE FUNCTIONS ──
let currentTemplates = [];

async function loadTemplates() {{
  try {{
    const r = await fetch('/api/templates');
    const d = await r.json();
    currentTemplates = d.templates || [];
    renderTemplatesList();
    return d;
  }} catch(e) {{
    console.error('Load templates failed', e);
    return {{ templates: [] }};
  }}
}}

function renderTemplatesList() {{
  const list = document.getElementById('templates-list');
  if (!currentTemplates || currentTemplates.length === 0) {{
    list.innerHTML = '<div class="log-line" style="color:var(--muted); font-size:12px;">Нет шаблонов. Создайте новый!</div>';
    return;
  }}

  let html = '';
  currentTemplates.forEach(t => {{
    const statusClass = t.archived ? 'status-indicator error' : (t.is_default ? 'status-indicator done' : 'status-indicator running');
    const statusText = t.archived ? 'Архив' : (t.is_default ? 'Дефолт' : 'Активен');
    html += `<div class="card" style="padding:10px; margin-bottom:8px;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <strong style="font-size:13px;">${{t.name || t.id}}</strong>
          <span style="font-size:11px; color:var(--muted); margin-left:8px;">${{t.category || 'Без категории'}}</span>
        </div>
        <span style="font-size:10px; background:rgba(6,182,212,0.15); color:var(--accent2); padding:2px 6px; border-radius:4px;">${{statusText}}</span>
      </div>
      <div style="font-size:11px; color:var(--muted); margin-top:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${{t.description || 'Без описания'}}</div>
      <div style="display:flex; gap:6px; margin-top:8px;">
        <button onclick="openTemplateEditor('${{t.id}}')" style="flex:1; padding:4px 8px; font-size:10px; background:var(--accent); border:none; border-radius:4px; color:#fff; cursor:pointer;">✎</button>
        <button onclick="duplicateTemplate('${{t.id}}')" style="padding:4px 8px; font-size:10px; background:transparent; border:1px solid var(--border); border-radius:4px; color:var(--text); cursor:pointer;">⧉</button>
        <button onclick="archiveTemplate('${{t.id}}', ${{!t.archived}})" style="padding:4px 8px; font-size:10px; background:transparent; border:1px solid var(--border); border-radius:4px; color:var(--text); cursor:pointer;">${{t.archived ? 'Разархив' : 'Архив'}}</button>
        <button onclick="deleteTemplate('${{t.id}}')" style="padding:4px 8px; font-size:10px; background:transparent; border:1px solid var(--danger); border-radius:4px; color:var(--danger); cursor:pointer;">🗑️</button>
      </div>
    </div>`;
  }});
  list.innerHTML = html;
}}

async function refreshTemplates() {{
  await loadTemplates();
}}

async function openTemplatesModal() {{
  const modal = document.getElementById('templates-modal');
  modal.classList.add('open');
  await loadAvailableTemplates();
}}

async function closeTemplatesModal(e) {{
  if (!e || e.target === document.getElementById('templates-modal')) {{
    document.getElementById('templates-modal').classList.remove('open');
  }}
}}

async function closeEditTemplateModal(e) {{
  if (!e || e.target === document.getElementById('edit-template-modal')) {{
    document.getElementById('edit-template-modal').classList.remove('open');
  }}
}}

async function loadAvailableTemplates() {{
  const list = document.getElementById('available-templates-list');
  try {{
    const r = await fetch('/api/templates');
    const d = await r.json();

    let html = '';
    d.templates.forEach(t => {{
      html += `<div class="card" style="padding:12px;">
        <div style="display:flex; justify-content:space-between;">
          <div>
            <strong style="font-size:14px;">${{t.name || t.id}}</strong>
            <span style="font-size:11px; color:var(--muted); margin-left:8px;">${{t.category || 'Без категории'}}</span>
          </div>
          <button onclick="selectTemplateForApply('${{t.id}}')" style="padding:4px 12px; font-size:12px; background:var(--accent); border:none; border-radius:4px; color:#fff; cursor:pointer;">Выбрать</button>
        </div>
        <div style="font-size:12px; color:var(--text); margin-top:4px;">${{t.description || 'Без описания'}}</div>
      </div>`;
    }});

    if (d.templates.length === 0) {{
      html = '<div class="modal-empty">Нет шаблонов. Создайте новый!</div>';
    }}

    list.innerHTML = html;
  }} catch(e) {{
    list.innerHTML = '<div class="modal-empty">❌ Ошибка загрузки</div>';
  }}
}}

let selectedTemplateId = null;

async function selectTemplateForApply(templateId) {{
  selectedTemplateId = templateId;
  document.getElementById('templates-modal').classList.remove('open');
}}

async function applySelectedTemplate() {{
  if (!selectedTemplateId) {{
    alert('Выберите шаблон!');
    return;
  }}

  try {{
    const r = await fetch(`/api/templates/${{selectedTemplateId}}/apply`, {{ method: 'POST' }});
    const d = await r.json();

    if (d.success) {{
      alert('Шаблон применён успешно!');
      selectedTemplateId = null;
      await loadTemplates();
    }} else {{
      alert('Ошибка: ' + (d.detail || 'Неизвестная ошибка'));
    }}
  }} catch(e) {{
    console.error('Apply template failed', e);
    alert('Ошибка применения шаблона');
  }}
}}

async function openTemplateEditor(templateId) {{
  const modal = document.getElementById('edit-template-modal');
  document.getElementById('edit-template-id').value = templateId;
  document.getElementById('edit-template-title').textContent = 'Редактор шаблона';

  try {{
    // Загружаем данные шаблона
    const r = await fetch('/api/templates/${{templateId}}');
    const t = await r.json();

    document.getElementById('edit-template-name').value = t.name || '';
    document.getElementById('edit-template-category').value = t.category || '';
    document.getElementById('edit-template-description').value = t.description || '';

    // Загружаем промпты из V2 таблицы
    await loadTemplatePrompts(templateId);
    // Загружаем настройки из V2 таблицы
    await loadTemplateSettings(templateId);

    modal.classList.add('open');
  }} catch(e) {{
    console.error('Open template editor failed', e);
    alert('Ошибка загрузки шаблона');
  }}
}}

// Загрузка промптов шаблона (V2)
async function loadTemplatePrompts(templateId) {{
  const container = document.getElementById('edit-template-prompts-container');
  try {{
    const r = await fetch(`/api/templates/${{templateId}}/prompts`);
    const d = await r.json();
    const prompts = d.prompts || [];

    if (prompts.length === 0) {{
      container.innerHTML = '<div style="color:var(--muted); font-size:12px;">Нет промптов. Добавьте первый!</div>';
      return;
    }}

    let html = '';
    prompts.forEach((p, idx) => {{
      html += createPromptFieldHTML(p.prompt_name, p.prompt_text, p.description, idx);
    }});
    container.innerHTML = html;
  }} catch(e) {{
    console.error('Load prompts failed', e);
    container.innerHTML = '<div style="color:var(--danger); font-size:12px;">Ошибка загрузки промптов</div>';
  }}
}}

// Загрузка настроек шаблона (V2)
async function loadTemplateSettings(templateId) {{
  const container = document.getElementById('edit-template-settings-container');
  try {{
    const r = await fetch(`/api/templates/${{templateId}}/settings`);
    const d = await r.json();
    const settings = d.settings || {{}};

    if (Object.keys(settings).length === 0) {{
      container.innerHTML = '<div style="color:var(--muted); font-size:12px;">Нет настроек. Добавьте первую!</div>';
      return;
    }}

    let html = '';
    Object.entries(settings).forEach(([key, value], idx) => {{
      html += createSettingFieldHTML(key, value, idx);
    }});
    container.innerHTML = html;
  }} catch(e) {{
    console.error('Load settings failed', e);
    container.innerHTML = '<div style="color:var(--danger); font-size:12px;">Ошибка загрузки настроек</div>';
  }}
}}

// Создание HTML для поля промпта
function createPromptFieldHTML(name, value, description = "", idx) {{
  const encodedName = encodeURIComponent(name);
  return `
    <div class="prompt-field" data-name="${{encodedName}}" style="display:flex; gap:8px; align-items:flex-start;">
      <div style="flex:1; display:flex; flex-direction:column; gap:4px;">
        <input type="text" class="prompt-name" value="${{name}}" placeholder="Имя промпта (stage_1_writer)" style="padding:6px; background:var(--bg); border:1px solid var(--border); border-radius:4px; color:var(--text); font-family:var(--font-mono); font-size:11px;">
        <textarea class="prompt-text" placeholder="Текст промпта..." style="width:100%; height:80px; padding:8px; background:#070710; border:1px solid var(--border); border-radius:4px; color:var(--text); font-family:var(--font-mono); font-size:11px; resize:vertical;">${{value}}</textarea>
      </div>
      <div style="display:flex; flex-direction:column; gap:4px;">
        <button onclick="removePromptField(this)" style="padding:4px 8px; font-size:10px; background:var(--danger); border:none; border-radius:4px; color:#fff; cursor:pointer;">🗑️</button>
      </div>
    </div>
  `;
}}

// Создание HTML для поля настройки
function createSettingFieldHTML(key, value, idx) {{
  const encodedKey = encodeURIComponent(key);
  return `
    <div class="setting-field" data-key="${{encodedKey}}" style="display:flex; gap:8px; align-items:center;">
      <input type="text" class="setting-key" value="${{key}}" placeholder="Ключ" style="width:120px; padding:6px; background:var(--bg); border:1px solid var(--border); border-radius:4px; color:var(--text); font-family:var(--font-mono); font-size:11px;">
      <input type="text" class="setting-value" value="${{value}}" placeholder="Значение" style="flex:1; padding:6px; background:var(--bg); border:1px solid var(--border); border-radius:4px; color:var(--text); font-family:var(--font-mono); font-size:11px;">
      <button onclick="removeSettingField(this)" style="padding:4px 8px; font-size:10px; background:var(--danger); border:none; border-radius:4px; color:#fff; cursor:pointer;">🗑️</button>
    </div>
  `;
}}

// Добавление нового поля промпта
function addPromptField() {{
  const container = document.getElementById('edit-template-prompts-container');
  const count = container.querySelectorAll('.prompt-field').length;
  container.innerHTML += createPromptFieldHTML('new_prompt_' + count, '', '', count);
}}

// Удаление поля промпта
function removePromptField(btn) {{
  btn.closest('.prompt-field').remove();
}}

// Добавление новой настройки
function addSettingField() {{
  const container = document.getElementById('edit-template-settings-container');
  const count = container.querySelectorAll('.setting-field').length;
  container.innerHTML += createSettingFieldHTML('new_setting_' + count, '', count);
}}

// Удаление настройки
function removeSettingField(btn) {{
  btn.closest('.setting-field').remove();
}}

async function saveTemplate() {{
  const templateId = document.getElementById('edit-template-id').value;
  const name = document.getElementById('edit-template-name').value;
  const category = document.getElementById('edit-template-category').value;
  const description = document.getElementById('edit-template-description').value;

  if (!name) {{
    alert('Введите название шаблона!');
    return;
  }}

  // Собираем промпты из V2 полей
  const prompts = [];
  const promptFields = document.querySelectorAll('.prompt-field');
  promptFields.forEach(field => {{
    const nameInput = field.querySelector('.prompt-name');
    const textInput = field.querySelector('.prompt-text');
    if (nameInput && textInput && nameInput.value && textInput.value) {{
      prompts.push({{
        prompt_name: nameInput.value,
        prompt_text: textInput.value,
        language: 'ru',
        description: ''
      }});
    }}
  }});

  // Собираем настройки из V2 полей
  const settings = Object.assign({{}});
  const settingFields = document.querySelectorAll('.setting-field');
  settingFields.forEach(field => {{
    const keyInput = field.querySelector('.setting-key');
    const valueInput = field.querySelector('.setting-value');
    if (keyInput && valueInput && keyInput.value && valueInput.value) {{
      settings[keyInput.value] = valueInput.value;
    }}
  }});

  try {{
    let response;
    if (!templateId) {{
      const id = name.toLowerCase().replace(/[^a-z0-9-]/g, '-') || 'new-template';

      response = await fetch('/api/templates', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
          id: id,
          name: name,
          category: category,
          description: description,
          prompts_json: '{{}}',
          settings_json: '{{}}',
          is_default: false
        }})
      }});

      const d = await response.json();
      if (!d.success) {{
        throw new Error(d.detail || 'Failed to create template');
      }}

      // Добавляем промпты и настройки
      for (const p of prompts) {{
        await fetch(`/api/templates/${{id}}/prompts`, {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify(p)
        }});
      }}

      for (const [key, value] of Object.entries(settings)) {{
        await fetch(`/api/templates/${{id}}/settings`, {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{ setting_key: key, setting_value: value }})
        }});
      }}

    }} else {{
      // Обновляем шаблон
      response = await fetch(`/api/templates/${{templateId}}`, {{
        method: 'PATCH',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
          name: name,
          category: category,
          description: description
        }})
      }});

      const d = await response.json();
      if (!d.success) {{
        throw new Error(d.detail || 'Failed to update template');
      }}

      // Обновляем промпты (удаляем все и добавляем новые)
      const currentPrompts = await fetch(`/api/templates/${{templateId}}/prompts`).then(r => r.json());
      for (const p of currentPrompts.prompts || []) {{
        await fetch(`/api/templates/${{templateId}}/prompts/${{p.prompt_name}}`, {{ method: 'DELETE' }});
      }}
      for (const p of prompts) {{
        await fetch(`/api/templates/${{templateId}}/prompts`, {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify(p)
        }});
      }}

      // Обновляем настройки
      const currentSettings = await fetch(`/api/templates/${{templateId}}/settings`).then(r => r.json());
      for (const key of Object.keys(currentSettings.settings || {{}})) {{
        await fetch(`/api/templates/${{templateId}}/settings/${{key}}`, {{ method: 'DELETE' }});
      }}
      for (const [key, value] of Object.entries(settings)) {{
        await fetch(`/api/templates/${{templateId}}/settings`, {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{ setting_key: key, setting_value: value }})
        }});
      }}
    }}

    alert('Шаблон ' + (!templateId ? 'создан' : 'сохранён') + '!');
    closeEditTemplateModal();
    await loadTemplates();
  }} catch(e) {{
    console.error('Save template failed', e);
    alert('Ошибка сохранения: ' + e.message);
  }}
}}

function closeEditTemplateModal() {{
  document.getElementById('edit-template-modal').classList.remove('open');
  document.getElementById('edit-template-id').value = '';
}}

async function deleteCurrentTemplate() {{
  const templateId = document.getElementById('edit-template-id').value;
  if (!templateId) {{
    alert('Нет шаблона для удаления');
    return;
  }}

  if (!confirm('Вы уверены? Это удалит шаблон навсегда!')) return;

  try {{
    const r = await fetch(`/api/templates/${{templateId}}`, {{ method: 'DELETE' }});
    const d = await r.json();

    if (d.success) {{
      alert('Шаблон удалён');
      closeEditTemplateModal();
      await loadTemplates();
    }} else {{
      alert('Ошибка: ' + (d.detail || 'Неизвестная ошибка'));
    }}
  }} catch(e) {{
    console.error('Delete template failed', e);
    alert('Ошибка удаления');
  }}
}}

async function duplicateTemplate(templateId) {{
  try {{
    const r = await fetch(`/api/templates/${{templateId}}/duplicate`, {{ method: 'POST' }});
    const d = await r.json();

    if (d.success) {{
      alert('Шаблон дублирован: ' + d.id);
      await loadTemplates();
    }} else {{
      alert('Ошибка: ' + (d.detail || 'Неизвестная ошибка'));
    }}
  }} catch(e) {{
    console.error('Duplicate template failed', e);
    alert('Ошибка дублирования');
  }}
}}

async function archiveTemplate(templateId, archived) {{
  try {{
    const r = await fetch(`/api/templates/${{templateId}}/archive`, {{ method: 'POST' }});
    const d = await r.json();

    if (d.success) {{
      alert(archived ? 'Шаблон архивирован' : 'Шаблон разархивирован');
      await loadTemplates();
    }} else {{
      alert('Ошибка: ' + (d.detail || 'Неизвестная ошибка'));
    }}
  }} catch(e) {{
    console.error('Archive template failed', e);
    alert('Ошибка архивации');
  }}
}}

async function deleteTemplate(templateId) {{
  if (!confirm('Вы уверены? Это удалит шаблон навсегда!')) return;

  try {{
    const r = await fetch(`/api/templates/${{templateId}}`, {{ method: 'DELETE' }});
    const d = await r.json();

    if (d.success) {{
      alert('Шаблон удалён');
      await loadTemplates();
    }} else {{
      alert('Ошибка: ' + (d.detail || 'Неизвестная ошибка'));
    }}
  }} catch(e) {{
    console.error('Delete template failed', e);
    alert('Ошибка удаления');
  }}
}}

// ── OPEN TEMPLATES LIST ──
async function openTemplatesList() {{
  const modal = document.getElementById('templates-modal');
  await loadAvailableTemplates();
  modal.classList.add('open');
}}

// ── OPEN CREATE TEMPLATE MODAL ──
function openCreateTemplateModal() {{
  document.getElementById('edit-template-id').value = '';
  document.getElementById('edit-template-title').textContent = 'Новый шаблон';
  document.getElementById('edit-template-name').value = '';
  document.getElementById('edit-template-category').value = '';
  document.getElementById('edit-template-description').value = '';
  document.getElementById('edit-template-stage-1-writer').value = '';
  document.getElementById('edit-template-stage-1-extractor').value = '';
  document.getElementById('edit-template-stage-2-scenes').value = '';
  document.getElementById('edit-template-visual-style').value = '';
  document.getElementById('edit-template-modal').classList.add('open');
}}

// ── COLAB URL VISIBILITY ──
function onColabChange() {{
  const w = document.getElementById('use_colab_whisper').checked;
  const r = document.getElementById('use_colab_render').checked;
  document.getElementById('colab_url_wrap').style.display = (w || r) ? 'block' : 'none';
}}

// ── AI SETTINGS TOGGLE ──
function toggleAiSettings() {{
  const section = document.getElementById('ai-settings-section');
  section.classList.toggle('expanded');
}}

// ── PROMPT EDITOR TOGGLE ──
function togglePromptEditor() {{
  const section = document.getElementById('prompt-editor-section');
  section.classList.toggle('expanded');
}}

// ── LOAD SAVED SETTINGS ──
window.onload = async () => {{
  buildPipeline();
  loadTemplates(); // Загрузить шаблоны
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

    // AI Settings
    const ai = d.ai_settings?.text || {{}};
    document.getElementById('ai_api_url').value          = ai.api_url || '';
    document.getElementById('ai_api_key').value          = ai.api_key || '';
    document.getElementById('ai_folder_id').value        = ai.folder_id || '';
    document.getElementById('ai_model').value            = ai.model || 'gemma-3-27b-it/latest';
    
    // Auto continue
    document.getElementById('auto_continue').checked     = d.auto_continue !== undefined ? d.auto_continue : true;

    // Prompts
    const prompts = d.prompts || {{}};
    document.getElementById('prompt_writer').value       = prompts.stage_1_writer || '';
    document.getElementById('prompt_stage_2').value      = prompts.stage_2_scenes || '';

    onColabChange();
  }} catch(e) {{ console.warn('Settings load failed', e); }}
}};

// ── SAVE AI SETTINGS ──
async function saveAiSettings() {{
  const aiSettings = {{
    text: {{
      api_url:   document.getElementById('ai_api_url').value,
      api_key:   document.getElementById('ai_api_key').value,
      folder_id: document.getElementById('ai_folder_id').value,
      model:     document.getElementById('ai_model').value
    }}
  }};
  try {{
    const r = await fetch('/save-ai-settings', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(aiSettings)
    }});
    const d = await r.json();
    alert(d.message || 'Настройки AI сохранены');
  }} catch(e) {{
    console.error('Save AI settings failed', e);
    alert('Ошибка сохранения настроек AI');
  }}
}}

// ── EPISODES MODAL ──
const EPISODE_NAMES = {{
  episode_1: '📝 Эпизод 1 — Завязка',
  episode_2: '⚡ Эпизод 2 — Кульминация',
  episode_3: '🎬 Эпизод 3 — Финал'
}};

let currentEpisodesData = null; // Глобальная переменная для кэша данных модалки

async function openEpisodesModal() {{
  const modal = document.getElementById('episodes-modal');
  modal.classList.add('open');
  await refreshEpisodesModal();
}}

async function refreshEpisodesModal() {{
  const body = document.getElementById('episodes-modal-body');
  body.innerHTML = '<div class="modal-empty">Загрузка...</div>';
  try {{
    const r = await fetch('/episodes');
    currentEpisodesData = await r.json();
    switchTab('master'); // По умолчанию открываем первую вкладку
  }} catch(e) {{
    body.innerHTML = '<div class="modal-empty">❌ Ошибка загрузки.</div>';
  }}
}}

function switchTab(tabName) {{
  // Активная кнопка
  document.querySelectorAll('.tab-btn').forEach(btn => {{
    btn.classList.toggle('active', btn.getAttribute('onclick').includes(tabName));
  }});

  const body = document.getElementById('episodes-modal-body');
  if (!currentEpisodesData || currentEpisodesData.error) {{
    body.innerHTML = `<div class="modal-empty">${{currentEpisodesData?.error || 'Нет данных'}}</div>`;
    return;
  }}

  let html = "";
  const d = currentEpisodesData;

  if (tabName === 'master') {{
    html = `<div class="episode-text">${{d.master_story || 'Пусто'}}</div>`;
  }} 
  else if (tabName === 'raw' || tabName === 'final') {{
    const dataObj = tabName === 'raw' ? d.episodes_raw : d.episodes_final;
    if (!dataObj) {{ html = '<div class="modal-empty">Данные не сгенерированы</div>'; }}
    else {{
      html = Object.entries(dataObj).map(([key, text]) => `
        <div class="episode-block">
          <div class="episode-label">${{EPISODE_NAMES[key] || key}}</div>
          <div class="episode-text">${{text.replace(/</g, '&lt;').replace(/>/g, '&gt;')}}</div>
        </div>
      `).join('');
    }}
  }} 
  else if (tabName === 'stage2') {{
    if (!d.stage_2) {{ html = '<div class="modal-empty">Запустите Этап 2</div>'; }}
    else {{
      html = Object.entries(d.stage_2).map(([key, text]) => `
        <div class="episode-block">
          <div class="episode-label" style="color: var(--accent2);">${{EPISODE_NAMES[key] || key}}</div>
          <div class="episode-text" style="font-family: var(--font-mono); font-size: 12px; color: #cbd5e1;">${{text}}</div>
        </div>
      `).join('');
    }}
  }}

  body.innerHTML = html;
}}

function closeEpisodesModal(e) {{
  if (e.target === document.getElementById('episodes-modal')) {{
    document.getElementById('episodes-modal').classList.remove('open');
  }}
}}



async function savePrompt() {{
  const promptText = document.getElementById('prompt_writer').value;
  try {{
    const r = await fetch('/save-prompt', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ stage_1_writer: promptText }})
    }});
    const d = await r.json();
    alert(d.message || 'Промпт сохранён');
  }} catch(e) {{
    console.error('Save prompt failed', e);
    alert('Ошибка сохранения');
  }}
}}

// ── PROMPT STAGE 2 TOGGLE ──
function togglePromptStage2Editor() {{
  const section = document.getElementById('prompt-stage-2-section');
  section.classList.toggle('expanded');
}}

// ── SAVE PROMPT STAGE 2 ──
async function savePromptStage2() {{
  const promptText = document.getElementById('prompt_stage_2').value;
  try {{
    const r = await fetch('/save-prompt-stage2', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ stage_2_scenes: promptText }})
    }});
    const d = await r.json();
    alert(d.message || 'Промпт Stage 2 сохранён');
  }} catch(e) {{
    console.error('Save prompt stage2 failed', e);
    alert('Ошибка сохранения');
  }}
}}

// ── START ──
async function startFrom(stageNum) {{
  // Собираем AI settings
  const aiSettings = {{
    text: {{
      api_url:    document.getElementById('ai_api_url').value,
      api_key:    document.getElementById('ai_api_key').value,
      folder_id:  document.getElementById('ai_folder_id').value,
      model:      document.getElementById('ai_model').value
    }}
  }};

  const body = {{
    stage:             stageNum,
    idea:              document.getElementById('idea-input').value,
    num_episodes:      parseInt(document.getElementById('num_episodes').value) || 3,
    aspect_ratio:      document.getElementById('aspect_ratio').value,
    quality:           document.getElementById('quality').value,
    codec:             document.getElementById('codec').value,
    test_mode:         document.getElementById('test_mode').checked,
    use_colab_whisper: document.getElementById('use_colab_whisper').checked,
    use_colab_render:  document.getElementById('use_colab_render').checked,
    colab_url:         document.getElementById('colab_url').value,
    auto_continue:     document.getElementById('auto_continue').checked,
    ai_settings:       aiSettings,
    prompts:           {{
        stage_1_writer: document.getElementById('prompt_writer').value,
        stage_2_scenes: document.getElementById('prompt_stage_2').value
    }}
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


# ── TEMPLATE API ──

class CreateTemplateRequest(BaseModel):
    id: str
    name: str
    description: str = ""
    category: str = ""
    prompts_json: str = "{}"
    settings_json: str = "{}"
    is_default: bool = False


class UpdateTemplateRequest(BaseModel):
    name: str = None
    description: str = None
    category: str = None
    prompts_json: str = None
    settings_json: str = None
    archived: bool = None


class AddPromptRequest(BaseModel):
    prompt_name: str
    prompt_text: str
    language: str = "ru"
    description: str = ""


class UpdatePromptRequest(BaseModel):
    prompt_text: str = None
    language: str = None
    description: str = None


class AddSettingRequest(BaseModel):
    setting_key: str
    setting_value: str


@app.get("/api/templates")
async def api_get_templates():
    try:
        templates = get_all_templates()
        return {"templates": templates}
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


@app.post("/api/templates")
async def api_create_template(req: CreateTemplateRequest):
    try:
        success = create_template(
            template_id=req.id,
            name=req.name,
            description=req.description,
            category=req.category,
            prompts_json=req.prompts_json,
            settings_json=req.settings_json,
            is_default=req.is_default
        )
        if not success:
            raise HTTPException(status_code=400, detail="Template already exists")
        return {"success": True, "id": req.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/templates/{template_id}")
async def api_update_template(template_id: str, req: UpdateTemplateRequest):
    try:
        template = get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        success = update_template(
            template_id=template_id,
            name=req.name,
            description=req.description,
            category=req.category,
            prompts_json=req.prompts_json,
            settings_json=req.settings_json,
            archived=req.archived
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
        return {"success": True, "id": template_id}
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
        return {"success": True, "id": new_id}
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

        # Получаем текущее состояние
        current_archived = template.get("archived", 0)
        success = archive_template(template_id, not current_archived)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to archive template")
        return {"success": True, "id": template_id, "archived": not current_archived}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates/{template_id}/apply")
async def api_apply_template(template_id: str):
    """
    Применить шаблон - сохранить ID в settings.json и обновить UI.
    """
    try:
        template = get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Читаем текущий settings
        if os.path.exists("settings.json"):
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
        else:
            settings = {}

        # Обновляем ID шаблона
        settings["active_template_id"] = template_id

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


@app.get("/api/templates/{template_id}/prompts")
async def api_get_template_prompts(template_id: str):
    """Получить все промпты шаблона (V2 структура)."""
    try:
        from .template_manager import get_template_prompts
        prompts = get_template_prompts(template_id)
        return {"prompts": prompts}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates/{template_id}/prompts")
async def api_add_template_prompt(template_id: str, req: AddPromptRequest):
    """Добавить промпт к шаблону (V2 структура)."""
    try:
        from .template_manager import get_template
        template = get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        success = add_template_prompt(
            template_id=template_id,
            prompt_name=req.prompt_name,
            prompt_text=req.prompt_text,
            language=req.language,
            description=req.description
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add prompt")
        return {"success": True, "prompt_name": req.prompt_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/templates/{template_id}/prompts/{prompt_name}")
async def api_update_template_prompt(template_id: str, prompt_name: str, req: UpdatePromptRequest):
    """Обновить промпт шаблона (V2 структура)."""
    try:
        from .template_manager import get_template_prompt
        success = update_template_prompt(
            template_id=template_id,
            prompt_name=prompt_name,
            prompt_text=req.prompt_text,
            language=req.language,
            description=req.description
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update prompt")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/templates/{template_id}/prompts/{prompt_name}")
async def api_delete_template_prompt(template_id: str, prompt_name: str):
    """Удалить промпт из шаблона (V2 структура)."""
    try:
        from .template_manager import delete_template_prompt
        success = delete_template_prompt(template_id=template_id, prompt_name=prompt_name)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete prompt")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/templates/{template_id}/settings")
async def api_get_template_settings(template_id: str):
    """Получить все настройки шаблона (V2 структура)."""
    try:
        from .template_manager import get_template_settings
        settings = get_template_settings(template_id)
        return {"settings": settings}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates/{template_id}/settings")
async def api_add_template_setting(template_id: str, req: AddSettingRequest):
    """Добавить настройку к шаблону (V2 структура)."""
    try:
        from .template_manager import get_template
        template = get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        success = add_template_setting(
            template_id=template_id,
            setting_key=req.setting_key,
            setting_value=req.setting_value
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add setting")
        return {"success": True, "setting_key": req.setting_key}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/templates/{template_id}/settings/{setting_key}")
async def api_update_template_setting(template_id: str, setting_key: str, req: dict):
    """Обновить настройку шаблона (V2 структура)."""
    try:
        from .template_manager import update_template_setting
        setting_value = req.get("setting_value")
        if setting_value is None:
            raise HTTPException(status_code=400, detail="setting_value is required")

        success = update_template_setting(
            template_id=template_id,
            setting_key=setting_key,
            setting_value=setting_value
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update setting")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/templates/{template_id}/settings/{setting_key}")
async def api_delete_template_setting(template_id: str, setting_key: str):
    """Удалить настройку из шаблона (V2 структура)."""
    try:
        from .template_manager import delete_template_setting
        success = delete_template_setting(template_id=template_id, setting_key=setting_key)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete setting")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status():
    return {"stage": manager.current_stage_idx, "logs": manager.logs}


if __name__ == "__main__":
    # Если запуск через uvicorn как модуль, запускаем напрямую
    # Если запуск через run.py, запускаем с cloudflared
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
            "uvicorn", "main:app",
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
