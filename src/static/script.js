// Константы и глобальные переменные
const STAGE_ICONS = ["✍️","🎬","👤","🖼️","🔊","📝","📋","🎞️"];
const COLAB_STAGES = [5, 7]; // Индексы этапов, где доступен Colab (1-based: 5 и 7)
let currentTemplates = [];
let activeTab = 'master';

// --- ИНИЦИАЛИЗАЦИЯ ---
document.addEventListener('DOMContentLoaded', () => {
    buildPipeline();
    loadSettings();
    loadTemplates();
});

// Загрузка шаблонов с сервера
async function loadTemplates() {
    try {
        const r = await fetch('/templates_data');
        currentTemplates = await r.json();
        renderTemplates();
    } catch (e) { console.error("Ошибка загрузки шаблонов", e); }
}

// Отрисовка контента внутри модалки
function renderTemplates() {
    const container = document.getElementById('episodes-modal-body');
    if (!container) return;

    if (currentTemplates.length === 0) {
        container.innerHTML = '<div style="padding:20px; color:var(--muted)">Данные пока не сгенерированы...</div>';
        return;
    }

    // Фильтруем данные в зависимости от активной вкладки
    const data = activeTab === 'master' 
        ? currentTemplates.filter(t => t.id === 'master')
        : currentTemplates.filter(t => t.id !== 'master');

    container.innerHTML = data.map(t => `
        <div class="template-item" style="padding:15px; border-bottom:1px solid var(--border)">
            <div style="font-weight:bold; color:var(--accent2); margin-bottom:8px">${t.name}</div>
            <pre style="white-space:pre-wrap; font-size:12px; background:#000; padding:10px; border-radius:8px">${t.content}</pre>
        </div>
    `).join('');
}

function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    renderTemplates();
}


function buildPipeline() {
    const el = document.getElementById('pipeline');
    if (!el) return;
    
    // Генерируем этапы на основе стандартного набора (или получаем с сервера)
    const stages = [
        {name: "Сценарий", icon: "✍️"}, {name: "Раскадровка", icon: "🎬"},
        {name: "Персонажи", icon: "👤"}, {name: "Генерация", icon: "🖼️"},
        {name: "Озвучка", icon: "🔊"}, {name: "Субтитры", icon: "📝"},
        {name: "Сборка", icon: "📋"}, {name: "Рендер", icon: "🎞️"}
    ];

    el.innerHTML = stages.map((s, i) => {
        const stageNum = i + 1;
        const isColab = COLAB_STAGES.includes(stageNum);
        return `
            <div class="stage-item" id="stage-${stageNum}" onclick="startFrom(${stageNum})">
                <span class="stage-num">${stageNum}</span>
                <span class="stage-icon">${s.icon}</span>
                <span class="stage-name">${s.name}</span>
                ${isColab ? '<span class="stage-badge">COLAB</span>' : ''}
                <button class="stage-run-btn">▶</button>
            </div>`;
    }).join('');
}

// --- УПРАВЛЕНИЕ AI НАСТРОЙКАМИ ---
function toggleAiSettings() {
    document.getElementById('ai-settings-section').classList.toggle('expanded');
}

async function loadSettings() {
    try {
        const r = await fetch('/settings');
        const d = await r.json();
        if (d.ai_settings?.text) {
            document.getElementById('ai_api_url').value = d.ai_settings.text.api_url || '';
            document.getElementById('ai_folder_id').value = d.ai_settings.text.folder_id || '';
            document.getElementById('ai_model').value = d.ai_settings.text.model || '';
        }
        // Загружаем промпты в редакторы
        if (d.prompts) {
            document.getElementById('prompt_writer').value = d.prompts.stage_1_writer || '';
            document.getElementById('prompt_stage_2').value = d.prompts.stage_2_scenes || '';
        }
    } catch (e) { console.error("Ошибка загрузки настроек", e); }
}

async function saveAiSettings() {
    const data = {
        ai_settings: {
            text: {
                api_url: document.getElementById('ai_api_url').value,
                api_key: document.getElementById('ai_api_key').value,
                folder_id: document.getElementById('ai_folder_id').value,
                model: document.getElementById('ai_model').value
            }
        }
    };
    await sendUpdate(data, "Настройки AI сохранены");
}

