/* ═══════════════════════════════════════════════════════════════
   GLOBAL STATE
   ═══════════════════════════════════════════════════════════════ */
let currentTemplateId = null;
let templates = [];
let statusPollInterval = null;

/* ═══════════════════════════════════════════════════════════════
   INITIALIZATION
   ═══════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    startStatusPolling();
    setupColabToggleHandlers();
});

/* ═══════════════════════════════════════════════════════════════
   SETTINGS MANAGEMENT
   ═══════════════════════════════════════════════════════════════ */
async function loadSettings() {
    try {
        const response = await fetch('/settings');
        const settings = await response.json();
        
        // Main settings
        document.getElementById('aspect_ratio').value = settings.aspect_ratio || '9:16';
        document.getElementById('quality').value = settings.quality || '1080p';
        document.getElementById('codec').value = settings.codec || 'libx264';
        document.getElementById('num_episodes').value = settings.num_episodes || 3;
        document.getElementById('test_mode').checked = settings.test_mode || false;
        document.getElementById('auto_continue').checked = settings.auto_continue !== false;
        document.getElementById('use_colab_whisper').checked = settings.use_colab_whisper || false;
        document.getElementById('use_colab_render').checked = settings.use_colab_render || false;
        document.getElementById('colab_url').value = settings.colab_url || '';
        
        // AI Settings
        if (settings.ai_settings && settings.ai_settings.text) {
            document.getElementById('ai_api_url').value = settings.ai_settings.text.api_url || '';
            document.getElementById('ai_api_key').value = settings.ai_settings.text.api_key || '';
            document.getElementById('ai_folder_id').value = settings.ai_settings.text.folder_id || '';
            document.getElementById('ai_model').value = settings.ai_settings.text.model || '';
        }
        
        // Update Colab URL field visibility
        updateColabUrlVisibility();
    } catch (error) {
        console.error('Error loading settings:', error);
        showNotification('Ошибка загрузки настроек', 'error');
    }
}

function setupColabToggleHandlers() {
    const whisperToggle = document.getElementById('use_colab_whisper');
    const renderToggle = document.getElementById('use_colab_render');
    
    whisperToggle.addEventListener('change', updateColabUrlVisibility);
    renderToggle.addEventListener('change', updateColabUrlVisibility);
}

function updateColabUrlVisibility() {
    const whisperChecked = document.getElementById('use_colab_whisper').checked;
    const renderChecked = document.getElementById('use_colab_render').checked;
    const colabUrlField = document.getElementById('colab_url_field');
    
    if (whisperChecked || renderChecked) {
        colabUrlField.style.display = 'block';
    } else {
        colabUrlField.style.display = 'none';
    }
}

/* ═══════════════════════════════════════════════════════════════
   PIPELINE CONTROL
   ═══════════════════════════════════════════════════════════════ */
