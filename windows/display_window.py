import ctypes
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QMouseEvent
from core.config_manager import ConfigManager
from core.events import events
from widgets.key_widget import KeyWidget
from widgets.rain_overlay import RainOverlay

# Windows API constants
_GWL_EXSTYLE       = -20
_WS_EX_NOACTIVATE  = 0x08000000   # Don't steal focus when clicked
_WS_EX_TOOLWINDOW  = 0x00000080   # NOTE: DO NOT set this on DisplayWindow — OBS skips tool windows
_WS_EX_APPWINDOW   = 0x00040000
_GWL_HWNDPARENT    = -8

def _create_hidden_owner() -> int:
    """Create an invisible WS_EX_TOOLWINDOW helper window.
    Setting it as the 'owner' of DisplayWindow causes Windows Shell to
    suppress DisplayWindow's taskbar button — without marking DisplayWindow
    itself as a tool window, so OBS Window Capture can still see it."""
    try:
        hwnd = ctypes.windll.user32.CreateWindowExW(
            _WS_EX_TOOLWINDOW,   # dwExStyle  — the OWNER is a tool window
            "STATIC",            # lpClassName
            None,                # lpWindowName
            0,                   # dwStyle (WS_OVERLAPPED)
            0, 0, 0, 0,          # x, y, w, h
            0, 0, 0, None        # parent, menu, hInstance, lpParam
        )
        return hwnd
    except Exception:
        return 0

class DisplayWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = ConfigManager.load()
        self._cfg = self._config.get("display_window", {})
        
        # NOTE: Do NOT use Qt.WindowType.Tool here.
        # Tool windows are invisible to OBS window capture.
        # We hide from taskbar manually via WinAPI after the window is created.
        self.setWindowTitle("MercyKPS Overlay")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Map the initial size based on editor_key_size
        base_w = self._cfg.get('width', 600)
        base_h = self._cfg.get('height', 400)
        editor_key_size = self._cfg.get("editor_key_size", 60)
        if editor_key_size <= 0:
            editor_key_size = 60
        scale_factor = 60.0 / editor_key_size
        
        mapped_win_w = int(base_w * scale_factor)
        mapped_win_h = int(base_h * scale_factor)
        
        x = self._cfg.get('x', 100)
        y = self._cfg.get('y', 100)
        
        # Check if current coordinates intersect with any connected screen
        from PyQt6.QtGui import QGuiApplication
        from PyQt6.QtCore import QRect
        win_rect = QRect(x, y, mapped_win_w, mapped_win_h)
        intersects_any = False
        screens = QGuiApplication.screens()
        for screen in screens:
            if screen.geometry().intersects(win_rect):
                intersects_any = True
                break
                
        if not intersects_any and screens:
            # Snap to first screen's geometry
            primary_geo = screens[0].geometry()
            x = primary_geo.x() + 100
            y = primary_geo.y() + 100
            self._cfg['x'] = x
            self._cfg['y'] = y
            self._cfg['monitor'] = 0
            ConfigManager.save()
            
        self.setGeometry(x, y, mapped_win_w, mapped_win_h)
        
        self.rain_overlays = {}
        self._key_widgets = []
        self._init_keys()
        
        # Connect to config change events to update positions dynamically
        events.config_changed.connect(self._on_config_changed)

    def showEvent(self, event):
        """After first show, assign a hidden owner window so Windows Shell
        suppresses our taskbar button, while keeping us fully visible to
        OBS Window Capture (which requires we NOT have WS_EX_TOOLWINDOW)."""
        super().showEvent(event)
        if not getattr(self, '_owner_hwnd_set', False):
            self._owner_hwnd_set = True
            try:
                hwnd = int(self.winId())
                owner = _create_hidden_owner()
                if owner:
                    self._hidden_owner = owner  # keep reference so GC won't destroy it
                    # Set owner → Shell hides our taskbar button automatically
                    ctypes.windll.user32.SetWindowLongPtrW(hwnd, _GWL_HWNDPARENT, owner)
                    # Also add WS_EX_NOACTIVATE so clicking keys doesn't steal game focus
                    ex = ctypes.windll.user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
                    ctypes.windll.user32.SetWindowLongW(hwnd, _GWL_EXSTYLE,
                                                        ex | _WS_EX_NOACTIVATE)
            except Exception:
                pass

    def resizeEvent(self, e):
        super().resizeEvent(e)
        for overlay in self.rain_overlays.values():
            overlay.resize(self.size())

    def _init_keys(self):
        self._config = ConfigManager.load()
        for w in self._key_widgets:
            w.setParent(None)
            w.deleteLater()
        self._key_widgets.clear()
        
        # Clear old rain overlays
        for overlay in self.rain_overlays.values():
            overlay.setParent(None)
            overlay.deleteLater()
        self.rain_overlays.clear()
        
        grid_size = self._config.get("display_window", {}).get("grid_size", 2)
        key_spacing = self._config.get("display_window", {}).get("key_spacing", 0)
        
        # Determine all unique rain layers needed
        rain_layers = set()
        for key_cfg in self._config.get("keys", []):
            rain_layers.add(key_cfg.get("rain_layer", 0))
            
        # Create a RainOverlay for each unique rain layer
        for r_layer in rain_layers:
            overlay = RainOverlay(r_layer, self)
            overlay.resize(self.size())
            overlay.show()
            self.rain_overlays[r_layer] = overlay
            
        # Create key widgets
        for key_cfg in self._config.get("keys", []):
            kw = KeyWidget(key_cfg, is_preview=False, grid_size=grid_size, parent=self)
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
            kw.setGeometry(
                mapped_x,
                mapped_y,
                kw_w,
                kw_h
            )
            kw.show()
            self._key_widgets.append(kw)
            
        self._update_z_order()

    def _update_z_order(self):
        items = []
        for r_layer, overlay in self.rain_overlays.items():
            items.append((r_layer, 1, overlay))
        for kw in self._key_widgets:
            k_layer = kw.cfg.get("key_layer", 0)
            items.append((k_layer, 0, kw))
            
        # Sort in descending order: lower layer number is raised last (on top)
        # Within the same layer, we draw rain (1) before key (0) so key is on top of rain of same layer.
        items.sort(key=lambda x: (x[0], x[1]), reverse=True)
        for layer, is_rain, widget in items:
            widget.raise_()

    def _on_config_changed(self, new_config):
        self._config = new_config
        self._cfg = self._config.get("display_window", {})
        
        # Update layout window size if changed
        base_w = self._cfg.get('width', 600)
        base_h = self._cfg.get('height', 400)
        editor_key_size = self._cfg.get("editor_key_size", 60)
        if editor_key_size <= 0:
            editor_key_size = 60
        scale_factor = 60.0 / editor_key_size
        
        mapped_win_w = int(base_w * scale_factor)
        mapped_win_h = int(base_h * scale_factor)
        self.resize(mapped_win_w, mapped_win_h)
        
        # Determine if key widgets need reconstruction (i.e. count, IDs or layers changed)
        current_ids = {kw.key_id for kw in self._key_widgets}
        new_ids = {k.get("id") for k in self._config.get("keys", [])}
        
        current_key_layers = {kw.cfg.get("key_layer", 0) for kw in self._key_widgets}
        new_key_layers = {k.get("key_layer", 0) for k in self._config.get("keys", [])}
        
        current_rain_layers = {kw.cfg.get("rain_layer", 0) for kw in self._key_widgets}
        new_rain_layers = {k.get("rain_layer", 0) for k in self._config.get("keys", [])}
        
        if (current_ids != new_ids or 
            current_key_layers != new_key_layers or 
            current_rain_layers != new_rain_layers or
            set(self.rain_overlays.keys()) != new_rain_layers):
            self._init_keys()
        else:
            # Just update positions and properties of existing widgets
            for kw in self._key_widgets:
                for key_cfg in self._config.get("keys", []):
                    if kw.key_id == key_cfg.get("id"):
                        kw.cfg = key_cfg
                        kw.key_code = key_cfg.get("key_code", "").lower()
                        grid_size = self._config.get("display_window", {}).get("grid_size", 2)
                        kw.grid_size = grid_size
                        kw_w = key_cfg.get('display_width', key_cfg.get('width', 60))
                        kw_h = key_cfg.get('display_height', key_cfg.get('height', 60))
                        key_spacing = self._config.get("display_window", {}).get("key_spacing", 0)
                        if grid_size == 0:
                            pixel_x = float(key_cfg.get('x', 0))
                            pixel_y = float(key_cfg.get('y', 0))
                        else:
                            pixel_x = float(key_cfg.get('x', 0) * (60 / grid_size))
                            pixel_y = float(key_cfg.get('y', 0) * (60 / grid_size))
                        mapped_x = int(pixel_x + (pixel_x / 60.0) * key_spacing)
                        mapped_y = int(pixel_y + (pixel_y / 60.0) * key_spacing)
                        kw.setGeometry(
                            mapped_x,
                            mapped_y,
                            kw_w,
                            kw_h
                        )
                        kw.update()
            
            # Apply dynamic z-order update
            self._update_z_order()
        
        # Notify rain overlays to reload its config
        for overlay in self.rain_overlays.values():
            overlay.reload_config()
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        # Only draw background color if specified (e.g. for testing)
        # Typically the HUD background is transparent (Alpha = 0)
        bg = self._cfg.get("background_color", [0, 0, 0, 0])
        if bg[3] > 0:
            p.fillRect(self.rect(), QColor(*bg))

    # Mouse Events for dragging the entire window from blank areas
    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start = e.globalPosition().toPoint()
            self._win_start = self.pos()
            e.accept()

    def mouseMoveEvent(self, e: QMouseEvent):
        # Always repaint on mouse move to clear any cursor ghosting artifacts
        # that appear on transparent/frameless windows on Windows.
        self.update()
        if e.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_start'):
            delta = e.globalPosition().toPoint() - self._drag_start
            new_pos = self._win_start + delta
            self.move(new_pos)
            self._cfg['x'] = new_pos.x()
            self._cfg['y'] = new_pos.y()
            ConfigManager.save()
            e.accept()
