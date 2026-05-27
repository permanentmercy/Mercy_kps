from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QMouseEvent

class TitleBar(QWidget):
    settings_clicked = pyqtSignal()

    def __init__(self, title="KPS-Plus", parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet("""
            TitleBar {
                background-color: #0a0a0a;
                border-bottom: 1px solid #262626;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }
            QLabel {
                color: #ffffff;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-weight: bold;
                padding-left: 10px;
                border: none;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                min-width: 48px;
                max-width: 48px;
                min-height: 44px;
                max-height: 44px;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
            }
            QPushButton#btn_min {
                background-image: url('assets/images/min.svg');
                background-position: center;
                background-repeat: no-repeat;
            }
            QPushButton#btn_max[state="normal"] {
                background-image: url('assets/images/max.svg');
                background-position: center;
                background-repeat: no-repeat;
            }
            QPushButton#btn_max[state="maximized"] {
                background-image: url('assets/images/restore.svg');
                background-position: center;
                background-repeat: no-repeat;
            }
            QPushButton#btn_close {
                background-image: url('assets/images/close.svg');
                background-position: center;
                background-repeat: no-repeat;
            }
            QPushButton#btn_close:hover {
                background-color: #c42b1c;
            }
            QPushButton#btn_close:pressed {
                background-color: #a82315;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Settings Button (Gear icon) — borderless large style using local SVGs
        self.btn_settings = QPushButton("")
        self.btn_settings.setObjectName("btn_settings")
        self.btn_settings.setStyleSheet("""
            QPushButton#btn_settings {
                background-image: url('assets/images/settings_normal.svg');
                background-position: center;
                background-repeat: no-repeat;
                background-color: transparent;
                border: none;
                min-width: 54px;
                max-width: 54px;
                min-height: 44px;
                max-height: 44px;
                padding: 0;
            }
            QPushButton#btn_settings:hover {
                background-image: url('assets/images/settings_hover.svg');
                background-color: #2a2a2a;
            }
            QPushButton#btn_settings:pressed {
                background-image: url('assets/images/settings_pressed.svg');
                background-color: #1a1a1a;
            }
        """)
        self.btn_settings.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.btn_settings)

        # Title Label (empty)
        self.lbl_title = QLabel("")
        layout.addWidget(self.lbl_title)

        layout.addStretch()

        # Minimize Button
        self.btn_min = QPushButton("")
        self.btn_min.setObjectName("btn_min")
        self.btn_min.clicked.connect(self._minimize)
        layout.addWidget(self.btn_min)

        # Maximize Button
        self.btn_max = QPushButton("")
        self.btn_max.setObjectName("btn_max")
        self.btn_max.setProperty("state", "normal")
        self.btn_max.clicked.connect(self._toggle_maximize)
        layout.addWidget(self.btn_max)

        # Close Button
        self.btn_close = QPushButton("")
        self.btn_close.setObjectName("btn_close")
        self.btn_close.clicked.connect(self._close)
        layout.addWidget(self.btn_close)

        self._drag_pos = None

    def _minimize(self):
        if self.window():
            self.window().showMinimized()

    def _toggle_maximize(self):
        if self.window():
            if self.window().isMaximized():
                self.window().showNormal()
                self.btn_max.setProperty("state", "normal")
            else:
                self.window().showMaximized()
                self.btn_max.setProperty("state", "maximized")
            self.btn_max.style().unpolish(self.btn_max)
            self.btn_max.style().polish(self.btn_max)

    def _close(self):
        if self.window():
            self.window().close()

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.window().frameGeometry().topLeft()

    def mouseMoveEvent(self, e: QMouseEvent):
        if e.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            if self.window().isMaximized():
                self.window().showNormal()
                self.btn_max.setProperty("state", "normal")
                self.btn_max.style().unpolish(self.btn_max)
                self.btn_max.style().polish(self.btn_max)
                new_x = int(e.globalPosition().toPoint().x() - self.window().width() / 2)
                self.window().move(new_x, e.globalPosition().toPoint().y() - self._drag_pos.y())
                self._drag_pos = QPoint(self.window().width() // 2, self._drag_pos.y())
            else:
                self.window().move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseDoubleClickEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()
