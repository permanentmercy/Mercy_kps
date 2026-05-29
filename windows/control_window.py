from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton, QCheckBox, QScrollArea, QDialog, QComboBox, QLineEdit, QFrame, QSplitter, QButtonGroup, QSlider
from PyQt6.QtCore import Qt, QPoint, QEvent, QRect
from PyQt6.QtGui import QGuiApplication, QKeyEvent
from widgets.title_bar import TitleBar
from widgets.smooth_slider import SmoothSlider
from widgets.color_button import ColorButton
from widgets.grid_canvas import GridCanvas
from widgets.profile_dialog import ProfileSelectionDialog
from widgets.toast import Toast
from core.config_manager import ConfigManager
from core.events import events
from core.i18n import Trans
from widgets.add_key_dialog import AddKeyDialog
import sys
import copy

class NonScrollSlider(SmoothSlider):
    def __init__(self, orientation=None, parent=None):
        super().__init__(min_val=0, max_val=100, default_val=0, parent=parent)
        
    def wheelEvent(self, e):
        e.ignore()


class DraggableFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dragging = False
        self._drag_start = None
        self._custom_pos = None

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start = e.position().toPoint()
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._dragging and self._drag_start:
            delta = e.position().toPoint() - self._drag_start
            new_pos = self.pos() + delta
            
            if self.parentWidget():
                pw = self.parentWidget().width()
                ph = self.parentWidget().height()
                new_x = max(0, min(new_pos.x(), pw - self.width()))
                new_y = max(0, min(new_pos.y(), ph - self.height()))
                new_pos.setX(new_x)
                new_pos.setY(new_y)
                
            self.move(new_pos)
            self._custom_pos = new_pos
            e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.unsetCursor()
            e.accept()
        else:
            super().mouseReleaseEvent(e)

