from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QColor, QPainter, QBrush, QFont, QPen
from PyQt6.QtCore import pyqtSignal, Qt, QRectF

class ColorButton(QPushButton):
    colorChanged = pyqtSignal(list)  # RGBA list

    def __init__(self, color_rgba=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setMinimumWidth(100)
        self.setSizePolicy(
            __import__('PyQt6.QtWidgets', fromlist=['QSizePolicy']).QSizePolicy.Policy.Expanding,
            __import__('PyQt6.QtWidgets', fromlist=['QSizePolicy']).QSizePolicy.Policy.Fixed
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background-color: transparent; border: none;")
        self._color = [255, 255, 255, 255]
        self._hover = False
        self.set_color(color_rgba or [255, 255, 255, 255])
        self.clicked.connect(self._pick_color)

    def set_color(self, val):
        try:
            if isinstance(val, (list, tuple)):
                rgba = [int(x) for x in val]
                if len(rgba) == 3:
                    rgba.append(255)
                self._color = rgba[:4]
            else:
                self._color = [255, 255, 255, 255]
        except Exception:
            self._color = [255, 255, 255, 255]
        self.update()

    def _pick_color(self):
        from widgets.color_picker_dialog import ColorPickerDialog
        result = ColorPickerDialog.get_color(list(self._color), parent=self)
        if result is not None:
            self._color = result
            self.update()
            self.colorChanged.emit(self._color)

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        swatch_w = 36   # colored preview block width
        radius = 6

        # ── Border ────────────────────────────────────────
        border_color = QColor(108, 99, 255) if self._hover else QColor(55, 55, 55)
        p.setPen(QPen(border_color, 1.5))
        p.setBrush(QColor(18, 18, 18))
        p.drawRoundedRect(QRectF(0.75, 0.75, w - 1.5, h - 1.5), radius, radius)

        # ── Color swatch (left block) ──────────────────────
        # Checkerboard underneath for alpha
        cell = 5
        for row in range(0, h, cell):
            for col in range(0, swatch_w, cell):
                is_light = (row // cell + col // cell) % 2 == 0
                c = QColor(80, 80, 80) if is_light else QColor(50, 50, 50)
                p.fillRect(col + 1, row, cell, cell, c)

        # Clip left swatch to rounded left side only
        from PyQt6.QtCore import QRect
        from PyQt6.QtGui import QPainterPath
        swatch_path = QPainterPath()
        swatch_path.addRoundedRect(QRectF(1, 1, swatch_w + radius, h - 2), radius, radius)
        swatch_clip = QPainterPath()
        swatch_clip.addRect(QRectF(1, 1, swatch_w, h - 2))
        p.save()
        p.setClipPath(swatch_clip.intersected(swatch_path))
        p.fillRect(1, 1, swatch_w, h - 2, QColor(*self._color))
        p.restore()

        # Separator line between swatch and text
        p.setPen(QPen(QColor(45, 45, 45), 1))
        p.drawLine(swatch_w, 1, swatch_w, h - 2)

        # ── RGBA text (right side) ─────────────────────────
        r, g, b, a = self._color
        text = f"rgba({r}, {g}, {b}, {a})"
        font = QFont("Consolas", 10) if QFont("Consolas").exactMatch() else QFont("monospace", 10)
        p.setFont(font)
        p.setPen(QColor(210, 210, 210))
        text_rect = QRectF(swatch_w + 8, 0, w - swatch_w - 10, h)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
