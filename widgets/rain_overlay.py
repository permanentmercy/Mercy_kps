from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import Qt, QTimer
from dataclasses import dataclass
from core.events import events
from core.config_manager import ConfigManager

@dataclass
class RainBar:
    key_code: str
    cx: int
    width: int
    bottom_y: float
    height: float
    color: tuple
    corner_radius: int = 8
    border_width: int = 2
    growing: bool = True
    opacity: float = 1.0

class RainOverlay(QWidget):
    def __init__(self, rain_layer=0, parent=None):
        super().__init__(parent)
        self.rain_layer = rain_layer
        # It should cover the whole DisplayWindow, but sit behind KeyWidgets
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._bars = []
        self._cfg = ConfigManager.load()
        self._rain_cfg = self._cfg.get("rain", {})
        
        # Subscribe to events
        events.key_pressed.connect(self._on_key_press)
        events.key_released.connect(self._on_key_release)
        
        # Timer for 60fps animation
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        if self._rain_cfg.get("enabled", True):
            self._timer.start(16) # ~60fps

    def reload_config(self):
        self._cfg = ConfigManager.load()
        self._rain_cfg = self._cfg.get("rain", {})
        if self._rain_cfg.get("enabled", True):
            if not self._timer.isActive():
                self._timer.start(16)
        else:
            self._timer.stop()
            self._bars.clear()
            self.update()

    def _get_key_config_by_code(self, key_code):
        for k in self._cfg.get("keys", []):
            if k.get("key_code", "").lower() == key_code:
                return k
        return None

    def _on_key_press(self, key_code):
        if not self._rain_cfg.get("enabled", True): return
        
        key_cfg = self._get_key_config_by_code(key_code)
        if not key_cfg: return
        if key_cfg.get("key_type", "normal") != "normal": return
        
        # Only draw key rain in this overlay if the key's rain_layer matches ours
        if key_cfg.get("rain_layer", 0) != self.rain_layer:
            return
        
        # Avoid duplicate growing bars for same key
        for b in self._bars:
            if b.key_code == key_code and b.growing:
                return
                
        color = key_cfg.get("rain_color", [108, 99, 255, 160])
        if not self._rain_cfg.get("color_link", True):
            # Fallback to a default color or global rain color if needed
            color = [255, 255, 255, 160]
            
        key_spacing = self._cfg.get("display_window", {}).get("key_spacing", 0)
        grid_size = self._cfg.get("display_window", {}).get("grid_size", 2)
        kw_w = key_cfg.get('display_width', key_cfg.get('width', 60))
        kw_h = key_cfg.get('display_height', key_cfg.get('height', 60))
        if grid_size == 0:
            pixel_x = float(key_cfg.get('x', 0))
            pixel_y = float(key_cfg.get('y', 0))
        else:
            pixel_x = float(key_cfg.get('x', 0) * (60 / grid_size))
            pixel_y = float(key_cfg.get('y', 0) * (60 / grid_size))
        mapped_x = int(pixel_x + (pixel_x / 60.0) * key_spacing)
        mapped_y = int(pixel_y + (pixel_y / 60.0) * key_spacing)

        rain_offset_y = key_cfg.get("rain_offset_y", 0)
        rain_thickness = key_cfg.get("rain_thickness", 0)

        bar = RainBar(
            key_code=key_code,
            cx=mapped_x + kw_w // 2,
            width=max(1, kw_w + rain_thickness),
            bottom_y=mapped_y + kw_h + rain_offset_y,
            height=0,
            color=color,
            corner_radius=key_cfg.get("corner_radius", 10),
            border_width=key_cfg.get("border_width", 2)
        )
        self._bars.append(bar)

    def _on_key_release(self, key_code):
        for bar in self._bars:
            if bar.key_code == key_code and bar.growing:
                bar.growing = False

    def _tick(self):
        needs_update = len(self._bars) > 0
        speed = self._rain_cfg.get("speed_up", 6)
        grow_speed = self._rain_cfg.get("grow_speed", 6)
        fade_speed = self._rain_cfg.get("fade_speed", 0.018)
        
        for bar in self._bars[:]:
            if bar.growing:
                # Grow downward at constant speed
                bar.height += grow_speed
            else:
                # Rise at constant uniform speed (no acceleration)
                bar.bottom_y -= speed
                bar.opacity -= fade_speed
                if bar.opacity <= 0:
                    self._bars.remove(bar)
                    
        if needs_update:
            self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for bar in self._bars:
            color = QColor(*bar.color[:3], int(bar.color[3] * bar.opacity))
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            
            border_w = bar.border_width
            r = max(0, bar.corner_radius - border_w)
            
            draw_w = max(1, bar.width - 2 * border_w)
            draw_x = int(bar.cx - bar.width / 2 + border_w)
            
            draw_bottom_y = bar.bottom_y - border_w
            draw_top_y = draw_bottom_y - bar.height
            draw_h = max(0, int(bar.height))
            
            p.drawRoundedRect(
                draw_x, 
                int(draw_top_y), 
                draw_w, 
                draw_h, 
                r, r
            )
