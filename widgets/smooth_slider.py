from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QMouseEvent
from PyQt6.QtCore import Qt, pyqtSignal, QRectF

class SmoothSlider(QWidget):
    valueChanged = pyqtSignal(int)
    sliderReleased = pyqtSignal()

    def __init__(self, min_val=0, max_val=100, default_val=50, parent=None):
        super().__init__(parent)
        self.setMinimumSize(100, 30)
        self._min = min_val
        self._max = max_val
        self._val = default_val
        self._hover = False
        
        # Style constants
        self.TRACK_H = 4
        self.THUMB_R = 8
        self.TRACK_COLOR = QColor("#333333")
        self.FILL_COLOR = QColor("#ffffff")
        self.THUMB_COLOR = QColor("#ffffff")
        self.GLOW_COLOR = QColor(255, 255, 255, 64)

    def value(self):
        return self._val

    def setValue(self, val):
        self._val = max(self._min, min(self._max, val))
        self.update()
        self.valueChanged.emit(self._val)

    def setRange(self, min_val, max_val):
        self._min = min_val
        self._max = max_val
        self._val = max(self._min, min(self._max, self._val))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        track_y = h / 2 - self.TRACK_H / 2
        thumb_x = self.THUMB_R + (w - 2 * self.THUMB_R) * (self._val - self._min) / (self._max - self._min)
        
        # Draw background track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.TRACK_COLOR)
        p.drawRoundedRect(QRectF(self.THUMB_R, track_y, w - 2 * self.THUMB_R, self.TRACK_H), self.TRACK_H/2, self.TRACK_H/2)
        
        # Draw fill track
        p.setBrush(self.FILL_COLOR)
        p.drawRoundedRect(QRectF(self.THUMB_R, track_y, thumb_x - self.THUMB_R, self.TRACK_H), self.TRACK_H/2, self.TRACK_H/2)
        
        # Draw glow if hover
        if self._hover:
            p.setBrush(self.GLOW_COLOR)
            p.drawEllipse(QRectF(thumb_x - self.THUMB_R - 4, h / 2 - self.THUMB_R - 4, 
                                 (self.THUMB_R + 4)*2, (self.THUMB_R + 4)*2))
                                 
        # Draw thumb
        p.setBrush(self.THUMB_COLOR)
        p.drawEllipse(QRectF(thumb_x - self.THUMB_R, h / 2 - self.THUMB_R, 
                             self.THUMB_R * 2, self.THUMB_R * 2))

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            self._update_val_from_pos(e.position().x())

    def mouseMoveEvent(self, e: QMouseEvent):
        if e.buttons() & Qt.MouseButton.LeftButton:
            self._update_val_from_pos(e.position().x())

    def mouseReleaseEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            self.sliderReleased.emit()

    def _update_val_from_pos(self, x):
        w = self.width()
        track_w = w - 2 * self.THUMB_R
        rel_x = max(0, min(track_w, x - self.THUMB_R))
        ratio = rel_x / track_w if track_w > 0 else 0
        val = int(self._min + ratio * (self._max - self._min))
        if val != self._val:
            self.setValue(val)
