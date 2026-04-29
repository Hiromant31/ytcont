import os
import json
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def run_stage_3_draw_characters():
    BASE_URL = "https://39f6-34-83-27-186.ngrok-free.app"
    TARGET_URL = f"{BASE_URL}/api/generate"
    
    proxies = {"http": "http://127.0.0.1:10809", "https": "http://127.0.0.1:10809"}
    headers = {"ngrok-skip-browser-warning": "1", "User-Agent": "Mozilla/5.0"}

    # --- НАСТРОЙКИ МАСТЕР-ПРОМПТОВ ---
    # Для персонажей
    CHAR_MASTER = "waist-up portrait, centered, looking at camera, single person, solo"
    CHAR_NEG = "split screen, multi view, grid, character sheet, multiple people, lowres, bad anatomy"

    # Для сцен (пример на будущее)
    SCENE_MASTER = "cinematic landscape, wide angle, highly detailed, 8k resolution"
    SCENE_NEG = "person, human, character, deformed, text, watermark"

    # --- ЗАГРУЗКА ---
    with open("data/visual_config.json", "r", encoding="utf-8") as f:
        config_data = json.load(f)

    characters = config_data.get("characters", {})
    style = config_data.get("visual_style", "")

    for name, description in characters.items():
        print(f"🎨 Генерирую: {name}...")
        
        # Собираем промпт здесь
        final_prompt = f"{description}, {CHAR_MASTER}, style of {style}"
        
        payload = {
            "prompt": final_prompt,
            "negative_prompt": CHAR_NEG, # Отправляем негативку
            "steps": 35,                 # Можно менять качество на лету
            "guidance": 8.5,             # Насколько строго следовать промпту
            "image": None
        }

        try:
            response = requests.post(TARGET_URL, json=payload, headers=headers, 
                                     proxies=proxies, verify=False, timeout=300)

            if response.status_code == 200:
                with open(f"outputs/references/{name}.png", "wb") as f:
                    f.write(response.content)
                print(f"✅ Готово!")
            else:
                print(f"❌ Ошибка: {response.text}")

        except Exception as e:
            print(f"❌ Ошибка связи: {e}")

if __name__ == "__main__":
    run_stage_3_draw_characters()
