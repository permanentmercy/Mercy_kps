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
                color: #cccccc;
                font-family: "Segoe MDL2 Assets", "Segoe UI Symbol";
                font-size: 10px;
                min-width: 48px;
                max-width: 48px;
                min-height: 44px;
                max-height: 44px;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
                color: #ffffff;
            }
            QPushButton#btn_close:hover {
                background-color: #c42b1c;
                color: #ffffff;
            }
            QPushButton#btn_close:pressed {
                background-color: #a82315;
                color: #ffffff;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Settings Button (Gear icon) — borderless large style
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setObjectName("btn_settings")
        self.btn_settings.setStyleSheet("""
            QPushButton#btn_settings {
                background-color: transparent;
                border: none;
                color: #888888;
                font-family: "Segoe UI", "Segoe UI Symbol";
                font-size: 24px;
                min-width: 54px;
                max-width: 54px;
                min-height: 44px;
                max-height: 44px;
                padding: 0;
            }
            QPushButton#btn_settings:hover {
                background-color: #2a2a2a;
                color: #ffffff;
            }
            QPushButton#btn_settings:pressed {
                background-color: #1a1a1a;
                color: #cccccc;
            }
        """)
        self.btn_settings.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.btn_settings)

        # Title Label (empty)
        self.lbl_title = QLabel("")
        layout.addWidget(self.lbl_title)

        layout.addStretch()

        # Minimize Button
        self.btn_min = QPushButton("\uE921")
        self.btn_min.setObjectName("btn_min")
        self.btn_min.clicked.connect(self._minimize)
        layout.addWidget(self.btn_min)

        # Maximize Button
        self.btn_max = QPushButton("\uE922")
        self.btn_max.setObjectName("btn_max")
        self.btn_max.clicked.connect(self._toggle_maximize)
        layout.addWidget(self.btn_max)

        # Close Button
        self.btn_close = QPushButton("\uE8BB")
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
                self.btn_max.setText("\uE922")
            else:
                self.window().showMaximized()
                self.btn_max.setText("\uE923")

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
                self.btn_max.setText("\uE922")
                new_x = int(e.globalPosition().toPoint().x() - self.window().width() / 2)
                self.window().move(new_x, e.globalPosition().toPoint().y() - self._drag_pos.y())
                self._drag_pos = QPoint(self.window().width() // 2, self._drag_pos.y())
            else:
                self.window().move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseDoubleClickEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()
