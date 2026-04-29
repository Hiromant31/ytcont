import threading
import time
import os
import shutil
import traceback

# Импорты твоих этапов
from stage_1_story import run_stage_1
from stage_2_scenes import run_stage_2
from stage_3_draw_characters import run_stage_3_refs
from stage_4_yandex_scenes import run_stage_4_scenes
from stage_5_tts_yandex import run_stage_5_yandex_tts
from stage_5_5_subtitles import run_stage_5_5_subtitles
from stage_6_build_manifest import run_stage_6_manifest
from stage_7_renderer import run_stage_7_render

class VideoProductionManager:
    def __init__(self):
        self.status = "Ожидание"
        self.current_stage_idx = 0
        self.logs = []
        self.is_running = False
        self.stages = [
            ("Сценарий", run_stage_1),
            ("Раскадровка", run_stage_2),
            ("Референсы лиц", run_stage_3_refs),
            ("Генерация кадров", run_stage_4_scenes),
            ("Озвучка", run_stage_5_yandex_tts),
            ("Субтитры", run_stage_5_5_subtitles),
            ("Манифест", run_stage_6_manifest),
            ("Рендеринг", run_stage_7_render),
        ]

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        self.logs.append(formatted_msg)
        print(formatted_msg)

    def save_to_google_drive(self):
        """Копирует все готовые видео из outputs на Google Drive."""
        drive_path = os.getenv("GOOGLE_DRIVE_PATH") # Берем путь из .env
        local_dir = "outputs/final_videos"
        
        if drive_path and os.path.exists(local_dir):
            self.log(f"📂 Синхронизация с Google Drive: {drive_path}...")
            os.makedirs(drive_path, exist_ok=True)
            for file in os.listdir(local_dir):
                if file.endswith(".mp4"):
                    src = os.path.join(local_dir, file)
                    dst = os.path.join(drive_path, f"{int(time.time())}_{file}")
                    shutil.copy2(src, dst)
                    self.log(f"✅ Файл сохранен на Диск: {file}")
        else:
            self.log("⚠️ Путь к Google Drive не настроен или видео не найдены.")

    def run_pipeline(self, start_from=1, custom_idea=None):
        self.is_running = True
        try:
            # Если передана идея из веб-интерфейса, сохраняем её в файл перед стартом
            if custom_idea and custom_idea.strip():
                with open("idea.txt", "w", encoding="utf-8") as f:
                    f.write(custom_idea)
                self.log(f"💡 Получена новая идея: {custom_idea[:50]}...")

            for i in range(start_from - 1, len(self.stages)):
                name, func = self.stages[i]
                self.current_stage_idx = i + 1
                self.status = f"Выполнение: {name}"
                self.log(f"--- СТАРТ ЭТАПА {i+1}: {name} ---")
                
                success = func()
                if success is False: 
                    raise Exception(f"Этап '{name}' завершился с внутренней ошибкой.")
                
                self.log(f"✅ Этап {i+1} завершен успешно.")

            # После всех этапов сохраняем результат
            self.save_to_google_drive()

            self.status = "Завершено"
            self.log("🎉 Пайплайн полностью выполнен!")
        except Exception as e:
            self.status = "Ошибка"
            self.log(f"❌ КРИТИЧЕСКАЯ ОШИБКА на этапе {self.current_stage_idx}: {str(e)}")
            self.log(traceback.format_exc())
        finally:
            self.is_running = False

manager = VideoProductionManager()