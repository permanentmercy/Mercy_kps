from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QMouseEvent
from PyQt6.QtCore import Qt, QRect, QPoint
from widgets.key_widget import KeyWidget
from core.config_manager import ConfigManager

class GridCanvas(QWidget):
    def __init__(self, display_win, parent=None):
        super().__init__(parent)
        self.display_win = display_win
        self._config = ConfigManager.load()
        
        self.setObjectName("GridCanvas")
        self.setStyleSheet("""
            QWidget#GridCanvas {
                background-color: #0b0f19;
                border: 1px solid #333333;
                border-radius: 8px;
            }
        """)
        
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.format_painter_style = None
        
        self._key_widgets = []
        self._selection_start = None
        self._selection_rect = None
        
        self._init_keys()

    def _get_display_size(self):
        dw = self._config.get("display_window", {})
        return dw.get("width", 600), dw.get("height", 400)

    def _get_scale(self):
        disp_w, disp_h = self._get_display_size()
        cw = max(1, self.width())
        ch = max(1, self.height())
        if disp_w <= 0 or disp_h <= 0:
            return 1.0, 1.0
        return cw / disp_w, ch / disp_h

    def mousePressEvent(self, e: QMouseEvent):
        from core.events import events
        events.edit_key_requested.emit("")
        
        if e.button() == Qt.MouseButton.LeftButton:
            # Clear existing selection
            for kw in self._key_widgets:
                kw.is_selected = False
                kw.update()
            
            # Start new selection
            self._selection_start = e.position().toPoint()
            self._selection_rect = QRect()
            self.update()
            
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._selection_start is not None and e.buttons() == Qt.MouseButton.LeftButton:
            # Draw rubber band
            current_pos = e.position().toPoint()
            self._selection_rect = QRect(self._selection_start, current_pos).normalized()
            
            # Select keys intersecting with rubber band
            for kw in self._key_widgets:
                was_selected = kw.is_selected
                is_selected = self._selection_rect.intersects(kw.geometry())
                if was_selected != is_selected:
                    kw.is_selected = is_selected
                    kw.update()
                    
            self.update()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            self._selection_start = None
            self._selection_rect = None
            self.update()
            
            # If format painter is active and Ctrl is not held, apply immediately on selection end
            if getattr(self, 'format_painter_style', None):
                from PyQt6.QtWidgets import QApplication
                if not (QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier):
                    self.apply_format_painter()
        super().mouseReleaseEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key.Key_Control:
            if getattr(self, 'format_painter_style', None):
                self.apply_format_painter()
        super().keyReleaseEvent(e)

    def apply_format_painter(self):
        style = getattr(self, 'format_painter_style', None)
        if not style:
            return
            
        selected_kws = [kw for kw in self._key_widgets if kw.is_selected]
        if not selected_kws:
            return
            
        import copy
        for kw in selected_kws:
            for k, v in style.items():
                kw.cfg[k] = copy.deepcopy(v)
            kw.update()
            
        self.format_painter_style = None
        self.unsetCursor()
        
        from core.config_manager import ConfigManager
        from core.events import events
        ConfigManager.save()
        events.config_changed.emit(ConfigManager.load())
        
        # Emit edit request for the first selected key to reload editor property values
        if selected_kws:
            events.edit_key_requested.emit(selected_kws[0].key_id)

    def reload_keys(self):
        self._init_keys()
        self.update()

    def _init_keys(self):
        self._config = ConfigManager.load()
        for kw in self._key_widgets:
            kw.setParent(None)
            kw.deleteLater()
        self._key_widgets.clear()
        
        sx, sy = self._get_scale()
        dw_cfg = self._config.get("display_window", {})
        grid_size = dw_cfg.get("grid_size", 2)
        editor_key_size = dw_cfg.get("editor_key_size", 60)
        scale_factor = editor_key_size / 60.0
        
        # One grid cell in canvas pixels, representing editor_key_size / grid_size (or scale_factor px if free layout)
        if grid_size == 0:
            cell_w = sx * scale_factor
            cell_h = sy * scale_factor
        else:
            cell_w = max(4, sx * (editor_key_size / grid_size))
            cell_h = max(4, sy * (editor_key_size / grid_size))
        
        for key_cfg in self._config.get("keys", []):
            kw = KeyWidget(
                key_cfg, is_preview=True,
                grid_size=grid_size,
                scale_x=sx * scale_factor, scale_y=sy * scale_factor,
                parent=self
            )
            # Position snapped to grid index in canvas space
            x = int(key_cfg.get("x", 0) * cell_w)
            y = int(key_cfg.get("y", 0) * cell_h)
            # Size matches key config (scaled by editor_key_size)
            kw_w = key_cfg.get('width', 60)
            kw_h = key_cfg.get('height', 60)
            w = int(kw_w * sx * scale_factor)
            h = int(kw_h * sy * scale_factor)
            kw.setGeometry(x, y, w, h)
            kw.show()
            self._key_widgets.append(kw)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # Reposition all key widgets when canvas size changes
        if not self._key_widgets:
            return
        self._config = ConfigManager.load()
        sx, sy = self._get_scale()
        dw_cfg = self._config.get("display_window", {})
        grid_size = dw_cfg.get("grid_size", 2)
        editor_key_size = dw_cfg.get("editor_key_size", 60)
        scale_factor = editor_key_size / 60.0
        
        if grid_size == 0:
            cell_w = sx * scale_factor
            cell_h = sy * scale_factor
        else:
            cell_w = max(4, sx * (editor_key_size / grid_size))
            cell_h = max(4, sy * (editor_key_size / grid_size))
        
        for kw in self._key_widgets:
            kw.scale_x = sx * scale_factor
            kw.scale_y = sy * scale_factor
            x = int(kw.cfg.get("x", 0) * cell_w)
            y = int(kw.cfg.get("y", 0) * cell_h)
            kw_w = kw.cfg.get('width', 60)
            kw_h = kw.cfg.get('height', 60)
            w = int(kw_w * sx * scale_factor)
            h = int(kw_h * sy * scale_factor)
            kw.setGeometry(x, y, w, h)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        grid_visible = self._config.get("display_window", {}).get("grid_visible", True)
        dw_cfg = self._config.get("display_window", {})
        grid = dw_cfg.get("grid_size", 2)
        editor_key_size = dw_cfg.get("editor_key_size", 60)
        
        if grid_visible and grid > 0:
            sx, sy = self._get_scale()
            cell_w = max(4, sx * (editor_key_size / grid))
            cell_h = max(4, sy * (editor_key_size / grid))
            p.setPen(QPen(QColor(255, 255, 255, 26), 1))
            
            x = 0.0
            while x < self.width():
                p.drawLine(int(x), 0, int(x), self.height())
                x += cell_w
            y = 0.0
            while y < self.height():
                p.drawLine(0, int(y), self.width(), int(y))
                y += cell_h
                
        # Draw rubber band selection
        if self._selection_rect is not None and not self._selection_rect.isEmpty():
            p.setPen(QPen(QColor(68, 136, 255, 200), 1, Qt.PenStyle.DashLine))
            p.setBrush(QBrush(QColor(68, 136, 255, 50)))
            p.drawRect(self._selection_rect)
            
        super().paintEvent(e)
