import threading
import time
import os
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
        self.current_stage_idx = 0  # 0 - еще не начинали
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

    def run_pipeline(self, start_from=1):
        self.is_running = True
        try:
            # Цикл идет по индексам, начиная с выбранного
            for i in range(start_from - 1, len(self.stages)):
                name, func = self.stages[i]
                self.current_stage_idx = i + 1
                self.status = f"Выполнение: {name}"
                self.log(f"--- СТАРТ ЭТАПА {i+1}: {name} ---")
                
                # Запускаем функцию этапа
                success = func()
                
                if success is False: # Если функция явно вернула False
                    raise Exception(f"Этап '{name}' завершился с внутренней ошибкой.")
                
                self.log(f"✅ Этап {i+1} завершен успешно.")

            self.status = "Завершено"
            self.log("🎉 Пайплайн полностью выполнен!")
        except Exception as e:
            self.status = "Ошибка"
            self.log(f"❌ КРИТИЧЕСКАЯ ОШИБКА на этапе {self.current_stage_idx}: {str(e)}")
            self.log(traceback.format_exc()) # Полный лог ошибки как в консоли
        finally:
            self.is_running = False

manager = VideoProductionManager()