// --- ЗАПУСК ПАЙПЛАЙНА ---
async function startFrom(stageNum) {
    const idea = document.getElementById('idea-input').value;
    if (stageNum === 1 && !idea.trim()) {
        alert("Введите идею или сценарий для начала!");
        return;
    }

    updateStatus('running', `Запуск этапа ${stageNum}...`);
    addLog(`>>> Запуск Pipeline с этапа ${stageNum}...`, 'stage');

    const payload = {
        stage: stageNum,
        idea: idea,
        num_episodes: parseInt(document.getElementById('num_episodes').value),
        aspect_ratio: document.getElementById('aspect_ratio').value,
        test_mode: document.getElementById('test_mode').checked,
        use_colab_whisper: document.getElementById('use_colab_whisper').checked,
        use_colab_render: document.getElementById('use_colab_render').checked,
        colab_url: document.getElementById('colab_url').value,
        auto_continue: document.getElementById('auto_continue').checked
    };

    try {
        const r = await fetch('/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const res = await r.json();
        addLog(`Сервер: ${res.message || 'Пайплайн запущен'}`, 'success');
    } catch (e) {
        addLog(`Ошибка запуска: ${e}`, 'error');
        updateStatus('error', 'Ошибка');
    }
}

// --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
function addLog(text, type = '') {
    const logs = document.getElementById('logs');
    const line = document.createElement('div');
    line.className = `log-line ${type}`;
    line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
    logs.appendChild(line);
    logs.scrollTop = logs.scrollHeight;
}

function updateStatus(state, text) {
    const dot = document.getElementById('status-dot');
    const txt = document.getElementById('status-text');
    dot.className = 'status-indicator ' + state;
    txt.textContent = text;
}

function onColabChange() {
    const isAnyColab = document.getElementById('use_colab_whisper').checked || 
                       document.getElementById('use_colab_render').checked;
    document.getElementById('colab_url_wrap').style.display = isAnyColab ? 'block' : 'none';
}

async function sendUpdate(data, successMsg) {
    try {
        await fetch('/update_settings', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        addLog(successMsg, 'success');
    } catch(e) { addLog("Ошибка сохранения", "error"); }
}

// ... (начало файла такое же, как раньше) ...

// Универсальные функции для модалок
function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('open');
    if (id === 'episodesModal') loadTemplates(); // Загружаем данные при открытии эпизодов
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('open');
}

// Обновленная функция старта (берет данные из новых ID)
async function startFrom(stageNum) {
    const ideaInput = document.getElementById('idea-input');
    const idea = ideaInput ? ideaInput.value : "";
    
    if (stageNum === 1 && !idea.trim()) {
        alert("Введите идею или сценарий!");
        return;
    }

    const getVal = (id) => document.getElementById(id)?.value;
    const getCheck = (id) => document.getElementById(id)?.checked;

    updateStatus('running', `Запуск этапа ${stageNum}...`);
    addLog(`>>> Старт Pipeline (Этап ${stageNum})`, 'stage');

    const payload = {
        stage: stageNum,
        idea: idea,
        num_episodes: parseInt(getVal('num_episodes') || 3),
        aspect_ratio: getVal('aspect_ratio'),
        test_mode: getCheck('test_mode'),
        use_colab_whisper: getCheck('use_colab_whisper'),
        use_colab_render: getCheck('use_colab_render'),
        colab_url: getVal('colab_url'),
        auto_continue: getCheck('auto_continue')
    };

    try {
        const r = await fetch('/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const res = await r.json();
        addLog(`Сервер: ${res.message}`, 'success');
    } catch (e) {
        addLog(`Ошибка: ${e}`, 'error');
        updateStatus('error', 'Ошибка');
    }
}

// ... (остальные функции: loadSettings, buildPipeline и т.д.) ...

// Функции для модалок
function openEpisodesModal() { document.getElementById('episodes-modal').classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
