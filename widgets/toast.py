from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor

class Toast(QLabel):
    def __init__(self, parent, text, duration=3000):
        super().__init__(parent)
        self.setText(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 30, 30, 240);
                color: #ffcc00;
                border: 1px solid #ffcc00;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        self.adjustSize()
        
        # Position at bottom right
        if parent:
            pw, ph = parent.width(), parent.height()
            self.move(pw - self.width() - 20, ph - self.height() - 20)
            
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.show()
        
        # Fade out animation
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(500)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.InQuad)
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._start_fade_out)
        self.timer.start(duration)
        
    def _start_fade_out(self):
        self.anim.start()
        self.anim.finished.connect(self.deleteLater)
