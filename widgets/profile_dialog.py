import os
import json
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, 
                             QPushButton, QHBoxLayout, QWidget, QMessageBox, QAbstractItemView,
                             QMenu)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from core.config_manager import ConfigManager
from core.events import events
from core.i18n import Trans

class ProfileSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(Trans.t("select_profile", "选择配置文件"))
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setStyleSheet("""
            QDialog {
                background-color: transparent;
            }
            #DialogBg {
                background-color: #0d0d0d;
                border: 1px solid #222222;
                border-radius: 16px;
            }
            QListWidget {
                background-color: #050505;
                border: 1px solid #1a1a1a;
                border-radius: 10px;
                color: #e5e5e5;
                padding: 8px;
                outline: none;
            }
            QListWidget::item {
                background-color: #111111;
                border: 1px solid #222222;
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 6px;
                color: #888888;
                outline: none;
            }
            QListWidget::item:hover {
                background-color: #222222;
                border-color: #444444;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #333333;
                border: 1px solid #ffffff;
                color: #ffffff;
            }
        """)
        
        # Load size and position
        self._config = ConfigManager.load()
        pd_cfg = self._config.get("profile_dialog", {})
        default_w = 400
        default_h = 500
        w = pd_cfg.get("width", default_w)
        h = pd_cfg.get("height", default_h)
        
        if "x" in pd_cfg and "y" in pd_cfg:
            self.setGeometry(pd_cfg["x"], pd_cfg["y"], w, h)
        else:
            self.resize(w, h)
            if parent:
                # Center on parent
                self.move(parent.geometry().center() - self.rect().center())
                
        self.setMinimumSize(300, 400)
        self.setMouseTracking(True)
        self._is_resizing = False
        self._is_moving = False
        self._resize_edge = []
        self._drag_start_pos = None
        self._drag_start_geo = None
        self._resize_margin = 8
        
        # Dialog outer layout
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        
        # Main layout wrapper for rounded corners
        self.main_wrapper = QWidget(self)
        self.main_wrapper.setObjectName("DialogBg")
        outer_layout.addWidget(self.main_wrapper)
        
        layout = QVBoxLayout(self.main_wrapper)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Title
        self.lbl_title = QLabel(Trans.t("select_profile", "选择配置文件"))
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        layout.addWidget(self.lbl_title)
        
        # List
        self.list_widget = QListWidget()
        self.list_widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.itemChanged.connect(self._on_item_changed)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.list_widget.installEventFilter(self)
        layout.addWidget(self.list_widget)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton(Trans.t("close", "关闭"))
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: none;
                border-radius: 16px;
                color: #000000;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 24px;
                min-width: 90px;
            }
            QPushButton:hover {
                background-color: #e5e5e5;
            }
            QPushButton:pressed {
                background-color: #cccccc;
            }
        """)
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        
        self._refresh_list()
        
        from PyQt6.QtGui import QGuiApplication
        QGuiApplication.instance().installEventFilter(self)

    def _save_geometry(self):
        geo = self.geometry()
        cfg = ConfigManager.load()
        cfg.setdefault("profile_dialog", {})
        cfg["profile_dialog"]["x"] = geo.x()
        cfg["profile_dialog"]["y"] = geo.y()
        cfg["profile_dialog"]["width"] = geo.width()
        cfg["profile_dialog"]["height"] = geo.height()
        ConfigManager.save(cfg, save_profile=False)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        from PyQt6.QtWidgets import QWidget
        
        # 1. Handle delete key in list_widget
        if obj == self.list_widget and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
                self._handle_delete()
                return True
                
        # 2. Resizing & Moving for ProfileSelectionDialog
        if isinstance(obj, QWidget) and obj.window() == self:
            if event.type() == QEvent.Type.MouseMove:
                if not getattr(self, '_is_resizing', False) and not getattr(self, '_is_moving', False):
                    # Check hover
                    pos = self.mapFromGlobal(event.globalPosition().toPoint())
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
                elif getattr(self, '_is_resizing', False):
                    # Execute resize
                    delta = event.globalPosition() - self._drag_start_pos
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
                    self._save_geometry()
                    return True
                elif getattr(self, '_is_moving', False):
                    # Drag to move
                    delta = event.globalPosition() - self._drag_start_pos
                    dx, dy = int(delta.x()), int(delta.y())
                    geo = self._drag_start_geo
                    self.move(geo.x() + dx, geo.y() + dy)
                    self._save_geometry()
                    return True
                    
            elif event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                pos = self.mapFromGlobal(event.globalPosition().toPoint())
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
                    self._drag_start_pos = event.globalPosition()
                    self._drag_start_geo = self.geometry()
                    return True
                else:
                    # Allow drag to move on dialog background or title label
                    if obj == self.main_wrapper or obj == self.lbl_title:
                        self._is_moving = True
                        self._drag_start_pos = event.globalPosition()
                        self._drag_start_geo = self.geometry()
                        return True
                    
            elif event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                if getattr(self, '_is_resizing', False):
                    self._is_resizing = False
                    self._resize_edge = []
                    self.unsetCursor()
                    self._save_geometry()
                    return True
                elif getattr(self, '_is_moving', False):
                    self._is_moving = False
                    self._save_geometry()
                    return True
        return super().eventFilter(obj, event)

    def _handle_delete(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
            
        item = selected_items[0]
        data = item.data(Qt.ItemDataRole.UserRole)
        if data == "CREATE_NEW":
            return
            
        # Check if it's the last profile
        profiles = list(ConfigManager.SETTINGS_DIR.glob("*.json"))
        if len(profiles) <= 1:
            return # Cannot delete last profile
            
        # Delete file
        try:
            os.remove(data)
        except Exception as e:
            print(f"Error deleting profile: {e}")
            
        self._refresh_list()

    def _refresh_list(self):
        self.list_widget.clear()
        
        # Add "Create New" item
        item_create = QListWidgetItem(Trans.t("create_profile_item", "＋ 创建新默认模板"))
        item_create.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_create.setData(Qt.ItemDataRole.UserRole, "CREATE_NEW")
        from PyQt6.QtGui import QColor, QFont
        font_create = QFont()
        font_create.setBold(True)
        item_create.setFont(font_create)
        item_create.setForeground(QColor("#cccccc")) # clean light gray
        self.list_widget.addItem(item_create)
        
        # Add profiles
        current_profile = ConfigManager.load().get("last_profile", "")
        
        profiles = list(ConfigManager.SETTINGS_DIR.glob("*.json"))
        for p in profiles:
            name = p.stem
            
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, p.as_posix())
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            
            if p.resolve() == Path(current_profile).resolve():
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setForeground(QColor("#ffffff")) # clean bold white for active profile
                item.setToolTip(Trans.t("current_profile_tooltip", "当前使用的配置文件"))
                
            self.list_widget.addItem(item)
            
    def _on_item_double_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        
        if data == "CREATE_NEW":
            self._create_new_profile()
        else:
            self._apply_profile(data)

    def _on_item_changed(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data == "CREATE_NEW":
            return
            
        old_path = Path(data)
        if not old_path.exists():
            return
            
        new_name = item.text().strip()
        if not new_name:
            return
            
        if not new_name.endswith(".json"):
            new_name += ".json"
            
        new_path = old_path.parent / new_name
        
        if new_path == old_path:
            return
            
        if new_path.exists():
            self.list_widget.blockSignals(True)
            self._refresh_list()
            self.list_widget.blockSignals(False)
            return
            
        try:
            os.rename(old_path, new_path)
            
            # If this was the current profile, update setting.json
            cfg = ConfigManager.load()
            current_profile = cfg.get("last_profile", "")
            if old_path.resolve() == Path(current_profile).resolve():
                cfg["last_profile"] = new_path.as_posix()
                ConfigManager.save(cfg, save_profile=False)
                
            item.setData(Qt.ItemDataRole.UserRole, new_path.as_posix())
            
            self.list_widget.blockSignals(True)
            self._refresh_list()
            self.list_widget.blockSignals(False)
        except Exception as e:
            print(f"Failed to rename: {e}")
            
    def _create_new_profile(self):
        # Generate unique name
        counter = 1
        while True:
            new_path = ConfigManager.SETTINGS_DIR / f"profile_{counter}.json"
            if not new_path.exists():
                break
            counter += 1
            
        with open(new_path, 'w', encoding='utf-8') as f:
            json.dump({"version": 2, "keys": ConfigManager.default_keys()}, f, indent=2, ensure_ascii=False)
            
        self._apply_profile(new_path.as_posix())

    def _apply_profile(self, path_str):
        # Update last_profile
        cfg = ConfigManager.load()
        cfg["last_profile"] = path_str
        ConfigManager.save(cfg, save_profile=False)
        
        # Force reload config
        ConfigManager.load(force=True)
        events.config_changed.emit(ConfigManager.load())
        self.accept()

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #121212;
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
            }
            QMenu::item:selected {
                background-color: #2a2a2a;
            }
        """)
        
        if item is not None and item.data(Qt.ItemDataRole.UserRole) != "CREATE_NEW":
            # Right clicked on an existing profile item
            self.list_widget.setCurrentItem(item)
            data = item.data(Qt.ItemDataRole.UserRole)
            
            action_apply = menu.addAction(Trans.t("apply_profile_menu", "应用此配置"))
            action_apply.triggered.connect(lambda: self._apply_profile(data))
            
            action_rename = menu.addAction(Trans.t("rename_profile_menu", "重命名"))
            action_rename.triggered.connect(lambda: self.list_widget.editItem(item))
            
            action_delete = menu.addAction(Trans.t("delete_profile_menu", "删除此配置"))
            action_delete.triggered.connect(self._handle_delete)
        else:
            # Right clicked on empty area
            action_create = menu.addAction(Trans.t("create_profile_menu", "创建新默认模板"))
            action_create.triggered.connect(self._create_new_profile)
            
        menu.exec(self.list_widget.mapToGlobal(pos))
