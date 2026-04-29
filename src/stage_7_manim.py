import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from manim import *

# --- НАСТРОЙКИ РАЗРЕШЕНИЯ (ВЕРТИКАЛЬНОЕ 240p) ---
config.pixel_height = 426
config.pixel_width = 240
config.frame_height = 16.0  # Увеличиваем логическую высоту сцены
config.frame_width = config.frame_height * (config.pixel_width / config.pixel_height)
config.frame_rate = 24

class FinalEpisodeScene(Scene):
    """Сцена финального эпизода (Вертикальная, 240p)"""
    
    def construct(self):
        # Загрузка данных
        manifest = self._load_json("data/3_assembly_manifest.json")
        if manifest is None:
            self._show_error("Манифест не найден")
            return

        ep_name = next(iter(manifest))
        scenes_data = manifest[ep_name]

        subtitle_path = Path("outputs/subtitles") / f"{ep_name}.json"
        episode_subs = self._load_json(subtitle_path)
        if episode_subs is None:
            self._show_error(f"Субтитры {subtitle_path} не найдены")
            return

        for scene_data in scenes_data:
            self._process_scene(scene_data, episode_subs)

    def _load_json(self, path: str | Path) -> Optional[Dict]:
        path = Path(path)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None

    def _show_error(self, message: str):
        error_text = Text(message, color=RED, font_size=20)
        self.add(error_text)
        self.wait(2)

    def _create_image(self, img_path: str) -> Mobject:
        """Создаёт изображение, подогнанное под ВЕРТИКАЛЬНЫЙ экран."""
        if Path(img_path).exists():
            img = ImageMobject(img_path)
            # В вертикальном видео мы заполняем экран по ВЫСОТЕ.
            # Если картинка горизонтальная, она будет обрезана по бокам (Crop-to-fill)
            img.height = config.frame_height
            # Если нужно, чтобы картинка была полностью видна с черными полями, 
            # используйте img.width = config.frame_width и уберите строку выше.
            return img
        else:
            return Rectangle(
                width=config.frame_width,
                height=config.frame_height,
                fill_color=BLACK, fill_opacity=1
            )

    def _create_animation_updater(self, mobject: Mobject, anim_type: str, duration: float):
        if duration <= 0: return

        # Коэффициенты для вертикального видео чуть меньше, чтобы не было "дерганий" в низком разрешении
        if anim_type == "zoom_in":
            zoom_speed = 0.10 / duration
            mobject.add_updater(lambda m, dt: m.scale(1 + zoom_speed * dt))
        
        elif anim_type == "zoom_out":
            zoom_speed = 0.10 / duration
            mobject.scale(1.10)
            mobject.add_updater(lambda m, dt: m.scale(1 - zoom_speed * dt))
        
        elif anim_type == "pan_left":
            pan_speed = 1.0 / duration
            mobject.shift(RIGHT * 0.5)
            mobject.add_updater(lambda m, dt: m.shift(LEFT * pan_speed * dt))
        
        elif anim_type == "pan_right":
            pan_speed = 1.0 / duration
            mobject.shift(LEFT * 0.5)
            mobject.add_updater(lambda m, dt: m.shift(RIGHT * pan_speed * dt))

    def _display_subtitles(self, words: List[Dict]) -> float:
        last_time = 0.0
        for word_data in words:
            start_time = word_data["start"]
            end_time = word_data["end"]
            
            wait_duration = start_time - last_time
            if wait_duration > 0:
                self.wait(wait_duration)
                last_time += wait_duration
            
            # В 240p шрифт должен быть жирным и четким
            subtitle = Text(
                word_data["text"],
                font="DejaVu Sans",
                weight=BOLD,
                color=YELLOW
            )
            # Уменьшаем масштаб, так как в вертикальном видео меньше места по ширине
            subtitle.width = config.frame_width * 0.85 
            subtitle.set_stroke(BLACK, width=6, background=True)
            # Позиция чуть выше низа
            subtitle.to_edge(DOWN, buff=2.5)
            
            self.add(subtitle)
            
            word_duration = end_time - start_time
            if word_duration > 0:
                self.wait(word_duration)
                last_time += word_duration
            
            self.remove(subtitle)
        
        return last_time

    def _process_scene(self, scene_data: Dict, episode_subs: Dict):
        scene_id = str(scene_data["scene_id"])
        duration = scene_data["duration"]
        img_path = scene_data["image_path"]
        audio_path = scene_data["audio_path"]
        anim_type = scene_data["animation"]
        
        img = self._create_image(img_path)
        
        if Path(audio_path).exists():
            self.add_sound(audio_path)
        
        self._create_animation_updater(img, anim_type, duration)
        self.add(img)
        
        words = episode_subs.get(scene_id, [])
        last_subtitle_time = self._display_subtitles(words)
        
        remaining_time = duration - last_subtitle_time
        if remaining_time > 0:
            self.wait(remaining_time)
        
        img.clear_updaters()
        self.remove(img)

if __name__ == "__main__":
    # Запуск: manim -pql script.py FinalEpisodeScene
    pass