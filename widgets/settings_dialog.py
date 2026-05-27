import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QWidget, QButtonGroup, QCheckBox, QLineEdit, QGroupBox)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QGuiApplication
from core.config_manager import ConfigManager
from core.i18n import Trans

class SettingsDialog(QDialog):
    def __init__(self, control_win, display_win, parent=None):
        super().__init__(parent)
        self.control_win = control_win
        self.display_win = display_win
        
        self.setWindowTitle(Trans.t("settings", "设置"))
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setStyleSheet("""
            QDialog {
                background-color: transparent;
            }
            #DialogBg {
                background-color: #121212;
                border: 1px solid #333;
                border-radius: 12px;
            }
            QLabel {
                color: #e5e5e5;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                color: #e5e5e5;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #262626;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 3px;
            }
            QPushButton {
                background-color: #1a1a1a;
                border: 1px solid #2e2e2e;
                border-radius: 8px;
                color: #d0d0d0;
                padding: 8px 18px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 13px;
                font-weight: 500;
                letter-spacing: 0.3px;
            }
            QPushButton:hover {
                background-color: #252525;
                border-color: #ffffff;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #111111;
            }
            QPushButton:checked {
                background-color: #ffffff;
                border-color: #ffffff;
                color: #121212;
                font-weight: bold;
            }
            QCheckBox {
                color: #e5e5e5;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }
            QLineEdit {
                background-color: #0a0a0a;
                border: 1px solid #262626;
                border-radius: 4px;
                color: #ffffff;
                padding: 4px 8px;
            }
        """)
        
        self.resize(520, 620)
        if parent:
            self.move(parent.geometry().center() - self.rect().center())
            
        self._is_moving = False
        self._drag_start_pos = None
        self._drag_start_geo = None
        
        # Dialog outer layout
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        
        # Main wrapper for rounded corners
        self.main_wrapper = QWidget(self)
        self.main_wrapper.setObjectName("DialogBg")
        outer_layout.addWidget(self.main_wrapper)
        
        layout = QVBoxLayout(self.main_wrapper)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        self.lbl_title = QLabel(Trans.t("settings", "设置"))
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        layout.addWidget(self.lbl_title)
        
        # 1. Language Section
        self.lbl_lang = QLabel()
        layout.addWidget(self.lbl_lang)
        
        self.widget_lang = QWidget()
        hbox_lang = QHBoxLayout(self.widget_lang)
        hbox_lang.setContentsMargins(0, 0, 0, 0)
        self.btn_group_lang = QButtonGroup(self)
        
        self.btn_zh = QPushButton("简体中文")
        self.btn_zh.setCheckable(True)
        self.btn_group_lang.addButton(self.btn_zh, 0)
        hbox_lang.addWidget(self.btn_zh)
        
        self.btn_en = QPushButton("English")
        self.btn_en.setCheckable(True)
        self.btn_group_lang.addButton(self.btn_en, 1)
        hbox_lang.addWidget(self.btn_en)
        
        config = ConfigManager.load()
        cur_lang = Trans.get_language()
        if cur_lang == "zh_CN":
            self.btn_zh.setChecked(True)
        else:
            self.btn_en.setChecked(True)
            
        self.btn_group_lang.idClicked.connect(self._change_language_btn)
        layout.addWidget(self.widget_lang)
        
        # 2. Monitor Section
        self.lbl_monitor = QLabel()
        layout.addWidget(self.lbl_monitor)
        
        self.widget_monitor = QWidget()
        hbox_monitor = QHBoxLayout(self.widget_monitor)
        hbox_monitor.setContentsMargins(0, 0, 0, 0)
        self.btn_group_monitor = QButtonGroup(self)
        
        screens = QGuiApplication.screens()
        cur_monitor = config.get("display_window", {}).get("monitor", 0)
        
        for i, s in enumerate(screens):
            btn = QPushButton(f"Monitor {i+1}")
            btn.setCheckable(True)
            if i == cur_monitor:
                btn.setChecked(True)
            self.btn_group_monitor.addButton(btn, i)
            hbox_monitor.addWidget(btn)
            
        self.btn_group_monitor.idClicked.connect(self._change_monitor)
        layout.addWidget(self.widget_monitor)
        
        # 2.5 Autostart Section
        self.chk_autostart = QCheckBox()
        self.chk_autostart.setChecked(config.get("autostart_enabled", False))
        self.chk_autostart.stateChanged.connect(self._toggle_autostart)
        layout.addWidget(self.chk_autostart)
        
        # 3. Associated Startup Section
        self.group_associated = QGroupBox()
        vbox_associated = QVBoxLayout(self.group_associated)
        self.chk_associated = QCheckBox()
        self.chk_associated.setChecked(config.get("associated_startup_enabled", False))
        self.chk_associated.stateChanged.connect(self._toggle_associated_startup)
        vbox_associated.addWidget(self.chk_associated)
        
        from PyQt6.QtWidgets import QListWidget, QListWidgetItem
        self.list_apps = QListWidget()
        self.list_apps.setFixedHeight(120)
        self.list_apps.setStyleSheet("""
            QListWidget {
                background-color: #0a0a0a;
                border: 1px solid #262626;
                border-radius: 6px;
                color: #ffffff;
                padding: 4px;
            }
            QListWidget::item {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QListWidget::item:hover {
                background-color: #222222;
            }
            QListWidget::item:selected {
                background-color: #ffffff;
                color: #000000;
            }
        """)
        vbox_associated.addWidget(self.list_apps)
        
        hbox_btn = QHBoxLayout()
        self.btn_add_app = QPushButton()
        self.btn_add_app.clicked.connect(self._add_associated_app)
        hbox_btn.addWidget(self.btn_add_app)
        
        self.btn_remove_app = QPushButton()
        self.btn_remove_app.clicked.connect(self._remove_associated_app)
        hbox_btn.addWidget(self.btn_remove_app)
        
        vbox_associated.addLayout(hbox_btn)
        
        self.app_paths = config.get("associated_app_paths", [])
        if not self.app_paths and config.get("associated_app_path"):
            self.app_paths = [config.get("associated_app_path")]
            
        self._populate_app_list()
        layout.addWidget(self.group_associated)
        
        layout.addStretch()
        
        # Powered By Label
        self.lbl_power = QLabel("Powered By Mercy's Bug")
        self.lbl_power.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_power.setStyleSheet("color: #555555; font-size: 10px; margin-bottom: 2px;")
        layout.addWidget(self.lbl_power)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_close = QPushButton()
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)
        
        self.retranslate_ui()
        
        QGuiApplication.instance().installEventFilter(self)

    def retranslate_ui(self):
        self.lbl_title.setText(Trans.t("settings", "设置"))
        self.lbl_lang.setText(Trans.t("language", "语言 (Language)"))
        self.lbl_monitor.setText(Trans.t("select_monitor", "选择显示器"))
        self.chk_autostart.setText(Trans.t("enable_autostart", "开机自启"))
        self.group_associated.setTitle(Trans.t("associated_startup", "关联启动"))
        self.chk_associated.setText(Trans.t("enable_associated", "启用关联启动"))
        self.btn_add_app.setText(Trans.t("add_app", "添加应用"))
        self.btn_remove_app.setText(Trans.t("remove_selected", "删除选中"))
        self.btn_close.setText(Trans.t("close", "关闭"))

    def eventFilter(self, obj, event):
        from PyQt6.QtWidgets import QWidget
        if isinstance(obj, QWidget) and obj.window() == self:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                pos = self.mapFromGlobal(event.globalPosition().toPoint())
                if self.main_wrapper.rect().contains(pos) and (obj == self.main_wrapper or obj == self.lbl_title):
                    self._is_moving = True
                    self._drag_start_pos = event.globalPosition()
                    self._drag_start_geo = self.geometry()
                    return True
            elif event.type() == QEvent.Type.MouseMove and self._is_moving:
                delta = event.globalPosition() - self._drag_start_pos
                self.move(self._drag_start_geo.x() + int(delta.x()), self._drag_start_geo.y() + int(delta.y()))
                return True
            elif event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                if self._is_moving:
                    self._is_moving = False
                    return True
        return super().eventFilter(obj, event)

    def _change_monitor(self, idx):
        screens = QGuiApplication.screens()
        if idx < len(screens):
            geo = screens[idx].geometry()
            self.display_win.move(geo.x() + 100, geo.y() + 100)
            
            cfg = ConfigManager.load()
            cfg.setdefault("display_window", {})["monitor"] = idx
            cfg["display_window"]["x"] = geo.x() + 100
            cfg["display_window"]["y"] = geo.y() + 100
            ConfigManager.save(cfg, save_profile=False)
            
            from core.events import events
            events.config_changed.emit(cfg)

    def _change_language_btn(self, btn_id):
        lang = "zh_CN" if btn_id == 0 else "en_US"
        Trans.set_language(lang)
        
        cfg = ConfigManager.load()
        cfg["language"] = lang
        ConfigManager.save(cfg, save_profile=False)
        
        self.retranslate_ui()
        if self.control_win:
            self.control_win.retranslate_ui()
            if hasattr(self.control_win, "grid_canvas") and self.control_win.grid_canvas:
                self.control_win.grid_canvas.reload_keys()

    def _toggle_associated_startup(self, state):
        enabled = (state == Qt.CheckState.Checked.value or state == 2)
        cfg = ConfigManager.load()
        cfg["associated_startup_enabled"] = enabled
        ConfigManager.save(cfg, save_profile=False)
        
        autostart = cfg.get("autostart_enabled", False)
        from core.startup_helper import set_windows_startup
        set_windows_startup(autostart, silent=enabled)

    def _toggle_autostart(self, state):
        enabled = (state == Qt.CheckState.Checked.value or state == 2)
        cfg = ConfigManager.load()
        cfg["autostart_enabled"] = enabled
        ConfigManager.save(cfg, save_profile=False)
        
        associated = cfg.get("associated_startup_enabled", False)
        from core.startup_helper import set_windows_startup
        set_windows_startup(enabled, silent=associated)

    def _populate_app_list(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QListWidgetItem
        self.list_apps.clear()
        for path in self.app_paths:
            item = QListWidgetItem(os.path.basename(path))
            item.setToolTip(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.list_apps.addItem(item)

    def _add_associated_app(self):
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            Trans.t("select_exe_title", "选择关联启动程序"),
            "",
            "Executable Files (*.exe);;All Files (*)"
        )
        if file_path:
            if file_path not in self.app_paths:
                self.app_paths.append(file_path)
                cfg = ConfigManager.load()
                cfg["associated_app_paths"] = self.app_paths
                if self.app_paths:
                    cfg["associated_app_path"] = self.app_paths[0]
                ConfigManager.save(cfg, save_profile=False)
                self._populate_app_list()

    def _remove_associated_app(self):
        current_item = self.list_apps.currentItem()
        if current_item:
            from PyQt6.QtCore import Qt
            full_path = current_item.data(Qt.ItemDataRole.UserRole)
            if full_path in self.app_paths:
                self.app_paths.remove(full_path)
                cfg = ConfigManager.load()
                cfg["associated_app_paths"] = self.app_paths
                cfg["associated_app_path"] = self.app_paths[0] if self.app_paths else ""
                ConfigManager.save(cfg, save_profile=False)
                self._populate_app_list()
