import os
import time
from dotenv import load_dotenv
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import uvicorn
from google import genai

# ================================
# 📦 ENV
# ================================
load_dotenv()

# Проверьте, нужен ли прокси-сервер. Если Gemini не подключается, 
# попробуйте закомментировать эти две строки:
os.environ["HTTP_PROXY"] = "http://127.0.0.1:10809"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10809"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

# ПРОВЕРЬТЕ НАЗВАНИЕ: В настоящее время актуальной моделью является "gemini-2.0-flash-exp" 
# или "gemini-1.5-flash". 3.1, скорее всего, опечатка.
MODEL = "gemini-3.1-flash-lite-preview"

# ================================
# 🌐 FASTAPI
# ================================
app = FastAPI()

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>AI Avito Generator</title>
    <meta charset="utf-8">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f0f0f; color: #fff; padding: 20px; max-width: 800px; margin: auto; }
        textarea, input { width: 100%; margin: 10px 0; padding: 12px; background:#1c1c1c; color:#fff; border:1px solid #333; border-radius: 5px; box-sizing: border-box; }
        button { width: 100%; padding: 15px; background: #ffca28; border: none; cursor: pointer; font-weight:bold; color: #000; font-size: 16px; border-radius: 5px; }
        button:hover { background: #ffd54f; }
        pre { background: #1a1a1a; padding: 15px; white-space: pre-wrap; border-radius:10px; border: 1px solid #444; line-height: 1.5; }
        h1 { color: #ffca28; text-align: center; }
    </style>
</head>
<body>
    <h1>🚀 Генератор объявлений</h1>
    <form method="post">
        <label>Вставь примеры объявлений (5-10 шт):</label>
        <textarea name="ads" rows="8" placeholder="Вставь сюда текст старых объявлений..."></textarea>
        <label>Что продаем сейчас?</label>
        <input name="task" placeholder="Например: Продать iPhone 15 Pro в идеале"/>
        <button type="submit">СГЕНЕРИРОВАТЬ</button>
    </form>
    <hr style="margin: 30px 0; border: 0; border-top: 1px solid #333;">
    <h3>Результат:</h3>
    <pre>%RESULT%</pre>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_PAGE.replace("%RESULT%", "Здесь появится ваше объявление...")

@app.post("/", response_class=HTMLResponse)
def generate(ads: str = Form(...), task: str = Form(...)):
    prompt = f"""
    Ты — эксперт по Авито. Проанализируй стиль этих объявлений:
    {ads}
    
    Создай новое объявление для: {task}. 
    Соблюдай структуру, стиль и призыв к действию из примеров. 
    Верни только текст объявления.
    """
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        result = response.text
    except Exception as e:
        result = f"Ошибка Gemini: {str(e)}"
    
    return HTML_PAGE.replace("%RESULT%", result)

# ================================
# 🚀 ЗАПУСК
# ================================
if __name__ == "__main__":
    print(f"\n" + "="*30)
    print(f"🔥 СЕРВЕР ЗАПУЩЕН")
    print(f"👉 Локальный URL: http://127.0.0.1:8000")
    print(f"👉 Для публичного доступа используйте cloudflared tunnel")
    print(f"="*30 + "\n")

    # 2. Запускаем uvicorn напрямую (без потоков).
    # Это предотвратит закрытие программы.
    uvicorn.run(app, host="127.0.0.1", port=8000)