class ControlWindow(QWidget):
    def __init__(self, display_win, listener, parent=None):
        super().__init__(parent)
        self.display_win = display_win
        self.listener = listener
        self._config = ConfigManager.load()
        
        # Frameless and transparent background
        self.setObjectName("ControlWindow")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("#ControlWindow { background: transparent; }")
        
        self._enable_taskbar_minimize()
        
        # Load geometry or default
        cw_cfg = self._config.get("control_window", {})
        x = cw_cfg.get("x", 100)
        y = cw_cfg.get("y", 100)
        w = cw_cfg.get("width", 1000)
        h = cw_cfg.get("height", 650)
        
        self.setGeometry(x, y, w, h)
        self.setMinimumSize(700, 450)
        
        # Grab keyboard focus for DEL events
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self._is_resizing = False
        self._resize_edge = []
        self._drag_start_pos = None
        self._drag_start_geo = None
        self._resize_margin = 8
        
        QGuiApplication.instance().installEventFilter(self)
        
        self._init_ui()
        self.retranslate_ui()

    def _enable_taskbar_minimize(self):
        import sys
        if sys.platform == "win32":
            try:
                import ctypes
                GWL_STYLE = -16
                WS_MINIMIZEBOX = 0x00020000
                WS_SYSMENU = 0x00080000
                
                hwnd = int(self.winId())
                user32 = ctypes.windll.user32
                style = user32.GetWindowLongW(hwnd, GWL_STYLE)
                style |= WS_MINIMIZEBOX | WS_SYSMENU
                user32.SetWindowLongW(hwnd, GWL_STYLE, style)
            except Exception as e:
                print(f"Failed to enable taskbar minimize: {e}")

    def eventFilter(self, obj, e):
        from PyQt6.QtWidgets import QWidget
        from PyQt6.QtCore import QEvent
        
        if isinstance(obj, QWidget) and obj.window() == self:
            if e.type() == QEvent.Type.MouseMove:
                if not getattr(self, '_is_resizing', False):
                    # Check hover
                    pos = self.mapFromGlobal(e.globalPosition().toPoint())
                    x, y = pos.x(), pos.y()
                    w, h = self.width(), self.height()
                    m = self._resize_margin
                    
                    edges = []
                    if x <= m: edges.append('left')
                    elif x >= w - m: edges.append('right')
                    if y <= m: edges.append('top')
                    elif y >= h - m: edges.append('bottom')
                    
                    if edges:
                        cursor = Qt.CursorShape.ArrowCursor
                        if 'left' in edges and 'top' in edges: cursor = Qt.CursorShape.SizeFDiagCursor
                        elif 'right' in edges and 'bottom' in edges: cursor = Qt.CursorShape.SizeFDiagCursor
                        elif 'right' in edges and 'top' in edges: cursor = Qt.CursorShape.SizeBDiagCursor
                        elif 'left' in edges and 'bottom' in edges: cursor = Qt.CursorShape.SizeBDiagCursor
                        elif 'left' in edges or 'right' in edges: cursor = Qt.CursorShape.SizeHorCursor
                        elif 'top' in edges or 'bottom' in edges: cursor = Qt.CursorShape.SizeVerCursor
                        
                        self.setCursor(cursor)
                        return True
                    else:
                        self.unsetCursor()
                else:
                    # Execute resize
                    delta = e.globalPosition() - self._drag_start_pos
                    dx, dy = int(delta.x()), int(delta.y())
                    geo = self._drag_start_geo
                    
                    new_x, new_y = geo.x(), geo.y()
                    new_w, new_h = geo.width(), geo.height()
                    
                    if 'left' in self._resize_edge:
                        new_x += dx
                        new_w -= dx
                    elif 'right' in self._resize_edge:
                        new_w += dx
                        
                    if 'top' in self._resize_edge:
                        new_y += dy
                        new_h -= dy
                    elif 'bottom' in self._resize_edge:
                        new_h += dy
                        
                    if new_w < self.minimumWidth():
                        if 'left' in self._resize_edge: new_x = geo.x() + geo.width() - self.minimumWidth()
                        new_w = self.minimumWidth()
                    if new_h < self.minimumHeight():
                        if 'top' in self._resize_edge: new_y = geo.y() + geo.height() - self.minimumHeight()
                        new_h = self.minimumHeight()
                        
                    self.setGeometry(new_x, new_y, new_w, new_h)
                    return True
                    
            elif e.type() == QEvent.Type.MouseButtonPress and e.button() == Qt.MouseButton.LeftButton:
                pos = self.mapFromGlobal(e.globalPosition().toPoint())
                x, y = pos.x(), pos.y()
                w, h = self.width(), self.height()
                m = self._resize_margin
                
                edges = []
                if x <= m: edges.append('left')
                elif x >= w - m: edges.append('right')
                if y <= m: edges.append('top')
                elif y >= h - m: edges.append('bottom')
                
                if edges:
                    self._is_resizing = True
                    self._resize_edge = edges
                    self._drag_start_pos = e.globalPosition()
                    self._drag_start_geo = self.geometry()
                    return True
                    
            elif e.type() == QEvent.Type.MouseButtonRelease and e.button() == Qt.MouseButton.LeftButton:
                if getattr(self, '_is_resizing', False):
                    self._is_resizing = False
                    self._resize_edge = []
                    self.unsetCursor()
                    return True
            elif e.type() == QEvent.Type.KeyPress:
                from PyQt6.QtWidgets import QApplication, QLineEdit, QTextEdit
                focused = QApplication.focusWidget()
                if not isinstance(focused, (QLineEdit, QTextEdit)):
                    if e.key() == Qt.Key.Key_Delete:
                        self._delete_selected_keys()
                        return True
                    elif e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                        if e.key() == Qt.Key.Key_C:
                            self._copy_key()
                            return True
                        elif e.key() == Qt.Key.Key_X:
                            self._cut_key()
                            return True
                        elif e.key() == Qt.Key.Key_V:
                            self._paste_key()
                            return True
            elif e.type() == QEvent.Type.KeyRelease:
                if e.key() == Qt.Key.Key_Control:
                    if hasattr(self, 'grid_canvas') and getattr(self.grid_canvas, 'format_painter_style', None):
                        self.grid_canvas.apply_format_painter()

        return super().eventFilter(obj, e)

    # Handled by eventFilter now

    def _init_ui(self):
        # Outer layout to wrap the central rounded frame
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0) # No margins, container fills window

        
        # Central frame with rounded corners
        self.container = QFrame(self)
        self.container.setObjectName("MainWindowContainer")
        self.container.setStyleSheet("""
            QFrame#MainWindowContainer {
                background-color: #0a0a0a;
                border: 1px solid #262626;
                border-radius: 12px;
            }
            QWidget#SplitterWrapper {
                background-color: #0a0a0a;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
        """)
        outer_layout.addWidget(self.container)
        
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Title bar
        self.title_bar = TitleBar("KPS-Plus Editor", self)
        self.title_bar.settings_clicked.connect(self._show_settings_dialog)
        main_layout.addWidget(self.title_bar)
        
        # Content Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: transparent;
                width: 15px;
            }
        """)
        
        # Add 15px margin around the splitter inside the main layout
        self.splitter_wrapper = QWidget()
        self.splitter_wrapper.setObjectName("SplitterWrapper")
        splitter_layout = QVBoxLayout(self.splitter_wrapper)
        splitter_layout.setContentsMargins(15, 15, 15, 15)
        splitter_layout.addWidget(self.splitter)
        main_layout.addWidget(self.splitter_wrapper)
        
        # Left Panel (Settings)
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_panel_widget = QWidget()
        left_panel = QVBoxLayout(left_panel_widget)
        left_scroll.setWidget(left_panel_widget)
        self.splitter.addWidget(left_scroll)
        
        # General Group
        self.group_general = QGroupBox()
        vbox_general = QVBoxLayout(self.group_general)
        
        self.chk_listen = QCheckBox()
        self.chk_listen.setChecked(self.listener.is_running)
        self.chk_listen.stateChanged.connect(self._toggle_listener)
        vbox_general.addWidget(self.chk_listen)
        
        left_panel.addWidget(self.group_general)
        
        # Rain Group
        self.group_rain = QGroupBox()
        vbox_rain = QVBoxLayout(self.group_rain)
        
        self.chk_rain = QCheckBox()
        self.chk_rain.setChecked(self._config.get("rain", {}).get("enabled", True))
        self.chk_rain.stateChanged.connect(self._toggle_rain)
        vbox_rain.addWidget(self.chk_rain)
        
        self.lbl_rain_speed = QLabel()
        vbox_rain.addWidget(self.lbl_rain_speed)
        
        hbox_rs = QHBoxLayout()
        rain_speed_val = self._config.get("rain", {}).get("speed_up", 6)
        self.slider_rain_speed = SmoothSlider(1, 30, rain_speed_val)
        self.slider_rain_speed.valueChanged.connect(self._update_rain_speed_label)
        self.slider_rain_speed.sliderReleased.connect(self._on_rain_speed_released)
        hbox_rs.addWidget(self.slider_rain_speed)
        self.lbl_rain_speed_val = QLabel(str(rain_speed_val))
        self.lbl_rain_speed_val.setFixedWidth(40)
        self.lbl_rain_speed_val.setStyleSheet("color: #a3a3a3; font-weight: bold; font-size: 13px;")
        hbox_rs.addWidget(self.lbl_rain_speed_val)
        vbox_rain.addLayout(hbox_rs)
        
        self.chk_rain_fade = QCheckBox()
        self.chk_rain_fade.setChecked(self._config.get("rain", {}).get("fade_enabled", True))
        self.chk_rain_fade.stateChanged.connect(self._toggle_rain_fade)
        vbox_rain.addWidget(self.chk_rain_fade)
        
        left_panel.addWidget(self.group_rain)
        
        # Display Group
        self.group_display = QGroupBox()
        vbox_display = QVBoxLayout(self.group_display)
        
        self.chk_grid = QCheckBox()
        self.chk_grid.setChecked(self._config.get("display_window", {}).get("grid_visible", True))
        self.chk_grid.stateChanged.connect(self._toggle_grid)
        vbox_display.addWidget(self.chk_grid)
        
        self.lbl_grid_size = QLabel()
        vbox_display.addWidget(self.lbl_grid_size)
        
        hbox_grid = QHBoxLayout()
        grid_val = max(1, self._config.get("display_window", {}).get("grid_size", 2))
        self.slider_grid = SmoothSlider(1, 10, grid_val)
        self.slider_grid.valueChanged.connect(self._update_grid_label)
        self.slider_grid.sliderReleased.connect(self._on_grid_slider_released)
        hbox_grid.addWidget(self.slider_grid)
        
        self.lbl_grid_val = QLabel()
        self.lbl_grid_val.setFixedWidth(40)
        self.lbl_grid_val.setText(str(grid_val))
        self.lbl_grid_val.setStyleSheet("color: #a3a3a3; font-weight: bold; font-size: 13px;")
        hbox_grid.addWidget(self.lbl_grid_val)
        vbox_display.addLayout(hbox_grid)
        
        # (Global vertical offsets moved to floating property panel)
        
        self.lbl_editor_key_size = QLabel()
        vbox_display.addWidget(self.lbl_editor_key_size)
        hbox_eks = QHBoxLayout()
        eks_val = self._config.get("display_window", {}).get("editor_key_size", 60)
        self.slider_editor_key_size = SmoothSlider(30, 120, eks_val)
        self.slider_editor_key_size.valueChanged.connect(self._update_editor_key_size_label)
        self.slider_editor_key_size.sliderReleased.connect(self._on_editor_key_size_released)
        hbox_eks.addWidget(self.slider_editor_key_size)
        self.lbl_editor_key_size_val = QLabel(str(eks_val))
        self.lbl_editor_key_size_val.setFixedWidth(40)
        self.lbl_editor_key_size_val.setStyleSheet("color: #a3a3a3; font-weight: bold; font-size: 13px;")
        hbox_eks.addWidget(self.lbl_editor_key_size_val)
        vbox_display.addLayout(hbox_eks)
        
        self.lbl_key_spacing = QLabel()
        vbox_display.addWidget(self.lbl_key_spacing)
        hbox_ks = QHBoxLayout()
        ks_val = self._config.get("display_window", {}).get("key_spacing", 0)
        self.slider_key_spacing = SmoothSlider(-20, 20, ks_val)
        self.slider_key_spacing.valueChanged.connect(self._update_key_spacing_label)
        self.slider_key_spacing.sliderReleased.connect(self._on_key_spacing_released)
        hbox_ks.addWidget(self.slider_key_spacing)
        self.lbl_key_spacing_val = QLabel(str(ks_val))
        self.lbl_key_spacing_val.setFixedWidth(40)
        self.lbl_key_spacing_val.setStyleSheet("color: #a3a3a3; font-weight: bold; font-size: 13px;")
        hbox_ks.addWidget(self.lbl_key_spacing_val)
        vbox_display.addLayout(hbox_ks)
        
        left_panel.addWidget(self.group_display)
        
        # Add Key Button
        self.btn_add_key = QPushButton()
        self.btn_add_key.clicked.connect(self._add_key)
        left_panel.addWidget(self.btn_add_key)
        
        # Select Profile Button
        self.btn_select_profile = QPushButton()
        self.btn_select_profile.clicked.connect(self._show_profile_dialog)
        left_panel.addWidget(self.btn_select_profile)
        
        left_panel.addStretch()
        
        # Right Panel (Layout Editor Canvas)
        right_panel_widget = QWidget()
        right_panel = QVBoxLayout(right_panel_widget)
        right_panel.setContentsMargins(0, 0, 0, 0)
        self.splitter.addWidget(right_panel_widget)
        
        # Editor canvas wrapper for absolute positioning
        self.canvas_wrapper = QWidget()
        canvas_wrapper_layout = QVBoxLayout(self.canvas_wrapper)
        canvas_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        
        # Editor canvas with grid (adaptive + scaled)
        self.grid_canvas = GridCanvas(self.display_win, self.canvas_wrapper)
        canvas_wrapper_layout.addWidget(self.grid_canvas)
        
        right_panel.addWidget(self.canvas_wrapper, stretch=1)
        
        # Set initial sizes for splitter
        cw_cfg = self._config.get("control_window", {})
        splitter_sizes = cw_cfg.get("splitter_sizes")
        if not splitter_sizes or not isinstance(splitter_sizes, list) or len(splitter_sizes) < 2:
            splitter_sizes = [300, 600]
        self.splitter.setSizes(splitter_sizes)
        
        # Initialize Floating Edit Panel (Absolute Positioned over Canvas Wrapper)
        self._init_floating_panel()
        
        # Connect events
        events.edit_key_requested.connect(self._on_edit_key_requested)
        self._current_edit_key_id = None

    def _init_floating_panel(self):
        self.floating_panel = DraggableFrame(self.canvas_wrapper)
        self.floating_panel.setObjectName("FloatingEditPanel")
        self.floating_panel.setStyleSheet("""
            QFrame#FloatingEditPanel {
                background-color: rgba(18, 18, 18, 230);
                border: 1px solid #333333;
                border-radius: 12px;
            }
            QFrame#FloatingEditPanel > QWidget,
            QFrame#FloatingEditPanel QLabel,
            QFrame#FloatingEditPanel QCheckBox {
                background-color: transparent;
            }
            QFrame#FloatingEditPanel QGroupBox {
                color: #aaaaaa;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 10px;
            }
            QFrame#FloatingEditPanel QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 4px;
            }
        """)
        
        main_vbox = QVBoxLayout(self.floating_panel)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea(self.floating_panel)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        vbox_editor = QVBoxLayout(scroll_content)
        vbox_editor.setContentsMargins(15, 15, 15, 15)
        vbox_editor.setSpacing(10)
        
        self.lbl_editing = QLabel()
        self.lbl_editing.setStyleSheet("font-weight: bold; font-size: 15px; margin-bottom: 5px;")
        vbox_editor.addWidget(self.lbl_editing)
        
        # 1. Basic Info Group
        self.group_basic = QGroupBox()
        vbox_basic = QVBoxLayout(self.group_basic)
        vbox_basic.setContentsMargins(10, 12, 10, 10)
        vbox_basic.setSpacing(8)
        
        # Key Code field
        self.widget_key_code = QWidget()
        hbox_code = QHBoxLayout(self.widget_key_code)
        hbox_code.setContentsMargins(0, 0, 0, 0)
        self.lbl_key_code = QLabel()
        hbox_code.addWidget(self.lbl_key_code)
        self.edit_key_code = QLineEdit()
        self.edit_key_code.textChanged.connect(self._change_key_code)
        hbox_code.addWidget(self.edit_key_code)
        self.btn_bind = QPushButton()
        self.btn_bind.clicked.connect(self._start_bind)
        hbox_code.addWidget(self.btn_bind)
        vbox_basic.addWidget(self.widget_key_code)

        # Nickname field
        self.widget_nickname = QWidget()
        hbox_nick = QHBoxLayout(self.widget_nickname)
        hbox_nick.setContentsMargins(0, 0, 0, 0)
        self.lbl_nickname = QLabel()
        self.lbl_nickname.setFixedWidth(52)
        hbox_nick.addWidget(self.lbl_nickname)
        self.edit_nickname = QLineEdit()
        self.edit_nickname.setPlaceholderText("...")
        self.edit_nickname.textChanged.connect(self._change_key_nickname)
        hbox_nick.addWidget(self.edit_nickname)
        vbox_basic.addWidget(self.widget_nickname)
        
        vbox_editor.addWidget(self.group_basic)
        
        # 2. Colors Group
        self.group_colors = QGroupBox()
        vbox_colors = QVBoxLayout(self.group_colors)
        vbox_colors.setContentsMargins(10, 12, 10, 10)
        vbox_colors.setSpacing(8)

        def _make_color_row(label_attr, btn_attr, signal_slot):
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            hbox = QHBoxLayout(row)
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.setSpacing(8)
            lbl = QLabel()
            lbl.setFixedWidth(52)
            lbl.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
            setattr(self, label_attr, lbl)
            hbox.addWidget(lbl)
            btn = ColorButton()
            btn.colorChanged.connect(signal_slot)
            setattr(self, btn_attr, btn)
            hbox.addWidget(btn, 1)
            return row

        vbox_colors.addWidget(_make_color_row('lbl_bg_color',     'btn_bg_color',     self._change_key_bg_color))
        vbox_colors.addWidget(_make_color_row('lbl_rain_color',   'btn_rain_color',   self._change_key_rain_color))
        vbox_colors.addWidget(_make_color_row('lbl_border_color', 'btn_border_color', self._change_key_border_color))
        vbox_colors.addWidget(_make_color_row('lbl_text_color',   'btn_text_color',   self._change_key_text_color))

        self.widget_rain_color = vbox_colors.itemAt(1).widget()
        self.widget_border_color = vbox_colors.itemAt(2).widget()

        vbox_editor.addWidget(self.group_colors)
        
        # 3. Shape & Size Group
        self.group_shape = QGroupBox()
        vbox_shape = QVBoxLayout(self.group_shape)
        vbox_shape.setContentsMargins(10, 12, 10, 10)
        vbox_shape.setSpacing(8)
        
        # Display Width field
        self.widget_display_width = QWidget()
        vbox_dw = QVBoxLayout(self.widget_display_width)
        vbox_dw.setContentsMargins(0, 0, 0, 0)
        vbox_dw.setSpacing(2)
        self.lbl_display_width = QLabel()
        vbox_dw.addWidget(self.lbl_display_width)
        self.slider_display_width = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_display_width.setRange(10, 300)
        self.slider_display_width.valueChanged.connect(self._change_key_display_width)
        vbox_dw.addWidget(self.slider_display_width)
        vbox_shape.addWidget(self.widget_display_width)

        # Display Height field
        self.widget_display_height = QWidget()
        vbox_dh = QVBoxLayout(self.widget_display_height)
        vbox_dh.setContentsMargins(0, 0, 0, 0)
        vbox_dh.setSpacing(2)
        self.lbl_display_height = QLabel()
        vbox_dh.addWidget(self.lbl_display_height)
        self.slider_display_height = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_display_height.setRange(10, 300)
        self.slider_display_height.valueChanged.connect(self._change_key_display_height)
        vbox_dh.addWidget(self.slider_display_height)
        vbox_shape.addWidget(self.widget_display_height)
        
        # Border Width field
        self.widget_border_width = QWidget()
        vbox_bw = QVBoxLayout(self.widget_border_width)
        vbox_bw.setContentsMargins(0, 0, 0, 0)
        vbox_bw.setSpacing(2)
        self.lbl_border_width = QLabel()
        vbox_bw.addWidget(self.lbl_border_width)
        self.slider_border_width = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_border_width.setRange(0, 10)
        self.slider_border_width.valueChanged.connect(self._change_key_border_width)
        vbox_bw.addWidget(self.slider_border_width)
        vbox_shape.addWidget(self.widget_border_width)

        # Corner Radius field
        self.widget_corner_radius = QWidget()
        vbox_cr = QVBoxLayout(self.widget_corner_radius)
        vbox_cr.setContentsMargins(0, 0, 0, 0)
        vbox_cr.setSpacing(2)
        self.lbl_corner_radius = QLabel()
        vbox_cr.addWidget(self.lbl_corner_radius)
        self.slider_corner_radius = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_corner_radius.setRange(0, 30)
        self.slider_corner_radius.valueChanged.connect(self._change_key_corner_radius)
        vbox_cr.addWidget(self.slider_corner_radius)
        vbox_shape.addWidget(self.widget_corner_radius)
        
        vbox_editor.addWidget(self.group_shape)
        
        # 4. Text & Counter Group
        self.group_text_counter = QGroupBox()
        vbox_tc = QVBoxLayout(self.group_text_counter)
        vbox_tc.setContentsMargins(10, 12, 10, 10)
        vbox_tc.setSpacing(8)

        # Text Size field
        self.widget_text_size = QWidget()
        vbox_ts = QVBoxLayout(self.widget_text_size)
        vbox_ts.setContentsMargins(0, 0, 0, 0)
        vbox_ts.setSpacing(2)
        self.lbl_text_size = QLabel()
        vbox_ts.addWidget(self.lbl_text_size)
        self.slider_text_size = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_text_size.setRange(8, 48)
        self.slider_text_size.valueChanged.connect(self._change_key_text_size)
        vbox_ts.addWidget(self.slider_text_size)
        vbox_tc.addWidget(self.widget_text_size)

        # Text Offset Y field
        self.widget_text_offset_y = QWidget()
        vbox_toy = QVBoxLayout(self.widget_text_offset_y)
        vbox_toy.setContentsMargins(0, 0, 0, 0)
        vbox_toy.setSpacing(2)
        self.lbl_text_offset_y = QLabel()
        vbox_toy.addWidget(self.lbl_text_offset_y)
        self.slider_text_offset_y = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_text_offset_y.setRange(-50, 50)
        self.slider_text_offset_y.valueChanged.connect(self._change_key_text_offset_y)
        vbox_toy.addWidget(self.slider_text_offset_y)
        vbox_tc.addWidget(self.widget_text_offset_y)

        # Counter Size field
        self.widget_counter_size = QWidget()
        vbox_cs = QVBoxLayout(self.widget_counter_size)
        vbox_cs.setContentsMargins(0, 0, 0, 0)
        vbox_cs.setSpacing(2)
        self.lbl_counter_size = QLabel()
        vbox_cs.addWidget(self.lbl_counter_size)
        self.slider_counter_size = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_counter_size.setRange(8, 64)
        self.slider_counter_size.valueChanged.connect(self._change_key_counter_size)
        vbox_cs.addWidget(self.slider_counter_size)
        vbox_tc.addWidget(self.widget_counter_size)

        # Counter Offset X field
        self.widget_counter_offset_x = QWidget()
        vbox_cx = QVBoxLayout(self.widget_counter_offset_x)
        vbox_cx.setContentsMargins(0, 0, 0, 0)
        vbox_cx.setSpacing(2)
        self.lbl_counter_offset_x = QLabel()
        vbox_cx.addWidget(self.lbl_counter_offset_x)
        self.slider_counter_offset_x = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_counter_offset_x.setRange(-100, 100)
        self.slider_counter_offset_x.valueChanged.connect(self._change_key_counter_offset_x)
        vbox_cx.addWidget(self.slider_counter_offset_x)
        vbox_tc.addWidget(self.widget_counter_offset_x)

        # Counter Offset Y field
        self.widget_counter_offset_y = QWidget()
        vbox_coy = QVBoxLayout(self.widget_counter_offset_y)
        vbox_coy.setContentsMargins(0, 0, 0, 0)
        vbox_coy.setSpacing(2)
        self.lbl_counter_offset_y = QLabel()
        vbox_coy.addWidget(self.lbl_counter_offset_y)
        self.slider_counter_offset_y = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_counter_offset_y.setRange(-100, 100)
        self.slider_counter_offset_y.valueChanged.connect(self._change_key_counter_offset_y)
        vbox_coy.addWidget(self.slider_counter_offset_y)
        vbox_tc.addWidget(self.widget_counter_offset_y)

        # Text Bold checkbox
        self.chk_text_bold = QCheckBox()
        self.chk_text_bold.stateChanged.connect(self._change_key_text_bold)
        vbox_tc.addWidget(self.chk_text_bold)
        
        # Counter Toggle checkbox
        self.chk_show_counter = QCheckBox()
        self.chk_show_counter.stateChanged.connect(self._change_key_show_counter)
        vbox_tc.addWidget(self.chk_show_counter)
        
        # Counter Autofit checkbox
        self.chk_counter_autofit = QCheckBox()
        self.chk_counter_autofit.stateChanged.connect(self._change_key_counter_autofit)
        vbox_tc.addWidget(self.chk_counter_autofit)
        
        # Simulate Press checkbox
        self.chk_simulate_press = QCheckBox()
        self.chk_simulate_press.stateChanged.connect(self._change_key_simulate_press)
        vbox_tc.addWidget(self.chk_simulate_press)
        
        vbox_editor.addWidget(self.group_text_counter)

        # 5. Rain Effect Group
        self.group_rain_effect = QGroupBox()
        vbox_re = QVBoxLayout(self.group_rain_effect)
        vbox_re.setContentsMargins(10, 12, 10, 10)
        vbox_re.setSpacing(8)

        # Rain Offset Y field
        self.widget_rain_offset_y = QWidget()
        vbox_roy = QVBoxLayout(self.widget_rain_offset_y)
        vbox_roy.setContentsMargins(0, 0, 0, 0)
        vbox_roy.setSpacing(2)
        self.lbl_rain_offset_y = QLabel()
        vbox_roy.addWidget(self.lbl_rain_offset_y)
        self.slider_rain_offset_y = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_rain_offset_y.setRange(-200, 200)
        self.slider_rain_offset_y.valueChanged.connect(self._change_key_rain_offset_y)
        vbox_roy.addWidget(self.slider_rain_offset_y)
        vbox_re.addWidget(self.widget_rain_offset_y)

        # Rain Thickness field
        self.widget_rain_thickness = QWidget()
        vbox_rt = QVBoxLayout(self.widget_rain_thickness)
        vbox_rt.setContentsMargins(0, 0, 0, 0)
        vbox_rt.setSpacing(2)
        self.lbl_rain_thickness = QLabel()
        vbox_rt.addWidget(self.lbl_rain_thickness)
        self.slider_rain_thickness = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_rain_thickness.setRange(-50, 50)
        self.slider_rain_thickness.valueChanged.connect(self._change_key_rain_thickness)
        vbox_rt.addWidget(self.slider_rain_thickness)
        vbox_re.addWidget(self.widget_rain_thickness)
        
        vbox_editor.addWidget(self.group_rain_effect)

        # 6. Layers Group
        self.group_layers = QGroupBox()
        vbox_lay = QVBoxLayout(self.group_layers)
        vbox_lay.setContentsMargins(10, 12, 10, 10)
        vbox_lay.setSpacing(8)
        
        # Key Layer field
        self.widget_key_layer = QWidget()
        vbox_kl = QVBoxLayout(self.widget_key_layer)
        vbox_kl.setContentsMargins(0, 0, 0, 0)
        vbox_kl.setSpacing(2)
        self.lbl_key_layer = QLabel()
        vbox_kl.addWidget(self.lbl_key_layer)
        self.slider_key_layer = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_key_layer.setRange(0, 5)
        self.slider_key_layer.valueChanged.connect(self._change_key_key_layer)
        vbox_kl.addWidget(self.slider_key_layer)
        vbox_lay.addWidget(self.widget_key_layer)

        # Rain Layer field
        self.widget_rain_layer = QWidget()
        vbox_rl = QVBoxLayout(self.widget_rain_layer)
        vbox_rl.setContentsMargins(0, 0, 0, 0)
        vbox_rl.setSpacing(2)
        self.lbl_rain_layer = QLabel()
        vbox_rl.addWidget(self.lbl_rain_layer)
        self.slider_rain_layer = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_rain_layer.setRange(0, 5)
        self.slider_rain_layer.valueChanged.connect(self._change_key_rain_layer)
        vbox_rl.addWidget(self.slider_rain_layer)
        vbox_lay.addWidget(self.widget_rain_layer)
        
        vbox_editor.addWidget(self.group_layers)

        # 7. Visualizer Group
        self.group_visualizer = QGroupBox()
        vbox_viz = QVBoxLayout(self.group_visualizer)
        vbox_viz.setContentsMargins(10, 12, 10, 10)
        vbox_viz.setSpacing(8)

        # Color rows for visualizer
        def _make_viz_color_row(label_attr, btn_attr, signal_slot):
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            hbox = QHBoxLayout(row)
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.setSpacing(8)
            lbl = QLabel()
            lbl.setFixedWidth(52)
            lbl.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
            setattr(self, label_attr, lbl)
            hbox.addWidget(lbl)
            from widgets.color_button import ColorButton
            btn = ColorButton()
            btn.colorChanged.connect(signal_slot)
            setattr(self, btn_attr, btn)
            hbox.addWidget(btn, 1)
            return row

        # Data Source selector (KPS / System Audio)
        self.widget_viz_source = QWidget()
        self.widget_viz_source.setStyleSheet("background: transparent;")
        _vs_row = QHBoxLayout(self.widget_viz_source)
        _vs_row.setContentsMargins(0, 0, 0, 0)
        _vs_row.setSpacing(8)
        self.lbl_viz_source = QLabel()
        self.lbl_viz_source.setFixedWidth(52)
        self.lbl_viz_source.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        _vs_row.addWidget(self.lbl_viz_source)
        self.combo_viz_source = QComboBox()
        self.combo_viz_source.setStyleSheet("""
            QComboBox {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 5px;
                color: #ddd;
                padding: 3px 8px;
                font-size: 12px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #1e1e1e;
                color: #ddd;
                selection-background-color: #2a2a2a;
                border: 1px solid #333;
            }
        """)
        self.combo_viz_source.currentIndexChanged.connect(self._change_viz_source)
        _vs_row.addWidget(self.combo_viz_source, 1)
        vbox_viz.addWidget(self.widget_viz_source)
        self._populate_viz_source_combo()



        vbox_viz.addWidget(_make_viz_color_row('lbl_viz_color_start', 'btn_viz_color_start', self._change_viz_color_start))
        vbox_viz.addWidget(_make_viz_color_row('lbl_viz_color_end',   'btn_viz_color_end',   self._change_viz_color_end))

        # Bar Count
        self.widget_viz_bar_count = QWidget()
        _vbc = QVBoxLayout(self.widget_viz_bar_count)
        _vbc.setContentsMargins(0, 0, 0, 0); _vbc.setSpacing(2)
        self.lbl_viz_bar_count = QLabel()
        _vbc.addWidget(self.lbl_viz_bar_count)
        self.slider_viz_bar_count = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_viz_bar_count.setRange(4, 64)
        self.slider_viz_bar_count.valueChanged.connect(self._change_viz_bar_count)
        _vbc.addWidget(self.slider_viz_bar_count)
        vbox_viz.addWidget(self.widget_viz_bar_count)

        # Max Height
        self.widget_viz_max_height = QWidget()
        _vmh = QVBoxLayout(self.widget_viz_max_height)
        _vmh.setContentsMargins(0, 0, 0, 0); _vmh.setSpacing(2)
        self.lbl_viz_max_height = QLabel()
        _vmh.addWidget(self.lbl_viz_max_height)
        self.slider_viz_max_height = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_viz_max_height.setRange(10, 100)
        self.slider_viz_max_height.valueChanged.connect(self._change_viz_max_height)
        _vmh.addWidget(self.slider_viz_max_height)
        vbox_viz.addWidget(self.widget_viz_max_height)

        # Bar Gap
        self.widget_viz_bar_gap = QWidget()
        _vbg = QVBoxLayout(self.widget_viz_bar_gap)
        _vbg.setContentsMargins(0, 0, 0, 0); _vbg.setSpacing(2)
        self.lbl_viz_bar_gap = QLabel()
        _vbg.addWidget(self.lbl_viz_bar_gap)
        self.slider_viz_bar_gap = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_viz_bar_gap.setRange(0, 8)
        self.slider_viz_bar_gap.valueChanged.connect(self._change_viz_bar_gap)
        _vbg.addWidget(self.slider_viz_bar_gap)
        vbox_viz.addWidget(self.widget_viz_bar_gap)

        # Smoothing
        self.widget_viz_smoothing = QWidget()
        _vs = QVBoxLayout(self.widget_viz_smoothing)
        _vs.setContentsMargins(0, 0, 0, 0); _vs.setSpacing(2)
        self.lbl_viz_smoothing = QLabel()
        _vs.addWidget(self.lbl_viz_smoothing)
        self.slider_viz_smoothing = NonScrollSlider(Qt.Orientation.Horizontal)
        self.slider_viz_smoothing.setRange(0, 95)
        self.slider_viz_smoothing.valueChanged.connect(self._change_viz_smoothing)
        _vs.addWidget(self.slider_viz_smoothing)
        vbox_viz.addWidget(self.widget_viz_smoothing)

        # Mirror checkbox
        self.chk_viz_mirror = QCheckBox()
        self.chk_viz_mirror.stateChanged.connect(self._change_viz_mirror)
        vbox_viz.addWidget(self.chk_viz_mirror)

        # Show name checkbox
        self.chk_viz_show_name = QCheckBox()
        self.chk_viz_show_name.stateChanged.connect(self._change_viz_show_name)
        vbox_viz.addWidget(self.chk_viz_show_name)

        vbox_editor.addWidget(self.group_visualizer)
        
        # Delete Key button
        self.btn_delete_key = QPushButton()
        self.btn_delete_key.setObjectName("btn_delete")
        self.btn_delete_key.clicked.connect(self._delete_current_key)
        vbox_editor.addWidget(self.btn_delete_key)

        
        scroll.setWidget(scroll_content)
        main_vbox.addWidget(scroll)
        
        # Initial state
        self.floating_panel.setFixedWidth(360)
        self.floating_panel.setFixedHeight(440)
        self.group_visualizer.hide()
        
        self.floating_panel.hide()


    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._update_floating_panel_geometry()

    def _update_floating_panel_geometry(self):
        if hasattr(self, 'canvas_wrapper') and self.canvas_wrapper and hasattr(self, 'floating_panel'):
            pw = self.canvas_wrapper.width()
            ph = self.canvas_wrapper.height()
            
            # The floating panel height should be dynamic: ph - 20 (leaving 10px margin top and bottom)
            target_h = max(200, ph - 20)
            self.floating_panel.setFixedHeight(target_h)
            
            if getattr(self.floating_panel, '_custom_pos', None) is not None:
                pos = self.floating_panel._custom_pos
                new_x = max(0, min(pos.x(), pw - self.floating_panel.width()))
                new_y = max(10, min(pos.y(), ph - target_h - 10))
                self.floating_panel.move(new_x, new_y)
                self.floating_panel._custom_pos = QPoint(new_x, new_y)
            else:
                fw = self.floating_panel.width()
                self.floating_panel.move(max(0, pw - fw - 10), 10)




    def keyPressEvent(self, e: QKeyEvent):
        if e.key() == Qt.Key.Key_Delete or e.key() == Qt.Key.Key_Backspace:
            if self._current_edit_key_id:
                self._delete_current_key()
        super().keyPressEvent(e)

    def retranslate_ui(self):
        # Window Title
        self.title_bar.lbl_title.setText("")
        
        # Group Boxes have no titles (clean closed cards)
        
        # Labels and Checkboxes
        self.chk_listen.setText(Trans.t("enable_listener"))
        
        self.chk_grid.setText(Trans.t("show_grid"))
        self.lbl_grid_size.setText(Trans.t("grid_size"))
        grid_val = self._config.get("display_window", {}).get("grid_size", 2)
        self.lbl_grid_val.setText(str(grid_val))
        
        self.chk_rain.setText(Trans.t("enable_rain"))
        self.lbl_rain_speed.setText(Trans.t("rain_speed", "键雨速度:"))
        self.chk_rain_fade.setText(Trans.t("rain_fade", "上升时渐隐"))
        
        self.lbl_key_code.setText(Trans.t("key_code"))
        self.lbl_nickname.setText(Trans.t("nickname", "昵称"))
        
        self.group_basic.setTitle(Trans.t("group_basic", "基本信息"))
        self.group_colors.setTitle(Trans.t("colors_group", "颜色"))
        self.group_shape.setTitle(Trans.t("group_shape", "尺寸与圆角"))
        self.group_text_counter.setTitle(Trans.t("group_text_counter", "文字与计数"))
        self.group_rain_effect.setTitle(Trans.t("group_rain_effect", "键雨效果"))
        self.group_layers.setTitle(Trans.t("group_layers", "图层层级"))
        self.group_visualizer.setTitle(Trans.t("group_visualizer", "可视化均衡器"))
        
        self.lbl_bg_color.setText(Trans.t("bg_color_short", "背景"))
        self.lbl_rain_color.setText(Trans.t("rain_color_short", "键雨"))
        self.lbl_border_color.setText(Trans.t("border_color_short", "边框"))
        self.lbl_text_color.setText(Trans.t("text_color_short", "文字"))
        self.lbl_viz_color_start.setText(Trans.t("viz_color_start", "低频色"))
        self.lbl_viz_color_end.setText(Trans.t("viz_color_end", "高频色"))
        self.chk_text_bold.setText(Trans.t("text_bold"))
        self.btn_delete_key.setText(Trans.t("delete_key"))
        self.btn_add_key.setText(Trans.t("add_key"))
        self.btn_select_profile.setText(Trans.t("select_profile", "选择配置文件"))
        self.btn_bind.setText(Trans.t("bind"))
        self.chk_show_counter.setText(Trans.t("show_counter", "显示按压次数"))
        self.chk_counter_autofit.setText(Trans.t("counter_autofit", "次数自适应大小"))
        self.chk_simulate_press.setText(Trans.t("simulate_press_effect", "更新时模拟按下效果"))
        self.chk_viz_mirror.setText(Trans.t("viz_mirror", "镜像对称显示"))
        self.chk_viz_show_name.setText(Trans.t("viz_show_name", "显示键名文字"))
        self.lbl_viz_bar_count.setText(Trans.t("viz_bar_count", "柱数量 (离散程度):"))
        self.lbl_viz_max_height.setText(Trans.t("viz_max_height", "最大高度 (%):"))
        self.lbl_viz_bar_gap.setText(Trans.t("viz_bar_gap", "柱间距:"))
        self.lbl_viz_smoothing.setText(Trans.t("viz_smoothing", "平滑度 (%):"))
        self.lbl_viz_source.setText(Trans.t("viz_source", "数据来源:"))
        if self.combo_viz_source.count() > 0:
            self.combo_viz_source.setItemText(0, Trans.t("viz_source_kps", "KPS 点击数据"))

        


        if self._current_edit_key_id:
            for k in self._config.get("keys", []):
                if k.get("id") == self._current_edit_key_id:
                    bw = k.get("border_width", 2)
                    cr = k.get("corner_radius", 10)
                    ts = k.get("font_size", 16)
                    toy = k.get("text_offset_y", 0)
                    cs = k.get("counter_size", 14)
                    cox = k.get("counter_offset_x", 0)
                    coy = k.get("counter_offset_y", 20)
                    roy = k.get("rain_offset_y", 0)
                    rt = k.get("rain_thickness", 0)
                    dw_val = k.get("display_width", k.get("width", 60))
                    dh_val = k.get("display_height", k.get("height", 60))
                    kl_val = k.get("key_layer", 0)
                    rl_val = k.get("rain_layer", 0)
                    self.lbl_border_width.setText(f"{Trans.t('border_width')} {bw}px")
                    self.lbl_corner_radius.setText(f"{Trans.t('corner_radius')} {cr}px")
                    self.lbl_text_size.setText(f"{Trans.t('text_size')} {ts}pt")
                    self.lbl_text_offset_y.setText(f"{Trans.t('text_offset_y')} {toy}px")
                    self.lbl_counter_size.setText(f"{Trans.t('counter_size')} {cs}pt")
                    self.lbl_counter_offset_x.setText(f"{Trans.t('counter_offset_x')} {cox}px")
                    self.lbl_counter_offset_y.setText(f"{Trans.t('counter_offset_y')} {coy}px")
                    self.lbl_rain_offset_y.setText(f"{Trans.t('rain_offset_y')} {roy}px")
                    self.lbl_rain_thickness.setText(f"{Trans.t('rain_thickness')} {rt}px")
                    self.lbl_display_width.setText(f"{Trans.t('display_width')} {dw_val}px")
                    self.lbl_display_height.setText(f"{Trans.t('display_height')} {dh_val}px")
                    self.lbl_key_layer.setText(f"{Trans.t('key_layer')} {kl_val}")
                    self.lbl_rain_layer.setText(f"{Trans.t('rain_layer')} {rl_val}")
                    break
        else:
            self.lbl_border_width.setText(Trans.t("border_width"))
            self.lbl_corner_radius.setText(Trans.t("corner_radius"))
            self.lbl_text_size.setText(Trans.t("text_size"))
            self.lbl_text_offset_y.setText(Trans.t("text_offset_y"))
            self.lbl_counter_size.setText(Trans.t("counter_size"))
            self.lbl_counter_offset_x.setText(Trans.t("counter_offset_x"))
            self.lbl_counter_offset_y.setText(Trans.t("counter_offset_y"))
            self.lbl_rain_offset_y.setText(Trans.t("rain_offset_y"))
            self.lbl_rain_thickness.setText(Trans.t("rain_thickness"))
            self.lbl_display_width.setText(Trans.t("display_width"))
            self.lbl_display_height.setText(Trans.t("display_height"))
            self.lbl_key_layer.setText(Trans.t("key_layer"))
            self.lbl_rain_layer.setText(Trans.t("rain_layer"))
            
        self.lbl_editor_key_size.setText(Trans.t("editor_key_size"))
        self.lbl_key_spacing.setText(Trans.t("key_spacing"))
        
        if hasattr(self, 'action_show_gui') and self.action_show_gui:
            self.action_show_gui.setText(Trans.t("tray_open_settings", "打开设置 (Open Settings)"))
        if hasattr(self, 'action_exit') and self.action_exit:
            self.action_exit.setText(Trans.t("tray_exit", "退出 (Exit)"))



    def _on_edit_key_requested(self, key_id):
        if not key_id:
            # Deselect / Hide
            self._current_edit_key_id = None
            self.floating_panel.hide()
            return
            
        self._current_edit_key_id = key_id
        for k in self._config.get("keys", []):
            if k.get("id") == key_id:
                key_type = k.get("key_type", "normal")
                
                # Show/hide relevant widgets
                if key_type == "normal":
                    self.widget_key_code.show()
                    self.widget_nickname.show()
                    self.widget_rain_color.show()
                    self.group_rain_effect.show()
                    self.chk_show_counter.show()
                    self.chk_simulate_press.hide()
                    self.group_visualizer.hide()
                    if hasattr(self, 'widget_rain_layer'):
                        self.widget_rain_layer.show()
                elif key_type == "kps_visualizer":
                    self.widget_key_code.hide()
                    self.widget_nickname.show()
                    self.widget_rain_color.hide()
                    self.group_rain_effect.hide()
                    self.chk_show_counter.hide()
                    self.chk_simulate_press.hide()
                    self.group_visualizer.show()
                    if hasattr(self, 'widget_rain_layer'):
                        self.widget_rain_layer.hide()
                else:
                    self.widget_key_code.hide()
                    self.widget_nickname.show()
                    self.widget_rain_color.hide()
                    self.group_rain_effect.hide()
                    self.chk_show_counter.hide()
                    self.chk_simulate_press.show()
                    self.group_visualizer.hide()
                    if hasattr(self, 'widget_rain_layer'):
                        self.widget_rain_layer.hide()
                
                self._update_floating_panel_geometry()
                
                self.lbl_editing.setText(f"{Trans.t('editing_title')}{k.get('display_name', 'Unknown')}")
                self.edit_key_code.blockSignals(True)
                self.edit_key_code.setText(k.get('key_code', ''))
                self.edit_key_code.blockSignals(False)
                self.edit_nickname.blockSignals(True)
                self.edit_nickname.setText(k.get('nickname', ''))
                self.edit_nickname.blockSignals(False)
                
                self.btn_bg_color._color = k.get("bg_color", [30, 30, 60, 180])
                self.btn_bg_color.update()
                
                self.btn_rain_color._color = k.get("rain_color", [108, 99, 255, 160])
                self.btn_rain_color.update()

                self.btn_border_color._color = k.get("border_color", [108, 99, 255, 255])
                self.btn_border_color.update()

                bw = k.get("border_width", 2)
                self.slider_border_width.blockSignals(True)
                self.slider_border_width.setValue(bw)
                self.slider_border_width.blockSignals(False)
                self.lbl_border_width.setText(f"{Trans.t('border_width')} {bw}px")

                cr = k.get("corner_radius", 10)
                self.slider_corner_radius.blockSignals(True)
                self.slider_corner_radius.setValue(cr)
                self.slider_corner_radius.blockSignals(False)
                self.lbl_corner_radius.setText(f"{Trans.t('corner_radius')} {cr}px")

                self.btn_text_color._color = k.get("text_color", [255, 255, 255, 255])
                self.btn_text_color.update()

                ts = k.get("font_size", 16)
                self.slider_text_size.blockSignals(True)
                self.slider_text_size.setValue(ts)
                self.slider_text_size.blockSignals(False)
                self.lbl_text_size.setText(f"{Trans.t('text_size')} {ts}pt")

                toy = k.get("text_offset_y", 0)
                self.slider_text_offset_y.blockSignals(True)
                self.slider_text_offset_y.setValue(toy)
                self.slider_text_offset_y.blockSignals(False)
                self.lbl_text_offset_y.setText(f"{Trans.t('text_offset_y')} {toy}px")

                self.chk_text_bold.blockSignals(True)
                self.chk_text_bold.setChecked(k.get("font_bold", True))
                self.chk_text_bold.blockSignals(False)
                
                self.chk_show_counter.blockSignals(True)
                self.chk_show_counter.setChecked(k.get("show_counter", False))
                self.chk_show_counter.blockSignals(False)
                
                self.chk_counter_autofit.blockSignals(True)
                self.chk_counter_autofit.setChecked(k.get("counter_autofit", False))
                self.chk_counter_autofit.blockSignals(False)
                
                self.chk_simulate_press.blockSignals(True)
                self.chk_simulate_press.setChecked(k.get("simulate_press", False))
                self.chk_simulate_press.blockSignals(False)
                
                cs = k.get("counter_size", 14)
                self.slider_counter_size.blockSignals(True)
                self.slider_counter_size.setValue(cs)
                self.slider_counter_size.blockSignals(False)
                self.lbl_counter_size.setText(f"{Trans.t('counter_size')} {cs}pt")
                
                cox = k.get("counter_offset_x", 0)
                self.slider_counter_offset_x.blockSignals(True)
                self.slider_counter_offset_x.setValue(cox)
                self.slider_counter_offset_x.blockSignals(False)
                self.lbl_counter_offset_x.setText(f"{Trans.t('counter_offset_x')} {cox}px")

                coy = k.get("counter_offset_y", 20)
                self.slider_counter_offset_y.blockSignals(True)
                self.slider_counter_offset_y.setValue(coy)
                self.slider_counter_offset_y.blockSignals(False)
                self.lbl_counter_offset_y.setText(f"{Trans.t('counter_offset_y')} {coy}px")

                roy = k.get("rain_offset_y", 0)
                self.slider_rain_offset_y.blockSignals(True)
                self.slider_rain_offset_y.setValue(roy)
                self.slider_rain_offset_y.blockSignals(False)
                self.lbl_rain_offset_y.setText(f"{Trans.t('rain_offset_y')} {roy}px")

                rt = k.get("rain_thickness", 0)
                self.slider_rain_thickness.blockSignals(True)
                self.slider_rain_thickness.setValue(rt)
                self.slider_rain_thickness.blockSignals(False)
                self.lbl_rain_thickness.setText(f"{Trans.t('rain_thickness')} {rt}px")

                dw_val = k.get("display_width", k.get("width", 60))
                self.slider_display_width.blockSignals(True)
                self.slider_display_width.setValue(dw_val)
                self.slider_display_width.blockSignals(False)
                self.lbl_display_width.setText(f"{Trans.t('display_width')} {dw_val}px")

                dh_val = k.get("display_height", k.get("height", 60))
                self.slider_display_height.blockSignals(True)
                self.slider_display_height.setValue(dh_val)
                self.slider_display_height.blockSignals(False)
                self.lbl_display_height.setText(f"{Trans.t('display_height')} {dh_val}px")
                
                kl_val = k.get("key_layer", 0)
                self.slider_key_layer.blockSignals(True)
                self.slider_key_layer.setValue(kl_val)
                self.slider_key_layer.blockSignals(False)
                self.lbl_key_layer.setText(f"{Trans.t('key_layer')} {kl_val}")
                
                rl_val = k.get("rain_layer", 0)
                self.slider_rain_layer.blockSignals(True)
                self.slider_rain_layer.setValue(rl_val)
                self.slider_rain_layer.blockSignals(False)
                self.lbl_rain_layer.setText(f"{Trans.t('rain_layer')} {rl_val}")
                
                # Load visualizer values if applicable
                if key_type == 'kps_visualizer':
                    self.btn_viz_color_start._color = k.get('viz_color_start', [108, 99, 255, 220])
                    self.btn_viz_color_start.update()
                    self.btn_viz_color_end._color = k.get('viz_color_end', [255, 80, 120, 220])
                    self.btn_viz_color_end.update()

                    vbc = k.get('viz_bar_count', 16)
                    self.slider_viz_bar_count.blockSignals(True)
                    self.slider_viz_bar_count.setValue(vbc)
                    self.slider_viz_bar_count.blockSignals(False)
                    self.lbl_viz_bar_count.setText(f"{Trans.t('viz_bar_count')} {vbc}")

                    vmh = k.get('viz_max_height', 80)
                    self.slider_viz_max_height.blockSignals(True)
                    self.slider_viz_max_height.setValue(vmh)
                    self.slider_viz_max_height.blockSignals(False)
                    self.lbl_viz_max_height.setText(f"{Trans.t('viz_max_height')} {vmh}%")

                    vbg = k.get('viz_bar_gap', 2)
                    self.slider_viz_bar_gap.blockSignals(True)
                    self.slider_viz_bar_gap.setValue(vbg)
                    self.slider_viz_bar_gap.blockSignals(False)
                    self.lbl_viz_bar_gap.setText(f"{Trans.t('viz_bar_gap')} {vbg}px")

                    vs = k.get('viz_smoothing', 60)
                    self.slider_viz_smoothing.blockSignals(True)
                    self.slider_viz_smoothing.setValue(vs)
                    self.slider_viz_smoothing.blockSignals(False)
                    self.lbl_viz_smoothing.setText(f"{Trans.t('viz_smoothing')} {vs}%")

                    self.chk_viz_mirror.blockSignals(True)
                    self.chk_viz_mirror.setChecked(k.get('viz_mirror', False))
                    self.chk_viz_mirror.blockSignals(False)

                    self.chk_viz_show_name.blockSignals(True)
                    self.chk_viz_show_name.setChecked(k.get('viz_show_name', True))
                    self.chk_viz_show_name.blockSignals(False)

                    self._populate_viz_source_combo()
                    src = k.get('viz_source', 'kps')
                    dev_name = k.get('viz_device_name', 'default')
                    self.combo_viz_source.blockSignals(True)
                    if src == 'kps':
                        self.combo_viz_source.setCurrentIndex(0)
                    else:
                        found = False
                        for idx in range(1, self.combo_viz_source.count()):
                            if self.combo_viz_source.itemData(idx) == dev_name:
                                self.combo_viz_source.setCurrentIndex(idx)
                                found = True
                                break
                        if not found:
                            self.combo_viz_source.addItem(f"{dev_name} (Offline)", dev_name)
                            self.combo_viz_source.setCurrentIndex(self.combo_viz_source.count() - 1)
                    self.combo_viz_source.blockSignals(False)


                self.floating_panel.show()
                self.floating_panel.raise_()
                
                # Bring focus to main window to ensure DEL key capture works
                self.setFocus()
                break


    def _change_key_code(self, text):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["key_code"] = text.lower()
                k["display_name"] = text.upper()
                ConfigManager.save()
                
                self.lbl_editing.setText(f"{Trans.t('editing_title')}{k.get('display_name', 'Unknown')}")
                
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_nickname(self, text):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["nickname"] = text
                ConfigManager.save()
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break

    def _start_bind(self):
        self.btn_bind.setText(Trans.t("listening"))
        self.btn_bind.setEnabled(False)
        events.key_pressed.connect(self._on_bind_key)

    def _on_bind_key(self, key_code):
        events.key_pressed.disconnect(self._on_bind_key)
        self.btn_bind.setText(Trans.t("bind"))
        self.btn_bind.setEnabled(True)
        self.edit_key_code.setText(key_code)

    def _change_key_bg_color(self, color):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["bg_color"] = color
                ConfigManager.save()
                
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_rain_color(self, color):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["rain_color"] = color
                ConfigManager.save()
                
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_border_color(self, color):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["border_color"] = color
                ConfigManager.save()
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_border_width(self, val):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["border_width"] = val
                self.lbl_border_width.setText(f"{Trans.t('border_width')} {val}px")
                ConfigManager.save()
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_corner_radius(self, val):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["corner_radius"] = val
                self.lbl_corner_radius.setText(f"{Trans.t('corner_radius')} {val}px")
                ConfigManager.save()
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_text_color(self, color):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["text_color"] = color
                ConfigManager.save()
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_text_size(self, val):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["font_size"] = val
                self.lbl_text_size.setText(f"{Trans.t('text_size')} {val}pt")
                ConfigManager.save()
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_text_bold(self, state):
        if not self._current_edit_key_id: return
        is_bold = self.chk_text_bold.isChecked()
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["font_bold"] = is_bold
                ConfigManager.save()
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_show_counter(self, state):
        if not self._current_edit_key_id: return
        is_show = self.chk_show_counter.isChecked()
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["show_counter"] = is_show
                ConfigManager.save()
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_counter_autofit(self, state):
        if not self._current_edit_key_id: return
        is_autofit = self.chk_counter_autofit.isChecked()
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["counter_autofit"] = is_autofit
                ConfigManager.save()
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_simulate_press(self, state):
        if not self._current_edit_key_id: return
        is_sim = self.chk_simulate_press.isChecked()
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["simulate_press"] = is_sim
                ConfigManager.save()
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_counter_size(self, val):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["counter_size"] = val
                self.lbl_counter_size.setText(f"{Trans.t('counter_size')} {val}pt")
                ConfigManager.save()
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_counter_offset_x(self, val):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["counter_offset_x"] = val
                self.lbl_counter_offset_x.setText(f"{Trans.t('counter_offset_x')} {val}px")
                ConfigManager.save()
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_rain_offset_y(self, val):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["rain_offset_y"] = val
                self.lbl_rain_offset_y.setText(f"{Trans.t('rain_offset_y')} {val}px")
                ConfigManager.save()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_rain_thickness(self, val):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["rain_thickness"] = val
                self.lbl_rain_thickness.setText(f"{Trans.t('rain_thickness')} {val}px")
                ConfigManager.save()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_display_width(self, val):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["display_width"] = val
                self.lbl_display_width.setText(f"{Trans.t('display_width')} {val}px")
                ConfigManager.save()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_display_height(self, val):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["display_height"] = val
                self.lbl_display_height.setText(f"{Trans.t('display_height')} {val}px")
                ConfigManager.save()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_key_layer(self, val):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["key_layer"] = val
                self.lbl_key_layer.setText(f"{Trans.t('key_layer')} {val}")
                ConfigManager.save()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_rain_layer(self, val):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["rain_layer"] = val
                self.lbl_rain_layer.setText(f"{Trans.t('rain_layer')} {val}")
                ConfigManager.save()
                events.config_changed.emit(ConfigManager.load())
                break

    # ── Visualizer change slots ───────────────────────────────────────────

    def _save_viz_field(self, field, value):
        """Helper: save a viz_* field for the current key and repaint."""
        if not self._current_edit_key_id:
            return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k[field] = value
                ConfigManager.save()
                events.config_changed.emit(ConfigManager.load())
                self.grid_canvas.reload_keys()
                break

    def _change_viz_color_start(self, color):
        self._save_viz_field("viz_color_start", color)

    def _change_viz_color_end(self, color):
        self._save_viz_field("viz_color_end", color)

    def _change_viz_bar_count(self, val):
        self.lbl_viz_bar_count.setText(f"{Trans.t('viz_bar_count')} {val}")
        self._save_viz_field("viz_bar_count", val)

    def _change_viz_max_height(self, val):
        self.lbl_viz_max_height.setText(f"{Trans.t('viz_max_height')} {val}%")
        self._save_viz_field("viz_max_height", val)

    def _change_viz_bar_gap(self, val):
        self.lbl_viz_bar_gap.setText(f"{Trans.t('viz_bar_gap')} {val}px")
        self._save_viz_field("viz_bar_gap", val)

    def _change_viz_smoothing(self, val):
        self.lbl_viz_smoothing.setText(f"{Trans.t('viz_smoothing')} {val}%")
        self._save_viz_field("viz_smoothing", val)

    def _change_viz_mirror(self, state):
        self._save_viz_field("viz_mirror", self.chk_viz_mirror.isChecked())

    def _change_viz_show_name(self, state):
        self._save_viz_field("viz_show_name", self.chk_viz_show_name.isChecked())

    def _populate_viz_source_combo(self):
        self.combo_viz_source.blockSignals(True)
        # Keep track of selected device
        selected_data = self.combo_viz_source.currentData()
        self.combo_viz_source.clear()
        
        # Add KPS
        self.combo_viz_source.addItem(Trans.t("viz_source_kps", "KPS 点击数据"), "kps")
        
        # Add Audio devices
        from core.audio_capture import AudioCapture
        devices = AudioCapture.get_loopback_devices()
        for d in devices:
            self.combo_viz_source.addItem(d['name'], d['name'])
            
        # Try to restore selection
        if selected_data is not None:
            idx = self.combo_viz_source.findData(selected_data)
            if idx >= 0:
                self.combo_viz_source.setCurrentIndex(idx)
        self.combo_viz_source.blockSignals(False)

    def _change_viz_source(self, idx):
        data = self.combo_viz_source.itemData(idx)
        if data == "kps":
            self._save_viz_field("viz_source", "kps")
            self._save_viz_field("viz_device_name", "default")
        else:
            self._save_viz_field("viz_source", "audio")
            self._save_viz_field("viz_device_name", data)
            # Proactively start audio capture if user switches to audio
            try:
                from core.audio_capture import AudioCapture
                AudioCapture.instance().start(data)
            except Exception:
                pass


    def _change_key_text_offset_y(self, val):


        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["text_offset_y"] = val
                self.lbl_text_offset_y.setText(f"{Trans.t('text_offset_y')} {val}px")
                ConfigManager.save()
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break

    def _change_key_counter_offset_y(self, val):
        if not self._current_edit_key_id: return
        for k in self._config.get("keys", []):
            if k.get("id") == self._current_edit_key_id:
                k["counter_offset_y"] = val
                self.lbl_counter_offset_y.setText(f"{Trans.t('counter_offset_y')} {val}px")
                ConfigManager.save()
                self.grid_canvas.reload_keys()
                events.config_changed.emit(ConfigManager.load())
                break
    def _update_editor_key_size_label(self, val):
        self.lbl_editor_key_size_val.setText(str(val))

    def _on_editor_key_size_released(self):
        val = self.slider_editor_key_size.value()
        self._config.setdefault("display_window", {})["editor_key_size"] = val
        ConfigManager.save()
        self.grid_canvas.reload_keys()
        events.config_changed.emit(ConfigManager.load())

    def _update_key_spacing_label(self, val):
        self.lbl_key_spacing_val.setText(str(val))
        self._config.setdefault("display_window", {})["key_spacing"] = val
        events.config_changed.emit(self._config)

    def _on_key_spacing_released(self):
        val = self.slider_key_spacing.value()
        self._config.setdefault("display_window", {})["key_spacing"] = val
        ConfigManager.save()
        events.config_changed.emit(ConfigManager.load())
    def _delete_current_key(self):
        self._delete_selected_keys()

    def _delete_selected_keys(self):
        selected_ids = [kw.key_id for kw in self.grid_canvas._key_widgets if kw.is_selected]
        if not selected_ids and self._current_edit_key_id:
            selected_ids = [self._current_edit_key_id]
            
        if not selected_ids:
            return
            
        keys = self._config.get("keys", [])
        self._config["keys"] = [k for k in keys if k.get("id") not in selected_ids]
        ConfigManager.save()
        
        self.grid_canvas.reload_keys()
        events.config_changed.emit(ConfigManager.load())
        
        if self._current_edit_key_id in selected_ids:
            self.floating_panel.hide()
            self._current_edit_key_id = None

    def _toggle_listener(self, state):
        if state == Qt.CheckState.Checked.value:
            self.listener.start()
        else:
            self.listener.stop()

    def _toggle_grid(self, state):
        self._config.setdefault("display_window", {})["grid_visible"] = (state == Qt.CheckState.Checked.value)
        ConfigManager.save()
        self.grid_canvas.update()
        
    def _update_grid_label(self, val):
        self.lbl_grid_val.setText(str(val))

    def _on_grid_slider_released(self):
        val = self.slider_grid.value()
        self._change_grid_size(val)

    def _change_grid_size(self, val):
        old_grid = self._config.get("display_window", {}).get("grid_size", 2)
        new_grid = val
        self._config.setdefault("display_window", {})["grid_size"] = new_grid
        
        # Snap all existing key positions to the new grid division index
        for k in self._config.get("keys", []):
            if old_grid == 0:
                pixel_x = k.get("x", 0)
                pixel_y = k.get("y", 0)
            else:
                pixel_x = k.get("x", 0) * (60 / old_grid)
                pixel_y = k.get("y", 0) * (60 / old_grid)
                
            if new_grid == 0:
                k["x"] = int(round(pixel_x))
                k["y"] = int(round(pixel_y))
            else:
                k["x"] = int(round(pixel_x / (60 / new_grid)))
                k["y"] = int(round(pixel_y / (60 / new_grid)))
            
        ConfigManager.save()
        self.grid_canvas.reload_keys()
        events.config_changed.emit(ConfigManager.load())
        
    def _toggle_rain(self, state):
        self._config.setdefault("rain", {})["enabled"] = (state == Qt.CheckState.Checked.value or state == 2)
        ConfigManager.save()
        events.config_changed.emit(ConfigManager.load())

    def _update_rain_speed_label(self, val):
        self.lbl_rain_speed_val.setText(str(val))

    def _on_rain_speed_released(self):
        val = self.slider_rain_speed.value()
        rain_cfg = self._config.setdefault("rain", {})
        rain_cfg["speed_up"] = val
        rain_cfg["grow_speed"] = val
        ConfigManager.save()
        events.config_changed.emit(ConfigManager.load())

    def _toggle_rain_fade(self, state):
        enabled = (state == Qt.CheckState.Checked.value or state == 2)
        self._config.setdefault("rain", {})["fade_enabled"] = enabled
        ConfigManager.save()
        events.config_changed.emit(ConfigManager.load())

    def _show_settings_dialog(self):
        from widgets.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self, self.display_win, self)
        dialog.exec()

    def _generate_unique_id(self):
        existing_ids = {k.get("id") for k in self._config.get("keys", [])}
        counter = 1
        while True:
            new_id = f"key_{counter:03d}"
            if new_id not in existing_ids:
                return new_id
            counter += 1

    def _add_key(self):
        dialog = AddKeyDialog(self)
        dialog.move(self.geometry().center() - dialog.rect().center())
        
        res = dialog.exec()
        if res == QDialog.DialogCode.Accepted:
            key_type = getattr(dialog, 'selected_key_type', 'normal')
            key_code = dialog.selected_key_code
            
            if key_type == 'normal' and not key_code:
                return
                
            new_key = copy.deepcopy(ConfigManager.default_keys()[0])
            new_key['id'] = self._generate_unique_id()
            new_key['key_type'] = key_type
            
            if key_type == 'normal':
                new_key['display_name'] = key_code.upper()
                new_key['key_code'] = key_code
            elif key_type == 'kps':
                new_key['display_name'] = 'KPS'
                new_key['key_code'] = ''
            elif key_type == 'total_clicks':
                new_key['display_name'] = 'TOTAL'
                new_key['key_code'] = ''
            elif key_type == 'active_keys_count':
                new_key['display_name'] = 'ACTIVE'
                new_key['key_code'] = ''
            elif key_type == 'kps_visualizer':
                new_key['display_name'] = 'VIZ'
                new_key['key_code'] = ''
                new_key['viz_bar_count'] = 16
                new_key['viz_max_height'] = 80
                new_key['viz_color_start'] = [108, 99, 255, 220]
                new_key['viz_color_end'] = [255, 80, 120, 220]
                new_key['viz_bar_gap'] = 2
                new_key['viz_smoothing'] = 60
                new_key['viz_mirror'] = False
                new_key['viz_show_name'] = True
                new_key['viz_source'] = 'kps'
                new_key['viz_device_name'] = 'default'

                
            grid_size = self._config.get("display_window", {}).get("grid_size", 2)
            if grid_size == 0:
                new_key['x'] = 50
                new_key['y'] = 50
            else:
                new_key['x'] = int(round(50 / (60 / grid_size)))
                new_key['y'] = int(round(50 / (60 / grid_size)))
            
            self._config.setdefault('keys', []).append(new_key)
            ConfigManager.save(self._config)
            
            self.grid_canvas.reload_keys()
            events.config_changed.emit(ConfigManager.load())

    def _show_profile_dialog(self):
        dialog = ProfileSelectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._reload_ui_from_config()
            
    def _reload_ui_from_config(self):
        self._config = ConfigManager.load()
        
        # Block signals temporarily to prevent event loops
        self.slider_grid.blockSignals(True)
        self.chk_grid.blockSignals(True)
        self.chk_listen.blockSignals(True)
        self.slider_editor_key_size.blockSignals(True)
        self.slider_key_spacing.blockSignals(True)
        self.chk_rain.blockSignals(True)
        self.slider_rain_speed.blockSignals(True)
        self.chk_rain_fade.blockSignals(True)
        
        grid_val = max(1, self._config.get("display_window", {}).get("grid_size", 2))
        self.slider_grid.setValue(grid_val)
        self.lbl_grid_val.setText(str(grid_val))
        
        eks_val = self._config.get("display_window", {}).get("editor_key_size", 60)
        self.slider_editor_key_size.setValue(eks_val)
        self.lbl_editor_key_size_val.setText(str(eks_val))
        
        ks_val = self._config.get("display_window", {}).get("key_spacing", 0)
        self.slider_key_spacing.setValue(ks_val)
        self.lbl_key_spacing_val.setText(str(ks_val))
        
        self.chk_grid.setChecked(self._config.get("display_window", {}).get("grid_visible", True))
        self.chk_listen.setChecked(self._config.get("enable_listener", True))
        
        self.chk_rain.setChecked(self._config.get("rain", {}).get("enabled", True))
        rain_speed_val = self._config.get("rain", {}).get("speed_up", 6)
        self.slider_rain_speed.setValue(rain_speed_val)
        self.lbl_rain_speed_val.setText(str(rain_speed_val))
        self.chk_rain_fade.setChecked(self._config.get("rain", {}).get("fade_enabled", True))
        
        self.slider_grid.blockSignals(False)
        self.chk_grid.blockSignals(False)
        self.chk_listen.blockSignals(False)
        self.slider_editor_key_size.blockSignals(False)
        self.slider_key_spacing.blockSignals(False)
        self.chk_rain.blockSignals(False)
        self.slider_rain_speed.blockSignals(False)
        self.chk_rain_fade.blockSignals(False)
        
        self.grid_canvas.reload_keys()
        self.retranslate_ui()
        
    def _copy_key(self):
        selected_ids = [kw.key_id for kw in self.grid_canvas._key_widgets if kw.is_selected]
        if not selected_ids and self._current_edit_key_id:
            selected_ids = [self._current_edit_key_id]
            
        if not selected_ids:
            return
            
        self._clipboard_keys_data = []
        for k in self._config.get("keys", []):
            if k.get("id") in selected_ids:
                self._clipboard_keys_data.append(copy.deepcopy(k))

    def _cut_key(self):
        selected_ids = [kw.key_id for kw in self.grid_canvas._key_widgets if kw.is_selected]
        if not selected_ids and self._current_edit_key_id:
            selected_ids = [self._current_edit_key_id]
            
        if not selected_ids:
            return
            
        self._clipboard_keys_data = []
        for k in self._config.get("keys", []):
            if k.get("id") in selected_ids:
                self._clipboard_keys_data.append(copy.deepcopy(k))
                
        if self._clipboard_keys_data:
            keys = self._config.get("keys", [])
            self._config["keys"] = [k for k in keys if k.get("id") not in selected_ids]
            ConfigManager.save()
            
            self.grid_canvas.reload_keys()
            events.config_changed.emit(ConfigManager.load())
            
            if self._current_edit_key_id in selected_ids:
                self.floating_panel.hide()
                self._current_edit_key_id = None

    def _paste_key(self):
        copied_keys = getattr(self, "_clipboard_keys_data", None)
        if not copied_keys:
            single_key = getattr(self, "_clipboard_key_data", None)
            if single_key:
                copied_keys = [single_key]
                
        if not copied_keys:
            return
            
        from PyQt6.QtGui import QCursor
        mouse_pos_global = QCursor.pos()
        canvas_pos = self.grid_canvas.mapFromGlobal(mouse_pos_global)
        
        grid_size = self._config.get("display_window", {}).get("grid_size", 2)
        sx, sy = self.grid_canvas._get_scale()
        
        avg_x = sum(k.get("x", 0) for k in copied_keys) / len(copied_keys)
        avg_y = sum(k.get("y", 0) for k in copied_keys) / len(copied_keys)
        
        is_over_canvas = self.grid_canvas.rect().contains(canvas_pos)
        
        for kw in self.grid_canvas._key_widgets:
            kw.is_selected = False
            kw.update()
            
        pasted_ids = []
        for k in copied_keys:
            new_key = copy.deepcopy(k)
            new_key["id"] = self._generate_unique_id()
            pasted_ids.append(new_key["id"])
            
            old_x = k.get("x", 0)
            old_y = k.get("y", 0)
            
            if is_over_canvas:
                if grid_size == 0:
                    cursor_grid_x = canvas_pos.x() / sx
                    cursor_grid_y = canvas_pos.y() / sy
                    dx = cursor_grid_x - avg_x
                    dy = cursor_grid_y - avg_y
                    new_key["x"] = int(old_x + dx)
                    new_key["y"] = int(old_y + dy)
                else:
                    grid_unit_x = (60 / grid_size) * sx
                    grid_unit_y = (60 / grid_size) * sy
                    cursor_grid_x = canvas_pos.x() / grid_unit_x
                    cursor_grid_y = canvas_pos.y() / grid_unit_y
                    dx = cursor_grid_x - avg_x
                    dy = cursor_grid_y - avg_y
                    new_key["x"] = int(round(old_x + dx))
                    new_key["y"] = int(round(old_y + dy))
            else:
                shift = 1 if grid_size > 0 else 10
                new_key["x"] = old_x + shift
                new_key["y"] = old_y + shift
                
            self._config.setdefault('keys', []).append(new_key)
            
        ConfigManager.save()
        self.grid_canvas.reload_keys()
        
        for kw in self.grid_canvas._key_widgets:
            if kw.key_id in pasted_ids:
                kw.is_selected = True
                kw.update()
                
        events.config_changed.emit(ConfigManager.load())
        
        if len(pasted_ids) == 1:
            self._on_edit_key_requested(pasted_ids[0])
        else:
            self.floating_panel.hide()
            self._current_edit_key_id = None

    def showEvent(self, e):
        super().showEvent(e)
        if getattr(self, '_first_show', True):
            self._first_show = False
            if ConfigManager._profile_missing_alert:
                Toast(self, Trans.t("profile_not_found", "没有扫描到配置文件"), 3000)
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(3000, self._show_profile_dialog)

    def closeEvent(self, event):
        # Save window geometry
        cw_cfg = self._config.setdefault("control_window", {})
        cw_cfg["x"] = self.x()
        cw_cfg["y"] = self.y()
        cw_cfg["width"] = self.width()
        cw_cfg["height"] = self.height()
        
        # Save splitter sizes
        if hasattr(self, 'splitter'):
            cw_cfg["splitter_sizes"] = self.splitter.sizes()
            
        ConfigManager.save()
        
        if getattr(self, "_force_close", False):
            event.accept()
        else:
            event.ignore()
            self.hide()
