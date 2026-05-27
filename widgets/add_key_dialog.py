from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeyEvent
from core.i18n import Trans

class AddKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_key_code = None
        self.selected_key_type = "normal"
        
        # Frameless dialog (DO NOT use Popup flag, as it prevents keyboard focus on Windows)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.resize(360, 220)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #0a0a0a;
                border: 1px solid #333333;
                border-radius: 12px;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }
            QPushButton {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 6px;
                color: #dddddd;
                padding: 8px 12px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
                border-color: #ffffff;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #111111;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_prompt = QLabel()
        self.lbl_prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_prompt)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #222222; max-height: 1px; border: none;")
        layout.addWidget(line)
        
        self.lbl_special_prompt = QLabel()
        self.lbl_special_prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_special_prompt.setStyleSheet("font-size: 12px; color: #888888;")
        layout.addWidget(self.lbl_special_prompt)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_kps = QPushButton()
        self.btn_kps.clicked.connect(lambda: self._select_special("kps"))
        btn_layout.addWidget(self.btn_kps)
        
        self.btn_total = QPushButton()
        self.btn_total.clicked.connect(lambda: self._select_special("total_clicks"))
        btn_layout.addWidget(self.btn_total)
        
        self.btn_active = QPushButton()
        self.btn_active.clicked.connect(lambda: self._select_special("active_keys_count"))
        btn_layout.addWidget(self.btn_active)
        
        layout.addLayout(btn_layout)
        
        self.retranslate_ui()

    def _select_special(self, key_type):
        self.selected_key_type = key_type
        self.selected_key_code = ""
        self.accept()

    def retranslate_ui(self):
        is_zh = Trans.get_language() == "zh_CN"
        self.lbl_prompt.setText("请按下您想要添加的按键" if is_zh else "Press any key to add")
        self.lbl_special_prompt.setText("或者选择添加特殊功能按钮：" if is_zh else "Or choose to add a special button:")
        self.btn_kps.setText("每秒点击数 (KPS)" if is_zh else "KPS (Keys/s)")
        self.btn_total.setText("总点击数 (Total)" if is_zh else "Total Clicks")
        self.btn_active.setText("当前触发数 (Active)" if is_zh else "Active Keys")

    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        self.setFocus()

    def changeEvent(self, event):
        # Cancel dialog when focus is lost (clicking outside)
        if event.type() == QEvent.Type.ActivationChange:
            if not self.isActiveWindow():
                self.reject()
        super().changeEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.reject()
            return
            
        # Map key using local mapper
        key_name = self._map_qt_key(key, event.text())
        if key_name:
            print(f"AddKeyDialog: Natively captured key: {key_name}", flush=True)
            self.selected_key_code = key_name
            self.selected_key_type = "normal"
            self.accept()
        else:
            event.ignore()

    def _map_qt_key(self, key, text):
        # Map common Qt keys to pynput/standard format
        mapping = {
            Qt.Key.Key_Space: "space",
            Qt.Key.Key_Return: "enter",
            Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Shift: "shift",
            Qt.Key.Key_Control: "ctrl",
            Qt.Key.Key_Alt: "alt",
            Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Up: "up",
            Qt.Key.Key_Down: "down",
            Qt.Key.Key_Left: "left",
            Qt.Key.Key_Right: "right",
            Qt.Key.Key_CapsLock: "caps_lock",
            Qt.Key.Key_PageUp: "page_up",
            Qt.Key.Key_PageDown: "page_down",
        }
        if key in mapping:
            return mapping[key]
            
        # F1 - F12
        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            return f"f{key - Qt.Key.Key_F1 + 1}"
            
        # Handle standard symbol keys directly by Qt Key enum to avoid Shift modifications
        symbol_mapping = {
            Qt.Key.Key_BracketLeft: "[",
            Qt.Key.Key_BracketRight: "]",
            Qt.Key.Key_Backslash: "\\",
            Qt.Key.Key_Semicolon: ";",
            Qt.Key.Key_Equal: "=",
            Qt.Key.Key_Comma: ",",
            Qt.Key.Key_Minus: "-",
            Qt.Key.Key_Period: ".",
            Qt.Key.Key_Slash: "/",
            Qt.Key.Key_QuoteLeft: "`",
            Qt.Key.Key_Apostrophe: "'",
        }
        if key in symbol_mapping:
            return symbol_mapping[key]

        # Handle standard alphanumeric keys directly by Qt Key enum to avoid Shift/Caps modifications
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            return chr(key).lower()
        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            return chr(key)
            
        return None
