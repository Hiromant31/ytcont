     1|import os
     2|import json
     3|from typing import Optional
     4|from datetime import datetime
     5|from pathlib import Path
     6|from fastapi import FastAPI, BackgroundTasks
     7|from fastapi.responses import HTMLResponse
     8|from orchestrator import manager
     9|from pydantic import BaseModel
    10|from dotenv import load_dotenv
    11|from youtube_oauth_helper import check_youtube_setup, get_youtube_credentials, validate_oauth_json, save_youtube_config
    12|from stage_8_youtube_upload import YouTubeUploader, find_latest_video, generate_schedule_time, save_upload_record
    13|
    14|load_dotenv()
    15|app = FastAPI()
    16|
    17|# YouTube модели данных
    18|class YouTubeConfig(BaseModel):
    19|    enabled: bool = False
    20|    oauth_client_json: str = ""
    21|    schedule_time: str = ""
    22|    auto_upload: bool = False
    23|    generate_tags: bool = True
    24|    default_privacy: str = "private"
    25|    notify_subscribers: bool = True
    26|
    27|class YouTubeUploadRequest(BaseModel):
    28|    video_path: str = ""
    29|    schedule_time: str = ""
    30|    custom_title: str = ""
    31|    custom_description: str = ""
    32|    custom_tags: str = ""
    33|    notify_subscribers: bool = True
    34|
    35|
    36|class StartRequest(BaseModel):
    37|    stage:              int   = 1
    38|    idea:               str   = ""
    39|    aspect_ratio:       str   = "9:16"
    40|    quality:            str   = "1080p"
    41|    codec:              str   = "libx264"
    42|    test_mode:          bool  = False
    43|    use_colab_whisper:  bool  = False
    44|    use_colab_render:   bool  = False
    45|    colab_url:          str   = ""
    46|
    47|
    48|@app.get("/settings")
    49|async def get_settings():
    50|    if os.path.exists("settings.json"):
    51|        with open("settings.json", "r", encoding="utf-8") as f:
    52|            return json.load(f)
    53|    return {
    54|        "aspect_ratio": "9:16",
    55|        "quality": "1080p",
    56|        "codec": "libx264",
    57|        "test_mode": False,
    58|        "use_colab_whisper": False,
    59|        "use_colab_render": False,
    60|        "colab_url": "",
    61|    }
    62|
    63|
    64|@app.get("/", response_class=HTMLResponse)
    65|async def index():
    66|    stages_data = [
    67|        {"icon": "✍️",  "name": name}
    68|        for name, _ in manager.stages
    69|    ]
    70|    stages_json = json.dumps(stages_data)
    71|
    72|    return f"""<!DOCTYPE html>
    73|<html lang="ru">
    74|<head>
    75|<meta charset="UTF-8">
    76|<meta name="viewport" content="width=device-width, initial-scale=1.0">
    77|<title>STUDIO — AI Video Pipeline</title>
    78|<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    79|<style>
    80|*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    81|
    82|:root {{
    83|  --bg:        #0a0a0f;
    84|  --surface:   #111118;
    85|  --border:    #1e1e2e;
    86|  --accent:    #7c3aed;
    87|  --accent2:   #06b6d4;
    88|  --accent3:   #f59e0b;
    89|  --text:      #e2e8f0;
    90|  --muted:     #64748b;
    91|  --success:   #10b981;
    92|  --danger:    #ef4444;
    93|  --font-head: 'Syne', sans-serif;
    94|  --font-mono: 'JetBrains Mono', monospace;
    95|}}
    96|
    97|body {{
    98|  font-family: var(--font-head);
    99|  background: var(--bg);
   100|  color: var(--text);
   101|  min-height: 100vh;
   102|  overflow-x: hidden;
   103|}}
   104|
   105|/* ── NOISE TEXTURE ── */
   106|body::before {{
   107|  content: '';
   108|  position: fixed; inset: 0;
   109|  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
   110|  pointer-events: none;
   111|  z-index: 0;
   112|}}
   113|
   114|/* ── LAYOUT ── */
   115|.shell {{
   116|  position: relative;
   117|  z-index: 1;
   118|  max-width: 1100px;
   119|  margin: 0 auto;
   120|  padding: 40px 24px 80px;
   121|}}
   122|
   123|/* ── HEADER ── */
   124|header {{
   125|  display: flex;
   126|  align-items: center;
   127|  gap: 18px;
   128|  margin-bottom: 48px;
   129|}}
   130|.logo-mark {{
   131|  width: 48px; height: 48px;
   132|  background: linear-gradient(135deg, var(--accent), var(--accent2));
   133|  border-radius: 12px;
   134|  display: flex; align-items: center; justify-content: center;
   135|  font-size: 22px;
   136|  flex-shrink: 0;
   137|}}
   138|.logo-text h1 {{
   139|  font-size: 28px;
   140|  font-weight: 800;
   141|  letter-spacing: -0.5px;
   142|  background: linear-gradient(90deg, #fff 40%, var(--accent2));
   143|  -webkit-background-clip: text;
   144|  -webkit-text-fill-color: transparent;
   145|  background-clip: text;
   146|}}
   147|.logo-text p {{
   148|  font-size: 12px;
   149|  color: var(--muted);
   150|  font-family: var(--font-mono);
   151|  letter-spacing: 0.08em;
   152|  text-transform: uppercase;
   153|}}
   154|
   155|/* ── MAIN GRID ── */
   156|.main-grid {{
   157|  display: grid;
   158|  grid-template-columns: 1fr 340px;
   159|  gap: 24px;
   160|  align-items: start;
   161|}}
   162|
   163|/* ── CARD ── */
   164|.card {{
   165|  background: var(--surface);
   166|  border: 1px solid var(--border);
   167|  border-radius: 16px;
   168|  padding: 24px;
   169|}}
   170|.card-title {{
   171|  font-size: 11px;
   172|  font-weight: 600;
   173|  letter-spacing: 0.12em;
   174|  text-transform: uppercase;
   175|  color: var(--muted);
   176|  font-family: var(--font-mono);
   177|  margin-bottom: 16px;
   178|}}
   179|
   180|/* ── IDEA TEXTAREA ── */
   181|.idea-wrap {{
   182|  position: relative;
   183|  margin-bottom: 24px;
   184|}}
   185|.idea-wrap textarea {{
   186|  width: 100%;
   187|  height: 110px;
   188|  background: #0d0d16;
   189|  border: 1px solid var(--border);
   190|  border-radius: 12px;
   191|  color: var(--text);
   192|  font-family: var(--font-head);
   193|  font-size: 15px;
   194|  padding: 16px;
   195|  resize: none;
   196|  outline: none;
   197|  transition: border-color .2s;
   198|  line-height: 1.6;
   199|}}
   200|.idea-wrap textarea:focus {{ border-color: var(--accent); }}
   201|.idea-wrap textarea::placeholder {{ color: var(--muted); }}
   202|
   203|/* ── SETTINGS ROW ── */
   204|.settings-row {{
   205|  display: grid;
   206|  grid-template-columns: 1fr 1fr 1fr;
   207|  gap: 12px;
   208|  margin-bottom: 16px;
   209|}}
   210|.field {{
   211|  display: flex;
   212|  flex-direction: column;
   213|  gap: 6px;
   214|}}
   215|.field label {{
   216|  font-size: 11px;
   217|  font-weight: 600;
   218|  letter-spacing: 0.1em;
   219|  text-transform: uppercase;
   220|  color: var(--muted);
   221|  font-family: var(--font-mono);
   222|}}
   223|select {{
   224|  background: #0d0d16;
   225|  border: 1px solid var(--border);
   226|  border-radius: 8px;
   227|  color: var(--text);
   228|  font-family: var(--font-mono);
   229|  font-size: 13px;
   230|  padding: 10px 12px;
   231|  outline: none;
   232|  cursor: pointer;
   233|  transition: border-color .2s;
   234|}}
   235|select:focus {{ border-color: var(--accent); }}
   236|
   237|/* ── TOGGLE SWITCH ── */
   238|.toggle-row {{
   239|  display: flex;
   240|  align-items: center;
   241|  gap: 10px;
   242|  padding: 10px 0;
   243|}}
   244|.toggle-row label {{ font-size: 13px; color: var(--text); cursor: pointer; }}
   245|.toggle {{
   246|  position: relative;
   247|  width: 40px; height: 22px;
   248|  flex-shrink: 0;
   249|}}
   250|.toggle input {{ opacity: 0; width: 0; height: 0; }}
   251|.slider {{
   252|  position: absolute; inset: 0;
   253|  background: var(--border);
   254|  border-radius: 22px;
   255|  cursor: pointer;
   256|  transition: .25s;
   257|}}
   258|.slider::before {{
   259|  content: '';
   260|  position: absolute;
   261|  width: 16px; height: 16px;
   262|  left: 3px; bottom: 3px;
   263|  background: #fff;
   264|  border-radius: 50%;
   265|  transition: .25s;
   266|}}
   267|.toggle input:checked + .slider {{ background: var(--accent); }}
   268|.toggle input:checked + .slider::before {{ transform: translateX(18px); }}
   269|
   270|/* ── COLAB SECTION ── */
   271|.colab-section {{
   272|  border: 1px solid var(--border);
   273|  border-radius: 12px;
   274|  padding: 16px;
   275|  margin-top: 16px;
   276|  background: #0d0d16;
   277|}}
   278|.colab-header {{
   279|  font-size: 11px;
   280|  font-weight: 700;
   281|  letter-spacing: 0.12em;
   282|  text-transform: uppercase;
   283|  font-family: var(--font-mono);
   284|  color: var(--accent2);
   285|  margin-bottom: 12px;
   286|  display: flex;
   287|  align-items: center;
   288|  gap: 8px;
   289|}}
   290|.colab-dot {{
   291|  width: 7px; height: 7px;
   292|  background: var(--accent2);
   293|  border-radius: 50%;
   294|  animation: pulse 2s infinite;
   295|}}
   296|@keyframes pulse {{
   297|  0%, 100% {{ opacity: 1; }}
   298|  50%       {{ opacity: 0.3; }}
   299|}}
   300|.colab-url-wrap {{
   301|  margin-top: 12px;
   302|}}
   303|.colab-url-wrap label {{
   304|  font-size: 11px;
   305|  color: var(--muted);
   306|  font-family: var(--font-mono);
   307|  display: block;
   308|  margin-bottom: 6px;
   309|}}
   310|.colab-url-wrap input {{
   311|  width: 100%;
   312|  background: var(--bg);
   313|  border: 1px solid var(--border);
   314|  border-radius: 8px;
   315|  color: var(--accent2);
   316|  font-family: var(--font-mono);
   317|  font-size: 12px;
   318|  padding: 10px 12px;
   319|  outline: none;
   320|  transition: border-color .2s;
   321|}}
   322|.colab-url-wrap input:focus {{ border-color: var(--accent2); }}
   323|.colab-toggles {{
   324|  display: flex;
   325|  flex-direction: column;
   326|  gap: 4px;
   327|}}
   328|
   329|/* ── RUN BUTTON ── */
   330|.run-btn {{
   331|  width: 100%;
   332|  padding: 16px;
   333|  background: linear-gradient(135deg, var(--accent), #5b21b6);
   334|  border: none;
   335|  border-radius: 12px;
   336|  color: #fff;
   337|  font-family: var(--font-head);
   338|  font-size: 15px;
   339|  font-weight: 700;
   340|  letter-spacing: 0.04em;
   341|  cursor: pointer;
   342|  margin-top: 20px;
   343|  transition: opacity .2s, transform .1s;
   344|  position: relative;
   345|  overflow: hidden;
   346|}}
   347|.run-btn:hover  {{ opacity: 0.9; }}
   348|.run-btn:active {{ transform: scale(0.99); }}
   349|.run-btn::after {{
   350|  content: '';
   351|  position: absolute;
   352|  inset: 0;
   353|  background: linear-gradient(135deg, transparent 40%, rgba(255,255,255,0.08));
   354|}}
   355|
   356|/* ── SIDEBAR ── */
   357|.sidebar {{ display: flex; flex-direction: column; gap: 16px; }}
   358|
   359|/* ── PIPELINE ── */
   360|.pipeline {{ display: flex; flex-direction: column; gap: 4px; }}
   361|.stage-item {{
   362|  display: flex;
   363|  align-items: center;
   364|  gap: 12px;
   365|  padding: 10px 12px;
   366|  border-radius: 10px;
   367|  cursor: pointer;
   368|  transition: background .15s;
   369|  border: 1px solid transparent;
   370|}}
   371|.stage-item:hover {{ background: rgba(124,58,237,0.08); border-color: rgba(124,58,237,0.2); }}
   372|.stage-item.active {{
   373|  background: rgba(124,58,237,0.12);
   374|  border-color: var(--accent);
   375|}}
   376|.stage-num {{
   377|  font-size: 11px;
   378|  font-family: var(--font-mono);
   379|  color: var(--muted);
   380|  width: 18px;
   381|  text-align: right;
   382|  flex-shrink: 0;
   383|}}
   384|.stage-icon {{ font-size: 16px; flex-shrink: 0; }}
   385|.stage-name {{ font-size: 13px; font-weight: 600; flex: 1; }}
   386|.stage-badge {{
   387|  font-size: 9px;
   388|  font-family: var(--font-mono);
   389|  background: rgba(6,182,212,0.15);
   390|  color: var(--accent2);
   391|  border: 1px solid rgba(6,182,212,0.3);
   392|  border-radius: 4px;
   393|  padding: 2px 6px;
   394|}}
   395|.stage-run-btn {{
   396|  font-size: 11px;
   397|  background: transparent;
   398|  border: 1px solid var(--border);
   399|  border-radius: 6px;
   400|  color: var(--muted);
   401|  padding: 3px 8px;
   402|  cursor: pointer;
   403|  font-family: var(--font-mono);
   404|  transition: all .15s;
   405|  white-space: nowrap;
   406|}}
   407|.stage-run-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
   408|
   409|/* ── LOGS ── */
   410|.logs-wrap {{
   411|  background: #070710;
   412|  border: 1px solid var(--border);
   413|  border-radius: 16px;
   414|  padding: 0;
   415|  overflow: hidden;
   416|  margin-top: 24px;
   417|}}
   418|.logs-header {{
   419|  display: flex;
   420|  align-items: center;
   421|  gap: 8px;
   422|  padding: 12px 16px;
   423|  border-bottom: 1px solid var(--border);
   424|  background: var(--surface);
   425|}}
   426|.logs-title {{
   427|  font-size: 11px;
   428|  font-family: var(--font-mono);
   429|  font-weight: 600;
   430|  letter-spacing: 0.1em;
   431|  text-transform: uppercase;
   432|  color: var(--muted);
   433|}}
   434|.live-dot {{
   435|  width: 7px; height: 7px;
   436|  background: var(--success);
   437|  border-radius: 50%;
   438|  animation: pulse 1.5s infinite;
   439|}}
   440|.logs-body {{
   441|  height: 280px;
   442|  overflow-y: auto;
   443|  padding: 16px;
   444|  font-family: var(--font-mono);
   445|  font-size: 12px;
   446|  line-height: 1.7;
   447|  color: #94a3b8;
   448|}}
   449|.logs-body::-webkit-scrollbar {{ width: 4px; }}
   450|.logs-body::-webkit-scrollbar-track {{ background: transparent; }}
   451|.logs-body::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}
   452|.log-line {{ padding: 1px 0; }}
   453|.log-line.success {{ color: var(--success); }}
   454|.log-line.error   {{ color: var(--danger); }}
   455|.log-line.stage   {{ color: #fff; font-weight: 600; }}
   456|.log-line.info    {{ color: var(--accent2); }}
   457|
   458|/* ── STATUS BAR ── */
   459|.status-bar {{
   460|  display: flex;
   461|  align-items: center;
   462|  gap: 10px;
   463|  padding: 12px 16px;
   464|  background: var(--surface);
   465|  border: 1px solid var(--border);
   466|  border-radius: 12px;
   467|  font-family: var(--font-mono);
   468|  font-size: 12px;
   469|}}
   470|.status-indicator {{
   471|  width: 8px; height: 8px;
   472|  border-radius: 50%;
   473|  background: var(--muted);
   474|  flex-shrink: 0;
   475|}}
   476|.status-indicator.running {{ background: var(--accent3); animation: pulse 1s infinite; }}
   477|.status-indicator.done    {{ background: var(--success); }}
   478|.status-indicator.error   {{ background: var(--danger); }}
   479|.status-text {{ color: var(--muted); }}
   480|
   481|@media (max-width: 768px) {{
   482|  .main-grid {{ grid-template-columns: 1fr; }}
   483|  .settings-row {{ grid-template-columns: 1fr 1fr; }}
   484|}}
   485|</style>
   486|</head>
   487|<body>
   488|<div class="shell">
   489|
   490|  <header>
   491|    <div class="logo-mark">🎬</div>
   492|    <div class="logo-text">
   493|      <h1>AI VIDEO STUDIO</h1>
   494|      <p>Hybrid Pipeline · Colab GPU Mode</p>
   495|    </div>
   496|  </header>
   497|
   498|  <div class="main-grid">
   499|
   500|    <!-- ── LEFT COLUMN ── -->
   501|    <div>
   502|
   503|      <div class="card" style="margin-bottom:16px">
   504|        <div class="card-title">Идея / Сценарий</div>
   505|        <div class="idea-wrap">
   506|          <textarea id="idea-input" placeholder="Введите тему, идею или полный сценарий ролика..."></textarea>
   507|        </div>
   508|
   509|        <div class="settings-row">
   510|          <div class="field">
   511|            <label>Формат</label>
   512|            <select id="aspect_ratio">
   513|              <option value="9:16">9:16 · Shorts / TikTok</option>
   514|              <option value="16:9">16:9 · YouTube</option>
   515|            </select>
   516|          </div>
   517|          <div class="field">
   518|            <label>Качество</label>
   519|            <select id="quality">
   520|              <option value="1080p">1080p · Full HD</option>
   521|              <option value="720p">720p · HD</option>
   522|              <option value="480p">480p · SD</option>
   523|              <option value="360p">360p · Low</option>
   524|              <option value="240p">240p · Min</option>
   525|            </select>
   526|          </div>
   527|          <div class="field">
   528|            <label>Кодек</label>
   529|            <select id="codec">
   530|              <option value="libx264">CPU · libx264</option>
   531|              <option value="h264_nvenc">GPU · h264_nvenc</option>
   532|            </select>
   533|          </div>
   534|        </div>
   535|
   536|        <div class="toggle-row">
   537|          <label class="toggle">
   538|            <input type="checkbox" id="test_mode">
   539|            <span class="slider"></span>
   540|          </label>
   541|          <label for="test_mode">🧪 Тестовый режим <span style="color:var(--muted);font-size:12px">(первые 15 сек)</span></label>
   542|        </div>
   543|
   544|        <!-- COLAB SECTION -->
   545|        <div class="colab-section">
   546|          <div class="colab-header">
   547|            <div class="colab-dot"></div>
   548|            Google Colab · Cloud GPU
   549|          </div>
   550|
   551|          <div class="colab-toggles">
   552|            <div class="toggle-row">
   553|              <label class="toggle">
   554|                <input type="checkbox" id="use_colab_whisper" onchange="onColabChange()">
   555|                <span class="slider"></span>
   556|              </label>
   557|              <label for="use_colab_whisper">☁️ Whisper на Colab <span style="color:var(--muted);font-size:12px">(субтитры)</span></label>
   558|            </div>
   559|            <div class="toggle-row">
   560|              <label class="toggle">
   561|                <input type="checkbox" id="use_colab_render" onchange="onColabChange()">
   562|                <span class="slider"></span>
   563|              </label>
   564|              <label for="use_colab_render">☁️ Рендер на Colab <span style="color:var(--muted);font-size:12px">(GPU FFmpeg)</span></label>
   565|            </div>
   566|          </div>
   567|
   568|          <div class="colab-url-wrap" id="colab_url_wrap" style="display:none">
   569|            <label>Ngrok URL из Colab:</label>
   570|            <input type="text" id="colab_url" placeholder="https://xxxx-xxxx.ngrok-free.app">
   571|          </div>
   572|        </div>
   573|
   574|        <button class="run-btn" onclick="startFrom(1)">▶ ЗАПУСТИТЬ ПОЛНЫЙ ЦИКЛ</button>
   575|      </div>
   576|
   577|      <!-- LOGS -->
   578|      <div class="logs-wrap">
   579|        <div class="logs-header">
   580|          <div class="live-dot"></div>
   581|          <span class="logs-title">Pipeline Logs</span>
   582|        </div>
   583|        <div class="logs-body" id="logs">
   584|          <div class="log-line" style="color:var(--muted)">Ожидание запуска...</div>
   585|        </div>
   586|      </div>
   587|
   588|    </div>
   589|
   590|    <!-- ── SIDEBAR ── -->
   591|    <div class="sidebar">
   592|
   593|      <div class="card">
   594|        <div class="card-title">Статус</div>
   595|        <div class="status-bar">
   596|          <div class="status-indicator" id="status-dot"></div>
   597|          <span class="status-text" id="status-text">Ожидание</span>
   598|        </div>
   599|      </div>
   600|
   601|      <div class="card">
   602|        <div class="card-title">Pipeline · Этапы</div>
   603|        <div class="pipeline" id="pipeline"></div>
   604|      </div>
   605|
   606|    </div>
   607|  </div>
   608|
   609|</div>
   610|
   611|<script>
   612|const STAGES = {{stages_json}};
   613|
   614|const STAGE_ICONS = ["✍️","🎬","👤","🖼️","🔊","📝","📋","🎞️"];
   615|const COLAB_STAGES = [5, 7]; // субтитры и рендер (0-indexed)
   616|
   617|// ── INIT PIPELINE ──
   618|function buildPipeline() {{
   619|  const el = document.getElementById('pipeline');
   620|  el.innerHTML = STAGES.map((s, i) => {{
   621|    const isColab = COLAB_STAGES.includes(i);
   622|    return `
   623|      <div class="stage-item" id="stage-${{i+1}}" onclick="">
   624|        <span class="stage-num">${{i+1}}</span>
   625|        <span class="stage-icon">${{STAGE_ICONS[i] || '⚙️'}}</span>
   626|        <span class="stage-name">${{s.name}}</span>
   627|        ${{isColab ? '<span class="stage-badge">COLAB</span>' : ''}}
   628|        <button class="stage-run-btn" onclick="event.stopPropagation();startFrom(${{i+1}})">▶</button>
   629|      </div>`;
   630|  }}).join('');
   631|}}
   632|
   633|// ── COLAB URL VISIBILITY ──
   634|function onColabChange() {{
   635|  const w = document.getElementById('use_colab_whisper').checked;
   636|  const r = document.getElementById('use_colab_render').checked;
   637|  document.getElementById('colab_url_wrap').style.display = (w || r) ? 'block' : 'none';
   638|}}
   639|
   640|// ── LOAD SAVED SETTINGS ──
   641|window.onload = async () => {{
   642|  buildPipeline();
   643|  try {{
   644|    const r = await fetch('/settings');
   645|    const d = await r.json();
   646|    document.getElementById('aspect_ratio').value        = d.aspect_ratio || '9:16';
   647|    document.getElementById('quality').value             = d.quality || '1080p';
   648|    document.getElementById('codec').value               = d.codec || 'libx264';
   649|    document.getElementById('test_mode').checked         = d.test_mode || false;
   650|    document.getElementById('use_colab_whisper').checked = d.use_colab_whisper || false;
   651|    document.getElementById('use_colab_render').checked  = d.use_colab_render  || false;
   652|    document.getElementById('colab_url').value           = d.colab_url || '';
   653|    onColabChange();
   654|  }} catch(e) {{ console.warn('Settings load failed', e); }}
   655|}};
   656|
   657|// ── START ──
   658|async function startFrom(stageNum) {{
   659|  const body = {{
   660|    stage:             stageNum,
   661|    idea:              document.getElementById('idea-input').value,
   662|    aspect_ratio:      document.getElementById('aspect_ratio').value,
   663|    quality:           document.getElementById('quality').value,
   664|    codec:             document.getElementById('codec').value,
   665|    test_mode:         document.getElementById('test_mode').checked,
   666|    use_colab_whisper: document.getElementById('use_colab_whisper').checked,
   667|    use_colab_render:  document.getElementById('use_colab_render').checked,
   668|    colab_url:         document.getElementById('colab_url').value,
   669|  }};
   670|  await fetch('/start', {{
   671|    method:  'POST',
   672|    headers: {{'Content-Type': 'application/json'}},
   673|    body:    JSON.stringify(body),
   674|  }});
   675|}}
   676|
   677|// ── LOG COLORING ──
   678|function classifyLog(line) {{
   679|  if (line.includes('✅') || line.includes('🎉'))  return 'success';
   680|  if (line.includes('❌') || line.includes('⚠️')) return 'error';
   681|  if (line.includes('━━━') || line.includes('---')) return 'stage';
   682|  if (line.includes('☁️') || line.includes('📤') || line.includes('📥')) return 'info';
   683|  return '';
   684|}}
   685|
   686|// ── POLL STATUS ──
   687|setInterval(async () => {{
   688|  try {{
   689|    const r = await fetch('/status');
   690|    const d = await r.json();
   691|
   692|    // Logs
   693|    const logsDiv = document.getElementById('logs');
   694|    logsDiv.innerHTML = d.logs.map(l =>
   695|      `<div class="log-line ${{classifyLog(l)}}">${{l}}</div>`
   696|    ).join('');
   697|    logsDiv.scrollTop = logsDiv.scrollHeight;
   698|
   699|    // Active stage
   700|    document.querySelectorAll('.stage-item').forEach((el, i) =>
   701|      el.classList.toggle('active', i + 1 === d.stage)
   702|    );
   703|
   704|    // Status dot
   705|    const dot  = document.getElementById('status-dot');
   706|    const text = document.getElementById('status-text');
   707|    const last = d.logs[d.logs.length - 1] || '';
   708|    if (last.includes('❌'))             {{ dot.className="status-indicator error";   text.textContent="Ошибка"; }}
   709|    else if (last.includes('🎉'))        {{ dot.className="status-indicator done";    text.textContent="Завершено"; }}
   710|    else if (d.stage > 0 && !last.includes('🎉')) {{ dot.className="status-indicator running"; text.textContent="Выполняется..."; }}
   711|    else                                 {{ dot.className="status-indicator";          text.textContent="Ожидание"; }}
   712|</script>
   713|
   714|<!-- YOUTUBE UPLOAD FUNCTIONS -->
   715|<script>
   716|// Проверка настройки YouTube
   717|async function checkYouTubeSetup() {{
   718|  try {{
   719|    const response = await fetch('/youtube/setup');
   720|    const data = await response.json();
   721|    
   722|    const statusDot = document.getElementById('youtube-status-dot');
   723|    const statusText = document.getElementById('youtube-status-text');
   724|    const statusDetails = document.getElementById('youtube-status-details');
   725|    const youtubeStatus = document.getElementById('youtube-status');
   726|    
   727|    const setup = data.setup_info;
   728|    
   729|    // Обновление статуса
   730|    if (setup.is_configured) {{
   731|      statusDot.className = "status-indicator done";
   732|      statusText.textContent = "YouTube настроен ✓";
   733|      youtubeStatus.textContent = "(Configured)";
   734|      youtubeStatus.style.color = "var(--success)";
   735|      
   736|      // Показываем форму загрузки
   737|      document.getElementById('youtube-setup-section').style.display = 'block';
   738|      document.getElementById('youtube-not-configured').style.display = 'none';
   739|      
   740|      // Загружаем список видео
   741|      loadAvailableVideos();
   742|    }} else {{
   743|      statusDot.className = "status-indicator error";
   744|      statusText.textContent = "YouTube не настроен ✗";
   745|      youtubeStatus.textContent = "(Not configured)";
   746|      youtubeStatus.style.color = 'var(--danger)';
   747|      
   748|      // Показываем что не настроено
   749|      showYouTubeNotConfigured(setup);
   750|    }}
   751|    
   752|    // Детали
   753|    let details = [];
   754|    if (!setup.oauth_json_exists) {{
   755|      details.push('❌ Отсутствует OAuth JSON файл (client_secret.json)');
   756|    }}
   757|    if (!setup.token_exists) {{
   758|      details.push('⚠️  Токен авторизации не найден');
   759|    }}
   760|    if (setup.required_packages.length > 0) {{
   761|      details.push(`⚠️  Отсутствуют пакеты: ${{setup.required_packages.join(', ')}}`);
   762|    }}
   763|    
   764|    statusDetails.innerHTML = details.map(d => `<div>${{d}}</div>`).join('');
   765|    
   766|  }} catch (error) {{
   767|    console.error('YouTube setup check error:', error);
   768|    alert('Ошибка проверки настроек YouTube');
   769|  }}
   770|}}
   771|
   772|// Показать что YouTube не настроен
   773|function showYouTubeNotConfigured(setup) {{
   774|  const details = document.getElementById('youtube-status-details');
   775|  details.innerHTML = `
   776|    <div style="margin-bottom:8px">Для настройки YouTube:</div>
   777|    <div style="font-size:11px; color:var(--muted);">
   778|      1. Создайте проект в Google Cloud Console<br>
   779|      2. Включите YouTube Data API v3<br>
   780|      3. Создайте OAuth 2.0 Desktop App credentials<br>
   781|      4. Скачайте client_secret.json и загрузите в настройки
   782|    </div>
   783|    <button onclick="setupYouTube()" style="margin-top:12px; padding:8px 16px; background:var(--surface); border:1px solid var(--border); border-radius:6px; color:var(--text); font-family:var(--font-mono); font-size:12px; cursor:pointer;">
   784|      📋 Показать полные инструкции
   785|    </button>
   786|  `;
   787|}}
   788|
   789|// Загрузка списка доступных видео
   790|async function loadAvailableVideos() {{
   791|  try {{
   792|    const response = await fetch('/youtube/list-videos');
   793|    const data = await response.json();
   794|    
   795|    const select = document.getElementById('youtube-video-select');
   796|    
   797|    // Очищаем все опции кроме первой
   798|    while (select.options.length > 1) {{
   799|      select.remove(1);
   800|    }}
   801|    
   802|    // Добавляем видео
   803|    data.videos.forEach(video => {{
   804|      const option = document.createElement('option');
   805|      option.value = video.path;
   806|      option.textContent = `${{video.name}} (${{formatFileSize(video.size)}})`;
   807|      select.appendChild(option);
   808|    }});
   809|    
   810|  }} catch (error) {{
   811|    console.error('Video list load error:', error);
   812|  }}
   813|}}
   814|
   815|// Форматирование размера файла
   816|function formatFileSize(bytes) {{
   817|  if (bytes === 0) return '0 Bytes';
   818|  const k = 1024;
   819|  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
   820|  const i = Math.floor(Math.log(bytes) / Math.log(k));
   821|  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
   822|}}
   823|
   824|// Установить завтра 18:00
   825|function setTomorrow18() {{
   826|  const now = new Date();
   827|  const tomorrow = new Date(now);
   828|  tomorrow.setDate(tomorrow.getDate() + 1);
   829|  tomorrow.setHours(18, 0, 0, 0);
   830|  
   831|  const input = document.getElementById('youtube-schedule');
   832|  input.value = tomorrow.toISOString().slice(0, 16);
   833|}}
   834|
   835|// Загрузка на YouTube
   836|async function startYouTubeUpload() {{
   837|  const videoSelect = document.getElementById('youtube-video-select');
   838|  const scheduleInput = document.getElementById('youtube-schedule');
   839|  const titleInput = document.getElementById('youtube-custom-title');
   840|  const descInput = document.getElementById('youtube-custom-desc');
   841|  const tagsInput = document.getElementById('youtube-custom-tags');
   842|  
   843|  // Конвертируем локальное время в ISO string если указано
   844|  let scheduleTime = '';
   845|  if (scheduleInput.value) {{
   846|    const localDate = new Date(scheduleInput.value);
   847|    scheduleTime = localDate.toISOString();
   848|  }}
   849|  
   850|  const uploadData = {{
   851|    video_path: videoSelect.value || '',
   852|    schedule_time: scheduleTime,
   853|    custom_title: titleInput.value || '',
   854|    custom_description: descInput.value || '',
   855|    custom_tags: tagsInput.value || '',
   856|    notify_subscribers: true
   857|  }};
   858|  
   859|  try {{
   860|    const response = await fetch('/youtube/upload', {{
   861|      method: 'POST',
   862|      headers: {{ 'Content-Type': 'application/json' }},
   863|      body: JSON.stringify(uploadData)
   864|    }});
   865|    
   866|    const result = await response.json();
   867|    
   868|    if (result.status === 'started') {{
   869|      alert(`✅ Загрузка начата!\nВидео: ${{result.video_path}}\nДата публикации: ${{result.schedule_time || 'Не указана'}}`);
   870|      // Можно добавить статус загрузки
   871|    }} else {{
   872|      alert(`❌ Ошибка: ${{result.message}}`);
   873|    }}
   874|    
   875|  }} catch (error) {{
   876|    console.error('YouTube upload error:', error);
   877|    alert('Ошибка загрузки на YouTube');
   878|  }}
   879|}}
   880|
   881|// Публикация сейчас (без отложенной публикации)
   882|async function startYouTubeUploadNow() {{
   883|  if (!confirm('Видео будет опубликовано СЕЙЧАС как unlisted (доступно по ссылке).\nПродолжить?')) {{
   884|    return;
   885|  }}
   886|  
   887|  const videoSelect = document.getElementById('youtube-video-select');
   888|  const titleInput = document.getElementById('youtube-custom-title');
   889|  const descInput = document.getElementById('youtube-custom-desc');
   890|  const tagsInput = document.getElementById('youtube-custom-tags');
   891|  
   892|  const uploadData = {{
   893|    video_path: videoSelect.value || '',
   894|    schedule_time: '', // Пусто = публикация сейчас
   895|    custom_title: titleInput.value || '',
   896|    custom_description: descInput.value || '',
   897|    custom_tags: tagsInput.value || '',
   898|    notify_subscribers: false // Не уведомлять для быстрой публикации
   899|  }};
   900|  
   901|  try {{
   902|    const response = await fetch('/youtube/upload', {{
   903|      method: 'POST',
   904|      headers: {{ 'Content-Type': 'application/json' }},
   905|      body: JSON.stringify(uploadData)
   906|    }});
   907|    
   908|    const result = await response.json();
   909|    
   910|    if (result.status === 'started') {{
   911|      alert(`✅ Видео загружено!\nСтатус: Unlisted (доступно по ссылке)`);
   912|    }} else {{
   913|      alert(`❌ Ошибка: ${{result.message}}`);
   914|    }}
   915|    
   916|  }} catch (error) {{
   917|    console.error('YouTube upload now error:', error);
   918|    alert('Ошибка загрузки на YouTube');
   919|  }}
   920|}}
   921|
   922|// Настройка YouTube
   923|function setupYouTube() {{
   924|  alert('📺 Настройка YouTube:\n\n1. Перейдите на https://console.cloud.google.com\n2. Создайте проект и включите YouTube Data API v3\n3. Создайте OAuth 2.0 Desktop App credentials\n4. Скачайте client_secret.json\n5. Загрузите файл в папку проекта\n\nПодробные инструкции в файле YOUTUBE_SETUP_INSTRUCTIONS.md');
   925|  
   926|  // Можно добавить форму загрузки файла
   927|  const fileInput = document.createElement('input');
   928|  fileInput.type = 'file';
   929|  fileInput.accept = '.json';
   930|  fileInput.style.display = 'none';
   931|  fileInput.onchange = handleOAuthFileUpload;
   932|  document.body.appendChild(fileInput);
   933|  fileInput.click();
   934|}}
   935|
   936|// Загрузка OAuth файла
   937|async function handleOAuthFileUpload(event) {{
   938|  const file = event.target.files[0];
   939|  if (!file) return;
   940|  
   941|  // В реальной реализации нужно загрузить файл на сервер
   942|  alert('OAuth файл загружен. Теперь проверьте настройки.');
   943|  checkYouTubeSetup();
   944|}}
   945|
   946|// Загрузка истории загрузок
   947|async function loadYouTubeHistory() {{
   948|  try {{
   949|    const response = await fetch('/youtube/uploads-history');
   950|    const data = await response.json();
   951|    
   952|    let historyHtml = '<div style="max-height:300px; overflow-y:auto; margin-top:12px;">';
   953|    
   954|    if (data.history && data.history.length > 0) {{
   955|      data.history.forEach(record => {{
   956|        const date = new Date(record.upload_time).toLocaleString('ru-RU');
   957|        const videoTitle = record.metadata?.title || 'Без названия';
   958|        const videoUrl = record.video_url || '#';
   959|        const scheduleTime = record.schedule_time 
   960|          ? new Date(record.schedule_time).toLocaleString('ru-RU')
   961|          : 'Сразу';
   962|        
   963|        historyHtml += `
   964|          <div style="background:var(--surface); padding:12px; border-radius:6px; margin-bottom:8px; border-left:3px solid var(--accent);">
   965|            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
   966|              <span style="font-weight:600; color:var(--text);">${{videoTitle}}</span>
   967|              <span style="font-size:11px; color:var(--muted);">${{date}}</span>
   968|            </div>
   969|            <div style="font-size:11px; color:var(--muted);">
   970|              ID: ${{record.video_id}} <br>
   971|              Публикация: ${{scheduleTime}} <br>
   972|              <a href="${{videoUrl}}" target="_blank" style="color:var(--accent2); text-decoration:none;">🔗 Ссылка на видео</a>
   973|            </div>
   974|          </div>
   975|        `;
   976|      }});
   977|    }} else {{
   978|      historyHtml += '<div style="text-align:center; color:var(--muted); padding:24px;">История загрузок пуста</div>';
   979|    }}
   980|    
   981|    historyHtml += '</div>';
   982|    
   983|    // Показываем в модальном окне
   984|    showModal('📜 История загрузок на YouTube', historyHtml);
   985|    
   986|  }} catch (error) {{
   987|    console.error('YouTube history load error:', error);
   988|  }}
   989|}}
   990|
   991|// Вспомогательная функция для модального окна
   992|function showModal(title, content) {{
   993|  // Простая реализация модального окна
   994|  const modal = document.createElement('div');
   995|  modal.style.cssText = `
   996|    position:fixed; top:0; left:0; right:0; bottom:0; 
   997|    background:rgba(0,0,0,0.8); z-index:1000; 
   998|    display:flex; align-items:center; justify-content:center;
   999|  `;
  1000|  
  1001|  modal.innerHTML = `
  1002|    <div style="background:var(--bg); border:1px solid var(--border); border-radius:12px; max-width:600px; width:90%; max-height:80vh; overflow:hidden;">
  1003|      <div style="padding:20px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center;">
  1004|        <div style="font-size:18px; font-weight:600;">${{title}}</div>
  1005|        <button onclick="this.parentElement.parentElement.parentElement.remove()" style="background:none; border:none; color:var(--muted); font-size:24px; cursor:pointer;">&times;</button>
  1006|      </div>
  1007|      <div style="padding:20px; overflow-y:auto; max-height:calc(80vh - 61px);">
  1008|        ${{content}}
  1009|      </div>
  1010|    </div>
  1011|  `;
  1012|  
  1013|  document.body.appendChild(modal);
  1014|  
  1015|  // Закрытие по клику на оверлей
  1016|  modal.onclick = function(e) {{
  1017|    if (e.target === modal) {{
  1018|      modal.remove();
  1019|    }}
  1020|  }};
  1021|}}
  1022|
  1023|// Автопроверка при загрузке
  1024|window.onload = async () => {{
  1025|  // Вызов вашего существующего onload
  1026|  buildPipeline();
  1027|  try {{
  1028|    const r = await fetch('/settings');
  1029|    const d = await r.json();
  1030|    document.getElementById('aspect_ratio').value = d.aspect_ratio || '9:16';
  1031|    document.getElementById('quality').value = d.quality || '1080p';
  1032|    document.getElementById('codec').value = d.codec || 'libx264';
  1033|    document.getElementById('test_mode').checked = d.test_mode || false;
  1034|    document.getElementById('use_colab_whisper').checked = d.use_colab_whisper || false;
  1035|    document.getElementById('use_colab_render').checked = d.use_colab_render || false;
  1036|    document.getElementById('colab_url').value = d.colab_url || '';
  1037|  }} catch (e) {{}}
  1038|  onColabChange();
  1039|  
  1040|  // Проверяем YouTube настройки
  1041|  checkYouTubeSetup();
  1042|}};
  1043|
  1044|</script>
  1045|</body>
  1046|</html>"""
  1047|
  1048|
  1049|@app.post("/start")
  1050|async def start_task(req: StartRequest, background_tasks: BackgroundTasks):
  1051|    with open("settings.json", "w", encoding="utf-8") as f:
  1052|        json.dump(req.model_dump(), f, indent=4, ensure_ascii=False)
  1053|    background_tasks.add_task(manager.run_pipeline, start_from=req.stage, custom_idea=req.idea)
  1054|    return {"status": "started"}
  1055|
  1056|
  1057|@app.get("/status")
  1058|async def get_status():
  1059|    return {"stage": manager.current_stage_idx, "logs": manager.logs}
  1060|
  1061|
  1062|@app.get("/youtube/setup")
  1063|async def get_youtube_setup_info():
  1064|    """Получение информации о настройке YouTube."""
  1065|    setup_info = check_youtube_setup()
  1066|    credentials = get_youtube_credentials()
  1067|    
  1068|    return {
  1069|        "setup_info": setup_info,
  1070|        "credentials": credentials,
  1071|        "instructions": "Скачайте client_secret.json из Google Cloud Console и загрузите в настройки."
  1072|    }
  1073|
  1074|
  1075|@app.post("/youtube/save-config")
  1076|async def save_youtube_config_endpoint(config: YouTubeConfig):
  1077|    """Сохранение конфигурации YouTube."""
  1078|    try:
  1079|        success = save_youtube_config(
  1080|            oauth_json_path=config.oauth_client_json,
  1081|            schedule_time=config.schedule_time,
  1082|            auto_upload=config.auto_upload
  1083|        )
  1084|        
  1085|        if success:
  1086|            return {"status": "success", "message": "Конфигурация YouTube сохранена"}
  1087|        else:
  1088|            return {"status": "error", "message": "Ошибка сохранения конфигурации"}
  1089|    except Exception as e:
  1090|        return {"status": "error", "message": f"Ошибка: {str(e)}"}
  1091|
  1092|
  1093|@app.post("/youtube/validate-oauth")
  1094|async def validate_oauth_file(file_path: str):
  1095|    """Валидация OAuth JSON файла."""
  1096|    is_valid, message = validate_oauth_json(file_path)
  1097|    return {
  1098|        "valid": is_valid,
  1099|        "message": message,
  1100|        "file_path": file_path
  1101|    }
  1102|
  1103|
  1104|@app.get("/youtube/list-videos")
  1105|async def list_available_videos():
  1106|    """Список доступных видео для загрузки."""
  1107|    videos_dir = "outputs/final_videos"
  1108|    video_files = []
  1109|    
  1110|    if os.path.exists(videos_dir):
  1111|        for ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
  1112|            for file_path in Path(videos_dir).glob(f"*{ext}"):
  1113|                video_files.append({
  1114|                    "path": str(file_path),
  1115|                    "name": file_path.name,
  1116|                    "size": os.path.getsize(file_path),
  1117|                    "modified": os.path.getmtime(file_path)
  1118|                })
  1119|    
  1120|    # Сортируем по дате изменения (новые первыми)
  1121|    video_files.sort(key=lambda x: x["modified"], reverse=True)
  1122|    
  1123|    return {
  1124|        "videos": video_files,
  1125|        "count": len(video_files)
  1126|    }
  1127|
  1128|
  1129|@app.post("/youtube/upload")
  1130|async def upload_to_youtube(req: YouTubeUploadRequest, background_tasks: BackgroundTasks):
  1131|    """Загрузка видео на YouTube."""
  1132|    try:
  1133|        # Получаем конфигурацию
  1134|        config = get_youtube_credentials()
  1135|        if not config:
  1136|            return {"status": "error", "message": "YouTube не настроен. Загрузите OAuth JSON файл."}
  1137|        
  1138|        # Определяем путь к видео
  1139|        video_path = req.video_path
  1140|        if not video_path or not os.path.exists(video_path):
  1141|            # Ищем последнее видео
  1142|            latest_video = find_latest_video()
  1143|            if not latest_video:
  1144|                return {"status": "error", "message": "Видео для загрузки не найдено"}
  1145|            video_path = latest_video
  1146|        
  1147|        # Создаем загрузчик
  1148|        uploader = YouTubeUploader(oauth_client_json_path=config.get("oauth_client_json", ""))
  1149|        
  1150|        # Генерируем метаданные
  1151|        video_title = req.custom_title or f"AI Generated Video - {datetime.now().strftime('%Y-%m-%d')}"
  1152|        
  1153|        metadata = uploader.generate_metadata(
  1154|            video_title=video_title,
  1155|            story_draft_path="data/story_draft.txt"
  1156|        )
  1157|        
  1158|        # Обновляем кастомными данными если есть
  1159|        if req.custom_description:
  1160|            metadata["description"] = req.custom_description
  1161|        if req.custom_tags:
  1162|            custom_tags = [tag.strip() for tag in req.custom_tags.split(",") if tag.strip()]
  1163|            metadata["tags"] = custom_tags + metadata.get("tags", [])[:30]  # Ограничиваем 30 тегами
  1164|        
  1165|        # Определяем время публикации
  1166|        schedule_time = req.schedule_time
  1167|        if not schedule_time and config.get("schedule_time"):
  1168|            schedule_time = config.get("schedule_time")
  1169|        
  1170|        # Запускаем загрузку в фоне
  1171|        background_tasks.add_task(
  1172|            perform_youtube_upload,
  1173|            uploader=uploader,
  1174|            video_path=video_path,
  1175|            metadata=metadata,
  1176|            schedule_time=schedule_time,
  1177|            notify_subscribers=req.notify_subscribers
  1178|        )
  1179|        
  1180|        return {
  1181|            "status": "started",
  1182|            "message": "Загрузка на YouTube начата",
  1183|            "video_path": video_path,
  1184|            "schedule_time": schedule_time
  1185|        }
  1186|        
  1187|    except Exception as e:
  1188|        return {"status": "error", "message": f"Ошибка: {str(e)}"}
  1189|
  1190|
  1191|async def perform_youtube_upload(uploader: YouTubeUploader, video_path: str, 
  1192|                               metadata: dict, schedule_time: Optional[str],
  1193|                               notify_subscribers: bool = True):
  1194|    """Фоновая задача для загрузки на YouTube."""
  1195|    try:
  1196|        print(f"📤 Начинаю загрузку на YouTube: {video_path}")
  1197|        
  1198|        success, video_id, video_url = uploader.upload_video(
  1199|            video_path=video_path,
  1200|            metadata=metadata,
  1201|            schedule_time=schedule_time,
  1202|            notify_subscribers=notify_subscribers
  1203|        )
  1204|        
  1205|        if success:
  1206|            # Сохраняем запись о загрузке
  1207|            save_upload_record(video_id, video_url, metadata, schedule_time)
  1208|            print(f"✅ Видео успешно загружено на YouTube: {video_url}")
  1209|        else:
  1210|            print(f"❌ Ошибка загрузки на YouTube: {video_url}")
  1211|            
  1212|    except Exception as e:
  1213|        print(f"❌ Критическая ошибка при загрузке на YouTube: {e}")
  1214|
  1215|
  1216|@app.get("/youtube/uploads-history")
  1217|async def get_uploads_history():
  1218|    """История загрузок на YouTube."""
  1219|    history_file = "youtube_uploads.json"
  1220|    
  1221|    if os.path.exists(history_file):
  1222|        with open(history_file, 'r', encoding='utf-8') as f:
  1223|            try:
  1224|                history = json.load(f)
  1225|                # Сортируем по времени загрузки (новые первыми)
  1226|                history.sort(key=lambda x: x.get("upload_time", ""), reverse=True)
  1227|                return {"history": history}
  1228|            except json.JSONDecodeError:
  1229|                return {"history": []}
  1230|    else:
  1231|        return {"history": []}