async function startPipeline() {
    const idea = document.getElementById('idea').value.trim();
    const stage = parseInt(document.getElementById('start_stage').value);
    
    if (!idea && stage === 1) {
        showNotification('Введите идею проекта', 'warning');
        return;
    }
    
    const requestData = {
        stage: stage,
        idea: idea,
        num_episodes: parseInt(document.getElementById('num_episodes').value),
        aspect_ratio: document.getElementById('aspect_ratio').value,
        quality: document.getElementById('quality').value,
        codec: document.getElementById('codec').value,
        test_mode: document.getElementById('test_mode').checked,
        use_colab_whisper: document.getElementById('use_colab_whisper').checked,
        use_colab_render: document.getElementById('use_colab_render').checked,
        colab_url: document.getElementById('colab_url').value,
        auto_continue: document.getElementById('auto_continue').checked,
        ai_settings: {
            text: {
                api_url: document.getElementById('ai_api_url').value,
                api_key: document.getElementById('ai_api_key').value,
                folder_id: document.getElementById('ai_folder_id').value,
                model: document.getElementById('ai_model').value
            }
        }
    };
    
    try {
        showLoading();
        const response = await fetch('/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        hideLoading();
        
        if (data.status === 'started') {
            showNotification('Pipeline запущен', 'success');
            updateStatusBadge('active');
        } else {
            showNotification('Ошибка запуска', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Error starting pipeline:', error);
        showNotification('Ошибка запуска pipeline', 'error');
    }
}

/* ═══════════════════════════════════════════════════════════════
   STATUS POLLING
   ═══════════════════════════════════════════════════════════════ */
function startStatusPolling() {
    statusPollInterval = setInterval(updateStatus, 2000);
}

async function updateStatus() {
    try {
        const response = await fetch('/status');
        const data = await response.json();
        
        // Update stage display
        const currentStageEl = document.getElementById('currentStage');
        if (data.stage && window.STAGES_DATA && window.STAGES_DATA[data.stage - 1]) {
            currentStageEl.textContent = `Stage ${data.stage}: ${window.STAGES_DATA[data.stage - 1].name}`;
        } else {
            currentStageEl.textContent = '—';
        }
        
        // Update logs
        const logsContainer = document.getElementById('logs');
        if (data.logs && data.logs.length > 0) {
            logsContainer.innerHTML = data.logs
                .map(log => `<div class="log-entry">${escapeHtml(log)}</div>`)
                .join('');
            logsContainer.scrollTop = logsContainer.scrollHeight;
        }
    } catch (error) {
        console.error('Error updating status:', error);
    }
}

function updateStatusBadge(status) {
    const badge = document.getElementById('statusBadge');
    badge.classList.remove('active');
    
    if (status === 'active') {
        badge.textContent = 'Выполняется';
        badge.classList.add('active');
    } else {
        badge.textContent = 'Ожидание';
    }
}

/* ═══════════════════════════════════════════════════════════════
   AI SETTINGS
   ═══════════════════════════════════════════════════════════════ */
function toggleAISettings() {
    const panel = document.getElementById('aiSettingsPanel');
    const toggleText = document.getElementById('aiSettingsToggleText');
    
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        toggleText.textContent = 'Скрыть настройки';
    } else {
        panel.style.display = 'none';
        toggleText.textContent = 'Показать настройки';
    }
}

async function saveAISettings() {
    const data = {
        text: {
            api_url: document.getElementById('ai_api_url').value,
            api_key: document.getElementById('ai_api_key').value,
            folder_id: document.getElementById('ai_folder_id').value,
            model: document.getElementById('ai_model').value
        }
    };
    
    try {
        showLoading();
        const response = await fetch('/save-ai-settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.message) {
            showNotification('AI настройки сохранены', 'success');
        } else {
            showNotification(result.error || 'Ошибка сохранения', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Error saving AI settings:', error);
        showNotification('Ошибка сохранения AI настроек', 'error');
    }
}

/* ═══════════════════════════════════════════════════════════════
   TEMPLATE MANAGER
   ═══════════════════════════════════════════════════════════════ */
async function openTemplateManager() {
    const modal = document.getElementById('templateManagerModal');
    modal.classList.add('active');
    await loadTemplates();
}

function closeTemplateManager() {
    const modal = document.getElementById('templateManagerModal');
    modal.classList.remove('active');
}

async function loadTemplates() {
    try {
        showLoading();
        const response = await fetch('/api/templates');
        const data = await response.json();
        templates = data.templates || [];
        hideLoading();
        
        renderTemplatesList();
    } catch (error) {
        hideLoading();
        console.error('Error loading templates:', error);
        showNotification('Ошибка загрузки шаблонов', 'error');
    }
}

function renderTemplatesList() {
    const container = document.getElementById('templatesList');
    
    if (templates.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: var(--muted); padding: 40px;">Нет сохраненных шаблонов</p>';
        return;
    }
    
    container.innerHTML = templates.map(template => `
        <div class="template-card" onclick="editTemplate('${template.id}')">
            <div class="template-card-header">
                <div class="template-card-title">${escapeHtml(template.name)}</div>
                ${template.is_default ? '<span class="template-badge default">Default</span>' : '<span class="template-badge">Custom</span>'}
            </div>
            <div class="template-card-meta">
                Создан: ${formatDate(template.created_at)}
            </div>
            <div class="template-card-actions">
                <button class="btn btn-secondary btn-block" onclick="event.stopPropagation(); applyTemplate('${template.id}')">
                    Применить
                </button>
                <button class="btn btn-secondary btn-block" onclick="event.stopPropagation(); duplicateTemplate('${template.id}')">
                    Дублировать
                </button>
                <button class="btn btn-secondary btn-block" onclick="event.stopPropagation(); exportTemplate('${template.id}')">
                    Экспорт
                </button>
                ${!template.is_default ? `
                <button class="btn btn-danger btn-block" onclick="event.stopPropagation(); deleteTemplate('${template.id}')">
                    Удалить
                </button>
                ` : ''}
            </div>
        </div>
    `).join('');
}

async function createNewTemplate() {
    currentTemplateId = null;
    document.getElementById('templateName').value = 'Новый шаблон';
    document.getElementById('templateSettingsJson').value = JSON.stringify({
        aspect_ratio: "9:16",
        quality: "1080p",
        codec: "libx264"
    }, null, 2);
    document.getElementById('templatePromptsJson').value = JSON.stringify({
        stage_1_writer: "",
        stage_2_scenes: ""
    }, null, 2);
    
    closeTemplateManager();
    openTemplateEditor();
}

async function applyTemplate(templateId) {
    try {
        showLoading();
        const response = await fetch(`/api/templates/${templateId}/apply`, {
            method: 'POST'
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            showNotification('Шаблон применен', 'success');
            await loadSettings();
        } else {
            showNotification('Ошибка применения шаблона', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Error applying template:', error);
        showNotification('Ошибка применения шаблона', 'error');
    }
}

async function duplicateTemplate(templateId) {
    try {
        showLoading();
        const response = await fetch(`/api/templates/${templateId}/duplicate`, {
            method: 'POST'
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            showNotification('Шаблон дублирован', 'success');
            await loadTemplates();
        } else {
            showNotification('Ошибка дублирования', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Error duplicating template:', error);
        showNotification('Ошибка дублирования шаблона', 'error');
    }
}

async function deleteTemplate(templateId) {
    if (!confirm('Удалить этот шаблон?')) return;
    
    try {
        showLoading();
        const response = await fetch(`/api/templates/${templateId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            showNotification('Шаблон удален', 'success');
            await loadTemplates();
        } else {
            showNotification('Ошибка удаления', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Error deleting template:', error);
        showNotification('Ошибка удаления шаблона', 'error');
    }
}

async function exportTemplate(templateId) {
    try {
        showLoading();
        const response = await fetch(`/api/templates/${templateId}/export`, {
            method: 'POST'
        });
        
        const data = await response.json();
        hideLoading();
        
        if (data) {
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `template_${templateId}.json`;
            a.click();
            URL.revokeObjectURL(url);
            showNotification('Шаблон экспортирован', 'success');
        }
    } catch (error) {
        hideLoading();
        console.error('Error exporting template:', error);
        showNotification('Ошибка экспорта шаблона', 'error');
    }
}

async function importTemplate() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        try {
            showLoading();
            const text = await file.text();
            const data = JSON.parse(text);
            
            const response = await fetch('/api/templates/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            hideLoading();
            
            if (result.success) {
                showNotification('Шаблон импортирован', 'success');
                await loadTemplates();
            } else {
                showNotification('Ошибка импорта', 'error');
            }
        } catch (error) {
            hideLoading();
            console.error('Error importing template:', error);
            showNotification('Ошибка импорта шаблона', 'error');
        }
    };
    input.click();
}

/* ═══════════════════════════════════════════════════════════════
   TEMPLATE EDITOR
   ═══════════════════════════════════════════════════════════════ */
async function openTemplateEditor() {
    const modal = document.getElementById('templateEditorModal');
    modal.classList.add('active');
}

function closeTemplateEditor() {
    const modal = document.getElementById('templateEditorModal');
    modal.classList.remove('active');
    currentTemplateId = null;
}

async function editTemplate(templateId) {
    try {
        showLoading();
        const response = await fetch(`/api/templates/${templateId}`);
        const template = await response.json();
        hideLoading();
        
        currentTemplateId = templateId;
        document.getElementById('templateName').value = template.name;
        document.getElementById('templateSettingsJson').value = template.settings_json || '{}';
        document.getElementById('templatePromptsJson').value = template.prompts_json || '{}';
        
        closeTemplateManager();
        openTemplateEditor();
        previewTemplate();
    } catch (error) {
        hideLoading();
        console.error('Error loading template:', error);
        showNotification('Ошибка загрузки шаблона', 'error');
    }
}

function switchEditorTab(tab) {
    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.editor-tab-content');
    
    tabs.forEach(t => t.classList.remove('active'));
    contents.forEach(c => c.style.display = 'none');
    
    if (tab === 'settings') {
        document.querySelector('.tab-btn:nth-child(1)').classList.add('active');
        document.getElementById('settingsTab').style.display = 'block';
    } else if (tab === 'prompts') {
        document.querySelector('.tab-btn:nth-child(2)').classList.add('active');
        document.getElementById('promptsTab').style.display = 'block';
    }
}

async function saveTemplate() {
    const name = document.getElementById('templateName').value.trim();
    const settingsJson = document.getElementById('templateSettingsJson').value;
    const promptsJson = document.getElementById('templatePromptsJson').value;
    
    if (!name) {
        showNotification('Введите название шаблона', 'warning');
        return;
    }
    
    // Validate JSON
    try {
        JSON.parse(settingsJson);
        JSON.parse(promptsJson);
    } catch (error) {
        showNotification('Ошибка в JSON: ' + error.message, 'error');
        return;
    }
    
    const data = {
        name: name,
        settings_json: settingsJson,
        prompts_json: promptsJson
    };
    
    try {
        showLoading();
        let response;
        
        if (currentTemplateId) {
            // Update existing template
            response = await fetch(`/api/templates/${currentTemplateId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        } else {
            // Create new template
            response = await fetch('/api/templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        }
        
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            showNotification('Шаблон сохранен', 'success');
            if (result.template_id) {
                currentTemplateId = result.template_id;
            }
            await loadTemplates();
        } else {
            showNotification('Ошибка сохранения', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Error saving template:', error);
        showNotification('Ошибка сохранения шаблона', 'error');
    }
}

function previewTemplate() {
    const settingsJson = document.getElementById('templateSettingsJson').value;
    const promptsJson = document.getElementById('templatePromptsJson').value;
    const iframe = document.getElementById('templatePreviewFrame');
    
    try {
        const settings = JSON.parse(settingsJson);
        const prompts = JSON.parse(promptsJson);
        
        const html = `
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {
                        font-family: 'Syne', sans-serif;
                        background: #0d0d16;
                        color: #e2e8f0;
                        padding: 20px;
                        font-size: 13px;
                        line-height: 1.6;
                    }
                    .section {
                        margin-bottom: 20px;
                        padding: 16px;
                        background: rgba(124, 58, 237, 0.05);
                        border: 1px solid rgba(124, 58, 237, 0.2);
                        border-radius: 8px;
                    }
                    .section-title {
                        font-size: 10px;
                        font-weight: 600;
                        text-transform: uppercase;
                        letter-spacing: 0.1em;
                        color: #7c3aed;
                        margin-bottom: 12px;
                    }
                    .field {
                        display: flex;
                        justify-content: space-between;
                        padding: 6px 0;
                        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                    }
                    .field:last-child {
                        border-bottom: none;
                    }
                    .label {
                        color: #64748b;
                        font-size: 12px;
                    }
                    .value {
                        color: #e2e8f0;
                        font-weight: 500;
                    }
                    .prompt-preview {
                        font-family: 'JetBrains Mono', monospace;
                        font-size: 11px;
                        white-space: pre-wrap;
                        max-height: 150px;
                        overflow-y: auto;
                        background: rgba(0, 0, 0, 0.3);
                        padding: 10px;
                        border-radius: 6px;
                    }
                </style>
            </head>
            <body>
                <div class="section">
                    <div class="section-title">Settings</div>
                    ${Object.entries(settings).map(([key, value]) => `
                        <div class="field">
                            <span class="label">${key}</span>
                            <span class="value">${value}</span>
                        </div>
                    `).join('')}
                </div>
                
                <div class="section">
                    <div class="section-title">Prompts</div>
                    ${Object.entries(prompts).map(([key, value]) => `
                        <div style="margin-bottom: 12px;">
                            <div class="label" style="margin-bottom: 6px;">${key}</div>
                            <div class="prompt-preview">${value || '(пусто)'}</div>
                        </div>
                    `).join('')}
                </div>
            </body>
            </html>
        `;
        
        iframe.srcdoc = html;
    } catch (error) {
        iframe.srcdoc = `
            <html>
            <body style="font-family: sans-serif; padding: 20px; color: #ef4444;">
                <h3>Ошибка предпросмотра</h3>
                <p>${error.message}</p>
            </body>
            </html>
        `;
    }
}

/* ═══════════════════════════════════════════════════════════════
   EPISODES VIEWER
   ═══════════════════════════════════════════════════════════════ */
async function openEpisodes() {
    const modal = document.getElementById('episodesModal');
    modal.classList.add('active');
    
    try {
        showLoading();
        const response = await fetch('/episodes');
        const data = await response.json();
        hideLoading();
        
        if (data.error) {
            document.getElementById('episodesContent').innerHTML = `
                <p style="text-align: center; color: var(--muted); padding: 40px;">
                    ${escapeHtml(data.error)}
                </p>
            `;
            return;
        }
        
        renderEpisodes(data);
    } catch (error) {
        hideLoading();
        console.error('Error loading episodes:', error);
        showNotification('Ошибка загрузки эпизодов', 'error');
    }
}

function closeEpisodes() {
    const modal = document.getElementById('episodesModal');
    modal.classList.remove('active');
}

function renderEpisodes(data) {
    const container = document.getElementById('episodesContent');
    let html = '';
    
    // Stage 1 content
    if (data.master_story || data.episodes_raw || data.episodes_final) {
        html += '<div class="episodes-tabs" id="stage1Tabs">';
        
        if (data.master_story) {
            html += '<button class="episode-tab active" onclick="showEpisodeContent(\'master_story\')">Master Story</button>';
        }
        if (data.episodes_raw) {
            html += '<button class="episode-tab" onclick="showEpisodeContent(\'episodes_raw\')">Episodes Raw</button>';
        }
        if (data.episodes_final) {
            html += '<button class="episode-tab" onclick="showEpisodeContent(\'episodes_final\')">Episodes Final</button>';
        }
        
        html += '</div>';
        html += '<div id="stage1Content" class="episode-content"></div>';
    }
    
    // Stage 2 content
    if (data.stage_2) {
        html += '<div class="episodes-tabs" id="stage2Tabs" style="margin-top: 32px;">';
        
        Object.keys(data.stage_2).forEach((episodeKey, index) => {
            const isActive = index === 0 ? 'active' : '';
            html += `<button class="episode-tab ${isActive}" onclick="showStage2Episode('${episodeKey}')">${episodeKey}</button>`;
        });
        
        html += '</div>';
        html += '<div id="stage2Content" class="episode-content"></div>';
    }
    
    container.innerHTML = html;
    
    // Store data globally for access
    window.episodesData = data;
    
    // Show first content
    if (data.master_story) {
        showEpisodeContent('master_story');
    }
    if (data.stage_2) {
        const firstEpisode = Object.keys(data.stage_2)[0];
        showStage2Episode(firstEpisode);
    }
}

function showEpisodeContent(type) {
    const tabs = document.querySelectorAll('#stage1Tabs .episode-tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    event.target.classList.add('active');
    
    const content = document.getElementById('stage1Content');
    const data = window.episodesData;
    
    if (type === 'master_story') {
        content.textContent = data.master_story;
    } else if (type === 'episodes_raw') {
        content.textContent = JSON.stringify(data.episodes_raw, null, 2);
    } else if (type === 'episodes_final') {
        content.textContent = JSON.stringify(data.episodes_final, null, 2);
    }
}

function showStage2Episode(episodeKey) {
    const tabs = document.querySelectorAll('#stage2Tabs .episode-tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    event.target.classList.add('active');
    
    const content = document.getElementById('stage2Content');
    content.textContent = window.episodesData.stage_2[episodeKey];
}

/* ═══════════════════════════════════════════════════════════════
   PROMPT EDITOR
   ═══════════════════════════════════════════════════════════════ */
async function openPromptEditor() {
    const modal = document.getElementById('promptEditorModal');
    modal.classList.add('active');
    
    try {
        const response = await fetch('/settings');
        const settings = await response.json();
        
        if (settings.prompts) {
            document.getElementById('stage1WriterPrompt').value = settings.prompts.stage_1_writer || '';
            document.getElementById('stage2ScenesPrompt').value = settings.prompts.stage_2_scenes || '';
        }
    } catch (error) {
        console.error('Error loading prompts:', error);
    }
}

function closePromptEditor() {
    const modal = document.getElementById('promptEditorModal');
    modal.classList.remove('active');
}

async function savePrompts() {
    const data = {
        stage_1_writer: document.getElementById('stage1WriterPrompt').value,
        stage_2_scenes: document.getElementById('stage2ScenesPrompt').value
    };
    
    try {
        showLoading();
        const response = await fetch('/save-prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.message) {
            showNotification('Промпты сохранены', 'success');
        } else {
            showNotification(result.error || 'Ошибка сохранения', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Error saving prompts:', error);
        showNotification('Ошибка сохранения промптов', 'error');
    }
}

/* ═══════════════════════════════════════════════════════════════
   UTILITY FUNCTIONS
   ═══════════════════════════════════════════════════════════════ */
function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

function showNotification(message, type = 'info') {
    // Simple notification - можно заменить на более красивую библиотеку
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#06b6d4'
    };
    
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 24px;
        right: 24px;
        background: ${colors[type]};
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        z-index: 3000;
        font-family: var(--font-head);
        font-weight: 600;
        font-size: 14px;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return '—';
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

/* ═══════════════════════════════════════════════════════════════
   MODAL CLOSE ON OUTSIDE CLICK
   ═══════════════════════════════════════════════════════════════ */
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('active');
    }
});