from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QMouseEvent, QPainterPath
from PyQt6.QtCore import Qt, QRectF, QPropertyAnimation, QEasingCurve, pyqtProperty
from core.events import events
from core.config_manager import ConfigManager
from core.i18n import Trans

class KeyWidget(QWidget):
    def __init__(self, key_config, is_preview=False, grid_size=20, scale_x=1.0, scale_y=1.0, parent=None):
        super().__init__(parent)
        self.cfg = key_config
        self.key_id = self.cfg.get('id', 'unknown')
        self.key_code = self.cfg.get('key_code', '').lower()
        self.is_preview = is_preview
        self.grid_size = grid_size
        self.scale_x = scale_x
        self.scale_y = scale_y
        self._is_dragging = False
        self.is_selected = False
        
        # In preview mode, position is managed by GridCanvas (no setGeometry here)
        if not is_preview:
            self.setGeometry(
                self.cfg.get('x', 0),
                self.cfg.get('y', 0),
                self.cfg.get('width', 60),
                self.cfg.get('height', 60)
            )
        
        self.is_pressed = False
        self._current_scale = 1.0
        self._prev_val = None
        self._simulated_pressing = False
        
        # Connect to global events (only if it's the actual display widget)
        if not self.is_preview:
            key_type = self.cfg.get('key_type', 'normal')
            if key_type == 'normal':
                events.key_pressed.connect(self._on_global_key_press)
                events.key_released.connect(self._on_global_key_release)
            else:
                events.key_pressed.connect(self._on_special_key_press_update)
                events.key_released.connect(self._on_special_key_release_update)
                
                if key_type == 'kps':
                    self._click_timestamps = []
                    from PyQt6.QtCore import QTimer
                    self._kps_timer = QTimer(self)
                    self._kps_timer.timeout.connect(self._on_kps_timeout)
                    self._kps_timer.start(100)

    @pyqtProperty(float)
    def current_scale(self):
        return self._current_scale

    @current_scale.setter
    def current_scale(self, value):
        self._current_scale = value
        self.update()

    def _on_global_key_press(self, key_code):
        if key_code == self.key_code and not self.is_pressed:
            self.is_pressed = True
            self._animate_scale(self.cfg.get('press_scale', 0.92))

    def _on_global_key_release(self, key_code):
        if key_code == self.key_code and self.is_pressed:
            self.is_pressed = False
            self._animate_scale(1.0)
            
            # Update counter (in-memory only, saved to disk on exit or settings change)
            self.cfg['counter'] = self.cfg.get('counter', 0) + 1
            if self.cfg.get('show_counter', False):
                self.update()

    def _on_special_key_press_update(self, key_code):
        if self.cfg.get('key_type', 'normal') == 'kps':
            import time
            if not hasattr(self, '_click_timestamps'):
                self._click_timestamps = []
            self._click_timestamps.append(time.time())
        self._check_value_update()
        self.update()

    def _on_special_key_release_update(self, key_code):
        self._check_value_update()
        self.update()

    def _on_kps_timeout(self):
        self._check_value_update()
        self.update()

    def _check_value_update(self):
        key_type = self.cfg.get('key_type', 'normal')
        if key_type == 'normal':
            return
            
        # Compute current value
        if key_type == 'kps':
            import time
            now = time.time()
            if not hasattr(self, '_click_timestamps'):
                self._click_timestamps = []
            self._click_timestamps = [t for t in self._click_timestamps if now - t <= 1.0]
            val = len(self._click_timestamps)
        elif key_type == 'total_clicks':
            val = sum(k.get('counter', 0) for k in ConfigManager.load().get('keys', []) if k.get('key_type', 'normal') == 'normal')
        elif key_type == 'active_keys_count':
            active_cnt = 0
            parent_win = self.parent()
            if parent_win and hasattr(parent_win, '_key_widgets'):
                active_cnt = sum(1 for kw in parent_win._key_widgets if kw.cfg.get('key_type', 'normal') == 'normal' and getattr(kw, 'is_pressed', False))
            val = active_cnt
        else:
            val = 0
            
        if getattr(self, '_prev_val', None) is None:
            self._prev_val = val
        elif val > self._prev_val:
            self._prev_val = val
            if self.cfg.get('simulate_press', False):
                self._trigger_simulated_press()
        else:
            self._prev_val = val

    def _trigger_simulated_press(self):
        if getattr(self, '_simulated_pressing', False):
            return
        self._simulated_pressing = True
        self.is_pressed = True
        self._animate_scale(self.cfg.get('press_scale', 0.92))
        
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(120, self._release_simulated_press)

    def _release_simulated_press(self):
        self.is_pressed = False
        self._animate_scale(1.0)
        self._simulated_pressing = False

    def _animate_scale(self, target):
        self.anim = QPropertyAnimation(self, b"current_scale")
        self.anim.setDuration(80)
        self.anim.setStartValue(self._current_scale)
        self.anim.setEndValue(target)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim.start()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Apply scaling from center
        w = self.width()
        h = self.height()
        scale = self._current_scale
        
        p.translate(w / 2, h / 2)
        p.scale(scale, scale)
        p.translate(-w / 2, -h / 2)

        # Draw Background
        bg_c = self.cfg.get('bg_color', [30, 30, 60, 180])
        if self.is_pressed and not self.is_preview:
            bg_c = [min(255, int(c * 1.2)) for c in bg_c[:3]] + [bg_c[3]]
            
        p.setBrush(QBrush(QColor(*bg_c)))
        
        # Draw Border
        border_c = self.cfg.get('border_color', [108, 99, 255, 255])
        border_w = self.cfg.get('border_width', 2)
        if self.is_preview and self.is_selected:
            # High-visibility border for selected items in the canvas
            border_c = [255, 255, 255, 255]
            border_w = 3
            
        radius = self.cfg.get('corner_radius', 10)
        font_size = self.cfg.get('font_size', 16)
        
        if self.is_preview:
            # Scale down visual elements so they match the canvas resolution
            border_w = max(1, int(border_w * self.scale_x)) if (self.is_selected or self.cfg.get('border_width', 2) > 0) else 0
            radius = max(1, int(radius * self.scale_x))
            font_size = max(6, int(font_size * self.scale_x))

        if border_w == 0 and not (self.is_preview and self.is_selected):
            p.setPen(Qt.PenStyle.NoPen)
        else:
            p.setPen(QPen(QColor(*border_c), border_w))
        rect = QRectF(max(0.5, border_w/2), max(0.5, border_w/2), w - max(1, border_w), h - max(1, border_w))
        p.drawRoundedRect(rect, radius, radius)

        # Draw Text
        text_c = self.cfg.get('text_color', [255, 255, 255, 255])
        p.setPen(QColor(*text_c))
        
        font = QFont("Segoe UI", font_size)
        font.setBold(self.cfg.get('font_bold', True))
        p.setFont(font)
        
        from core.config_manager import ConfigManager
        global_cfg = ConfigManager.load().get("display_window", {})
        
        toy = self.cfg.get("text_offset_y", global_cfg.get("text_offset_y", 0))
        coy = self.cfg.get("counter_offset_y", global_cfg.get("counter_offset_y", 20))
        
        if self.is_preview:
            toy = int(toy * self.scale_y)
            coy = int(coy * self.scale_y)
            
        key_type = self.cfg.get('key_type', 'normal')
        
        # Determine Display Name: nickname overrides display_name for visual text
        if key_type == 'normal':
            disp_name = self.cfg.get('nickname') or self.cfg.get('display_name', '')
            val = str(self.cfg.get('counter', 0))
        elif key_type == 'kps':
            disp_name = self.cfg.get('nickname') or self.cfg.get('display_name', 'KPS')
            import time
            now = time.time()
            if not hasattr(self, '_click_timestamps'):
                self._click_timestamps = []
            self._click_timestamps = [t for t in self._click_timestamps if now - t <= 1.0]
            val = str(len(self._click_timestamps))
        elif key_type == 'total_clicks':
            disp_name = self.cfg.get('nickname') or self.cfg.get('display_name', 'TOTAL')
            val = str(sum(k.get('counter', 0) for k in ConfigManager.load().get('keys', []) if k.get('key_type', 'normal') == 'normal'))
        elif key_type == 'active_keys_count':
            disp_name = self.cfg.get('nickname') or self.cfg.get('display_name', 'ACTIVE')
            active_cnt = 0
            parent_win = self.parent()
            if parent_win and hasattr(parent_win, '_key_widgets'):
                active_cnt = sum(1 for kw in parent_win._key_widgets if kw.cfg.get('key_type', 'normal') == 'normal' and getattr(kw, 'is_pressed', False))
            val = str(active_cnt)
            
        show_counter = self.cfg.get('show_counter', False)
        
        if show_counter or key_type != 'normal':
            p.drawText(QRectF(0, toy, w, h), Qt.AlignmentFlag.AlignCenter, disp_name)
            
            c_size = self.cfg.get('counter_size', 14)
            cox = self.cfg.get('counter_offset_x', 0)
            
            if self.is_preview:
                c_size = max(4, int(c_size * self.scale_x))
                cox = int(cox * self.scale_x)
                
            font.setPointSize(c_size)
            p.setFont(font)
            p.drawText(QRectF(cox, coy, w, h), Qt.AlignmentFlag.AlignCenter, val)
        else:
            p.drawText(QRectF(0, toy, w, h), Qt.AlignmentFlag.AlignCenter, disp_name)

    # Mouse Events for dragging and context menu (Only active in preview mode)
    def mousePressEvent(self, e: QMouseEvent):
        if not self.is_preview:
            e.ignore()
            return
            
        if e.button() == Qt.MouseButton.LeftButton:
            parent_canvas = self.parent()
            is_ctrl = bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
            
            if is_ctrl:
                self.is_selected = not self.is_selected
                self.update()
            else:
                if not self.is_selected:
                    if parent_canvas:
                        for kw in parent_canvas._key_widgets:
                            kw.is_selected = False
                            kw.update()
                    self.is_selected = True
                    self.update()
                
            self._drag_start_pos = e.globalPosition().toPoint()
            self._is_dragging = False
            
            # Save start positions for ALL selected widgets
            if parent_canvas:
                for kw in parent_canvas._key_widgets:
                    if kw.is_selected:
                        kw._widget_start_pos = kw.pos()
                        kw.raise_()
            else:
                self._widget_start_pos = self.pos()
                self.raise_()
                
            e.accept()
        elif e.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(e.globalPosition().toPoint())
            e.accept()
        else:
            e.ignore()

    def mouseMoveEvent(self, e: QMouseEvent):
        if not self.is_preview:
            e.ignore()
            return
            
        if e.buttons() == Qt.MouseButton.LeftButton:
            delta = e.globalPosition().toPoint() - self._drag_start_pos
            if delta.manhattanLength() > 3:
                self._is_dragging = True
                
            parent = self.parent()
            if not parent:
                return

            # Gather all selected widgets
            selected_kws = [kw for kw in parent._key_widgets if kw.is_selected]
            if not selected_kws:
                return

            # Group bounds checking in HUD coordinates to prevent HUD keys going out of bounds
            base_w, base_h = parent._get_display_size()
            dw_cfg = parent._config.get("display_window", {})
            editor_key_size = dw_cfg.get("editor_key_size", 60)
            if editor_key_size <= 0:
                editor_key_size = 60
            scale_factor = 60.0 / editor_key_size
            
            mapped_win_w = int(base_w * scale_factor)
            mapped_win_h = int(base_h * scale_factor)
            
            sx = max(0.01, self.scale_x)
            sy = max(0.01, self.scale_y)
            
            # Start position of each widget in HUD coordinates
            min_disp_dx = -min(kw._widget_start_pos.x() / sx for kw in selected_kws)
            max_disp_dx = mapped_win_w - max(kw._widget_start_pos.x() / sx + kw.cfg.get('width', 60) for kw in selected_kws)
            min_disp_dy = -min(kw._widget_start_pos.y() / sy for kw in selected_kws)
            max_disp_dy = mapped_win_h - max(kw._widget_start_pos.y() / sy + kw.cfg.get('height', 60) for kw in selected_kws)
            
            # Proposed delta in HUD coordinates
            disp_dx = delta.x() / sx
            disp_dy = delta.y() / sy
            
            # Constrain the delta in HUD coordinate space
            disp_dx = max(min_disp_dx, min(disp_dx, max_disp_dx))
            disp_dy = max(min_disp_dy, min(disp_dy, max_disp_dy))
            
            grid = self.grid_size
            if grid == 0:
                for kw in selected_kws:
                    disp_x = kw._widget_start_pos.x() / sx + disp_dx
                    disp_y = kw._widget_start_pos.y() / sy + disp_dy
                    
                    kw.cfg['x'] = int(disp_x)
                    kw.cfg['y'] = int(disp_y)
                    
                    final_x = int(disp_x * sx)
                    final_y = int(disp_y * sy)
                    kw.move(final_x, final_y)
            else:
                cell_w = max(4, sx * (60 / grid))
                cell_h = max(4, sy * (60 / grid))
                grid_unit = 60 / grid
                for kw in selected_kws:
                    disp_x = kw._widget_start_pos.x() / sx + disp_dx
                    disp_y = kw._widget_start_pos.y() / sy + disp_dy
                    
                    snapped_grid_x = round(disp_x / grid_unit)
                    snapped_grid_y = round(disp_y / grid_unit)
                    
                    kw.cfg['x'] = int(snapped_grid_x)
                    kw.cfg['y'] = int(snapped_grid_y)
                    
                    final_x = int(snapped_grid_x * cell_w)
                    final_y = int(snapped_grid_y * cell_h)
                    kw.move(final_x, final_y)
                
            ConfigManager.save()
            events.config_changed.emit(ConfigManager.load())
            e.accept()

    def mouseReleaseEvent(self, e: QMouseEvent):
        if not self.is_preview:
            e.ignore()
            return
            
        if e.button() == Qt.MouseButton.LeftButton:
            if not getattr(self, '_is_dragging', False):
                is_ctrl = bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
                if not is_ctrl:
                    parent_canvas = self.parent()
                    if parent_canvas:
                        for kw in parent_canvas._key_widgets:
                            if kw != self:
                                kw.is_selected = False
                                kw.update()
                        self.is_selected = True
                        self.update()
                    # Single click no longer opens the editor (double-click does)
            self._is_dragging = False
            
            # If format painter is active and Ctrl is not held, apply immediately on click
            parent_canvas = self.parent()
            if parent_canvas and getattr(parent_canvas, 'format_painter_style', None):
                from PyQt6.QtWidgets import QApplication
                if not (QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier):
                    parent_canvas.apply_format_painter()
        e.accept()

    def mouseDoubleClickEvent(self, e: QMouseEvent):
        if not self.is_preview:
            e.ignore()
            return
        if e.button() == Qt.MouseButton.LeftButton:
            events.edit_key_requested.emit(self.key_id)
            e.accept()

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0a0a0a;
                color: #ffffff;
                border: 1px solid #333333;
            }
            QMenu::item {
                padding: 5px 20px 5px 20px;
            }
            QMenu::item:selected {
                background-color: #2a2a2a;
            }
            QMenu::separator {
                height: 1px;
                background-color: #333333;
                margin: 4px 0px;
            }
        """)
        
        action_edit = menu.addAction(Trans.t("edit_key", "🎨 编辑此按键"))
        action_edit.triggered.connect(lambda: events.edit_key_requested.emit(self.key_id))
        
        action_painter = menu.addAction(Trans.t("format_painter", "格式刷"))
        action_painter.triggered.connect(self._trigger_format_painter)
        
        menu.exec(pos)

    def _trigger_format_painter(self):
        parent_canvas = self.parent()
        if not parent_canvas:
            return
            
        exclude_keys = {'id', 'key_code', 'display_name', 'nickname', 'x', 'y', 'counter', 'key_type', 'simulate_press'}
        import copy
        parent_canvas.format_painter_style = {k: copy.deepcopy(v) for k, v in self.cfg.items() if k not in exclude_keys}
        parent_canvas.setCursor(Qt.CursorShape.WhatsThisCursor)
