import os
import json
import requests
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def run_colab_scenes_final():
    BASE_URL = "https://ec20-34-141-243-34.ngrok-free.app" # ОБНОВИ ССЫЛКУ
    TARGET_URL = f"{BASE_URL}/api/generate"
    
    proxies = {"http": "http://127.0.0.1:10809", "https": "http://127.0.0.1:10809"}
    headers = {"ngrok-skip-browser-warning": "1", "User-Agent": "Mozilla/5.0"}

    # МАСТЕР-СТИЛЬ: заменяем фотореализм на художественный стиль
    # МАСТЕР-СТИЛЬ: Усиливаем акцент на рисованности (используем веса (word:1.4))


    with open("data/visual_config.json", "r", encoding="utf-8") as f:
        v_config = json.load(f)
    with open("data/2_production_map.json", "r", encoding="utf-8") as f:
        p_map = json.load(f)

    # Вырезаем "Photorealistic style" из твоего конфига, если он там есть
    original_style = v_config.get("visual_style", "").replace("Photorealistic style,", "")
    chars = v_config.get("characters", {})

    scenes = p_map.get("production_scenes", [])
    os.makedirs("outputs/scenes", exist_ok=True)

    print(f"🎬 Отрисовка сцен в формате 16:9 (Art Style)")

        # 1. МАСТЕР-НАСТРОЙКИ (вынеси их перед циклом)
    # Усиленный стиль: двойные скобки ((...)) дают множитель внимания нейросети
        # 1. ОБНОВЛЕННЫЙ МАСТЕР-СТИЛЬ (Визуальная новелла / Аниме-арт)
    # 2D, cel shaded — это теги для классической заливки как в мультфильмах/новеллах
    # soft shadows, detailed background — добавят глубины
    ART_STYLE = ("((visual novel style)), (2D art), (cel shaded), detailed digital painting, "
                 "soft volumetric lighting, masterpiece, clean lines, vivid colors, "
                 "high-quality anime background")
    
    # 2. ОБНОВЛЕННЫЙ НЕГАТИВ (удаляем 'flat colors', чтобы не было плоским)
    SCENE_NEG = ("photorealistic, photography, 3d render, low quality, blurry, "
                 "sketch, coloring book, black and white, monochrome, rough lines, "
                 "bad anatomy, deformed, text, watermark")

    for i, scene in enumerate(scenes):
        visual_prompt = scene.get("visual_prompt", "")
        
        # 3. КОРРЕКТИРОВКА ВЕСОВ ПЕРСОНАЖЕЙ
        # Поднимаем вес персонажа чуть выше (до 0.85), чтобы он не был просто контуром
        main_1_raw = chars.get("The_Protagonist", "")[:150]
        main_2_raw = chars.get("The_Relatives", "")[:150]
        
        main_1_fixed = f"(subject: {main_1_raw} :0.85)"
        main_2_fixed = f"(characters: {main_2_raw} :0.85)"
        
        clean_action = visual_prompt.replace("[STYLE]", "").strip()
        
        # Сборка: Стиль + Действие + Персонажи + Локация
        final_prompt = f"{ART_STYLE}, {clean_action}, {main_1_fixed}, {main_2_fixed}, {original_style}"

        print(f"\n📸 Сцена {i+1}...")
        
        payload = {
            "prompt": final_prompt,
            "negative_prompt": SCENE_NEG,
            "steps": 30, 
            "guidance": 10.0,  # Снижаем до 10.0, чтобы заливка была мягче и естественнее
            "image": None
        }



        try:
            response = requests.post(TARGET_URL, json=payload, headers=headers, 
                                     proxies=proxies, timeout=300, verify=False)

            if response.status_code == 200:
                with open(f"outputs/scenes/scene_{i+1}.png", "wb") as f:
                    f.write(response.content)
                print(f"✅ Готово! (16:9)")
            else:
                print(f"❌ Ошибка: {response.text[:200]}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        
        time.sleep(2)

if __name__ == "__main__":
    run_colab_scenes_final()
