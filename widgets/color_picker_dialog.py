import math
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QLineEdit, QPushButton, QWidget, QSizePolicy, QGridLayout
)
from PyQt6.QtCore import Qt, QPoint, QRectF, pyqtSignal, QSize
from PyQt6.QtGui import (
    QPainter, QColor, QLinearGradient, QConicalGradient,
    QRadialGradient, QBrush, QPen, QPixmap, QImage, QMouseEvent
)
from core.i18n import Trans


# ──────────────────────────────────────────────────────────
# SV Square  (Saturation on X, Value on Y)
# ──────────────────────────────────────────────────────────
class SVSquare(QWidget):
    changed = pyqtSignal(float, float)   # s, v  (0..1)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._hue = 0.0
        self._s = 1.0
        self._v = 1.0
        self._pressed = False

    def set_hsv(self, h, s, v):
        self._hue = h
        self._s = s
        self._v = v
        self.update()

    def _pos_to_sv(self, pos):
        s = max(0.0, min(1.0, pos.x() / (self.width() - 1)))
        v = max(0.0, min(1.0, 1.0 - pos.y() / (self.height() - 1)))
        return s, v

    def mousePressEvent(self, e: QMouseEvent):
        self._pressed = True
        s, v = self._pos_to_sv(e.position().toPoint())
        self._s, self._v = s, v
        self.changed.emit(s, v)
        self.update()

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._pressed:
            s, v = self._pos_to_sv(e.position().toPoint())
            self._s, self._v = s, v
            self.changed.emit(s, v)
            self.update()

    def mouseReleaseEvent(self, e):
        self._pressed = False

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        w, h = self.width(), self.height()

        # Base hue color
        base = QColor.fromHsvF(self._hue, 1.0, 1.0)

        # White → hue gradient (left to right)
        grad_h = QLinearGradient(0, 0, w, 0)
        grad_h.setColorAt(0.0, QColor(255, 255, 255))
        grad_h.setColorAt(1.0, base)
        p.fillRect(0, 0, w, h, grad_h)

        # Transparent → black gradient (top to bottom)
        grad_v = QLinearGradient(0, 0, 0, h)
        grad_v.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad_v.setColorAt(1.0, QColor(0, 0, 0, 255))
        p.fillRect(0, 0, w, h, grad_v)

        # Cursor
        cx = int(self._s * (w - 1))
        cy = int((1.0 - self._v) * (h - 1))
        p.setPen(QPen(QColor(255, 255, 255), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPoint(cx, cy), 7, 7)
        p.setPen(QPen(QColor(0, 0, 0), 1))
        p.drawEllipse(QPoint(cx, cy), 8, 8)


# ──────────────────────────────────────────────────────────
# Hue Strip  (vertical)
# ──────────────────────────────────────────────────────────
class HueStrip(QWidget):
    changed = pyqtSignal(float)   # hue 0..1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hue = 0.0
        self._pressed = False

    def set_hue(self, h):
        self._hue = max(0.0, min(1.0, h))
        self.update()

    def _pos_to_hue(self, y):
        return max(0.0, min(1.0, y / (self.height() - 1)))

    def mousePressEvent(self, e):
        self._pressed = True
        h = self._pos_to_hue(e.position().y())
        self._hue = h
        self.changed.emit(h)
        self.update()

    def mouseMoveEvent(self, e):
        if self._pressed:
            h = self._pos_to_hue(e.position().y())
            self._hue = h
            self.changed.emit(h)
            self.update()

    def mouseReleaseEvent(self, e):
        self._pressed = False

    def paintEvent(self, _):
        p = QPainter(self)
        w, h = self.width(), self.height()
        grad = QLinearGradient(0, 0, 0, h)
        for i in range(7):
            grad.setColorAt(i / 6.0, QColor.fromHsvF(i / 6.0, 1.0, 1.0))
        p.fillRect(0, 0, w, h, grad)

        # Cursor line
        cy = int(self._hue * (h - 1))
        p.setPen(QPen(QColor(255, 255, 255), 2))
        p.drawLine(0, cy, w, cy)
        p.setPen(QPen(QColor(0, 0, 0), 1))
        p.drawLine(0, cy - 1, w, cy - 1)
        p.drawLine(0, cy + 1, w, cy + 1)


# ──────────────────────────────────────────────────────────
# Alpha Strip  (horizontal, shows color → transparent)
# ──────────────────────────────────────────────────────────
class AlphaStrip(QWidget):
    changed = pyqtSignal(int)   # alpha 0..255

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._color = QColor(255, 255, 255)
        self._alpha = 255
        self._pressed = False

    def set_color(self, color: QColor, alpha: int):
        self._color = color
        self._alpha = max(0, min(255, alpha))
        self.update()

    def _pos_to_alpha(self, x):
        return max(0, min(255, int(x / (self.width() - 1) * 255)))

    def mousePressEvent(self, e):
        self._pressed = True
        a = self._pos_to_alpha(e.position().x())
        self._alpha = a
        self.changed.emit(a)
        self.update()

    def mouseMoveEvent(self, e):
        if self._pressed:
            a = self._pos_to_alpha(e.position().x())
            self._alpha = a
            self.changed.emit(a)
            self.update()

    def mouseReleaseEvent(self, e):
        self._pressed = False

    def paintEvent(self, _):
        p = QPainter(self)
        w, h = self.width(), self.height()

        # Checkerboard background for transparency
        cell = 6
        for row in range(0, h, cell):
            for col in range(0, w, cell):
                is_light = (row // cell + col // cell) % 2 == 0
                c = QColor(180, 180, 180) if is_light else QColor(120, 120, 120)
                p.fillRect(col, row, cell, cell, c)

        # Gradient: transparent → opaque color
        c_transparent = QColor(self._color)
        c_transparent.setAlpha(0)
        c_opaque = QColor(self._color)
        c_opaque.setAlpha(255)
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, c_transparent)
        grad.setColorAt(1.0, c_opaque)
        p.fillRect(0, 0, w, h, grad)

        # Cursor line
        cx = int(self._alpha / 255.0 * (w - 1))
        p.setPen(QPen(QColor(255, 255, 255), 2))
        p.drawLine(cx, 0, cx, h)
        p.setPen(QPen(QColor(0, 0, 0), 1))
        p.drawLine(cx - 1, 0, cx - 1, h)
        p.drawLine(cx + 1, 0, cx + 1, h)


# ──────────────────────────────────────────────────────────
# Color Preview  (old vs new, checkerboard for alpha)
# ──────────────────────────────────────────────────────────
class ColorPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self._old = QColor(255, 255, 255, 255)
        self._new = QColor(255, 255, 255, 255)

    def set_colors(self, old: QColor, new: QColor):
        self._old = old
        self._new = new
        self.update()

    def _draw_checker(self, p, rect):
        cell = 6
        for row in range(0, rect.height(), cell):
            for col in range(0, rect.width(), cell):
                is_light = (row // cell + col // cell) % 2 == 0
                c = QColor(80, 80, 80) if is_light else QColor(50, 50, 50)
                p.fillRect(rect.x() + col, rect.y() + row, cell, cell, c)

    def paintEvent(self, _):
        p = QPainter(self)
        w, h = self.width(), self.height()
        half = w // 2

        from PyQt6.QtCore import QRect
        left = QRect(0, 0, half, h)
        right = QRect(half, 0, w - half, h)

        self._draw_checker(p, left)
        p.fillRect(left, self._old)

        self._draw_checker(p, right)
        p.fillRect(right, self._new)

        # Divider
        p.setPen(QPen(QColor(80, 80, 80), 1))
        p.drawLine(half, 0, half, h)

        # Labels — language-aware
        is_zh = Trans.get_language() == "zh_CN"
        old_lbl = "旧" if is_zh else "Old"
        new_lbl = "新" if is_zh else "New"
        p.setPen(QColor(200, 200, 200))
        from PyQt6.QtGui import QFont
        font = QFont("Segoe UI", 8)
        p.setFont(font)
        p.drawText(left, Qt.AlignmentFlag.AlignCenter, old_lbl)
        p.drawText(right, Qt.AlignmentFlag.AlignCenter, new_lbl)


# ──────────────────────────────────────────────────────────
# ColorPickerDialog
# ──────────────────────────────────────────────────────────
PRESETS = [
    [255, 255, 255, 255], [200, 200, 200, 200], [0, 0, 0, 255],   [0, 0, 0, 0],
    [108, 99, 255, 255],  [72, 149, 239, 255],  [67, 217, 173, 255], [39, 174, 96, 255],
    [255, 235, 59, 255],  [255, 152, 0, 255],   [244, 67, 54, 255],  [233, 30, 99, 255],
    [240, 240, 245, 60],  [255, 255, 255, 160], [108, 99, 255, 160], [0, 0, 0, 120],
]

DIALOG_STYLE = """
QDialog {
    background-color: transparent;
}
#PickerBg {
    background-color: #141414;
    border: 1px solid #333333;
    border-radius: 14px;
}
QLabel {
    color: #c8c8c8;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 12px;
    background: transparent;
}
QSpinBox {
    background-color: #0f0f0f;
    border: 1px solid #2a2a2a;
    border-radius: 5px;
    color: #ffffff;
    padding: 3px 6px;
    font-size: 12px;
    min-width: 52px;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 0px;
}
QLineEdit {
    background-color: #0f0f0f;
    border: 1px solid #2a2a2a;
    border-radius: 5px;
    color: #ffffff;
    padding: 3px 8px;
    font-size: 12px;
    font-family: monospace;
}
QPushButton#btn_ok {
    background-color: #6c63ff;
    border: none;
    border-radius: 6px;
    color: #ffffff;
    padding: 7px 20px;
    font-size: 13px;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}
QPushButton#btn_ok:hover { background-color: #7c74ff; }
QPushButton#btn_cancel {
    background-color: #1e1e1e;
    border: 1px solid #333333;
    border-radius: 6px;
    color: #bbbbbb;
    padding: 7px 20px;
    font-size: 13px;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}
QPushButton#btn_cancel:hover { background-color: #2a2a2a; }
"""


class ColorPickerDialog(QDialog):
    """Dark-themed, full-featured RGBA color picker dialog. Draggable by title bar."""

    def __init__(self, initial_rgba=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(DIALOG_STYLE)

        rgba = initial_rgba or [255, 255, 255, 255]
        self._old_color = QColor(*rgba[:4])
        self._r, self._g, self._b, self._a = rgba[0], rgba[1], rgba[2], rgba[3]
        self._updating = False

        # Drag state
        self._drag_start_pos = None
        self._drag_win_pos = None

        self._build_ui()
        self._sync_from_rgb()
        self.preview.set_colors(self._old_color, self._current_qcolor())

        # Position from main config first; fallback to parent center
        from core.config_manager import ConfigManager
        cfg = ConfigManager.load()
        px = cfg.get("display_window", {}).get("picker_x", None)
        py = cfg.get("display_window", {}).get("picker_y", None)
        if px is not None and py is not None:
            self.move(px, py)
        elif parent:
            self.move(parent.mapToGlobal(parent.rect().center()) - self.rect().center())

    # ── Drag support (title bar) ──────────────────────────
    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            title_h = 46  # approximate title row height
            if e.position().y() < title_h:
                self._drag_start_pos = e.globalPosition().toPoint()
                self._drag_win_pos = self.pos()
                e.accept()
                return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._drag_start_pos is not None and e.buttons() == Qt.MouseButton.LeftButton:
            delta = e.globalPosition().toPoint() - self._drag_start_pos
            self.move(self._drag_win_pos + delta)
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            if self._drag_start_pos is not None:
                # Save position to main config
                try:
                    from core.config_manager import ConfigManager
                    cfg = ConfigManager.load()
                    cfg.setdefault("display_window", {})["picker_x"] = self.x()
                    cfg["display_window"]["picker_y"] = self.y()
                    ConfigManager.save(cfg, save_profile=False)
                except Exception:
                    pass
            self._drag_start_pos = None
            self._drag_win_pos = None
        super().mouseReleaseEvent(e)

    # ── UI Construction ────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        bg = QWidget()
        bg.setObjectName("PickerBg")
        outer.addWidget(bg)

        root = QVBoxLayout(bg)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # Title (draggable area — cursor hint)
        is_zh = Trans.get_language() == "zh_CN"
        self.lbl_title = QLabel(Trans.t("select_color", "选择颜色"))
        self.lbl_title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #ffffff; "
            "padding-bottom: 4px;"
        )
        self.lbl_title.setCursor(Qt.CursorShape.SizeAllCursor)
        root.addWidget(self.lbl_title)

        # ── Picker area: SV + Hue ──
        picker_row = QHBoxLayout()
        picker_row.setSpacing(10)

        self.sv_square = SVSquare()
        self.sv_square.changed.connect(self._on_sv_changed)
        picker_row.addWidget(self.sv_square)

        self.hue_strip = HueStrip()
        self.hue_strip.changed.connect(self._on_hue_changed)
        picker_row.addWidget(self.hue_strip)

        picker_row.addStretch()
        root.addLayout(picker_row)

        # ── Alpha strip ──
        alpha_row = QHBoxLayout()
        alpha_row.setSpacing(6)
        lbl_a = QLabel("A")
        lbl_a.setFixedWidth(12)
        alpha_row.addWidget(lbl_a)
        self.alpha_strip = AlphaStrip()
        self.alpha_strip.changed.connect(self._on_alpha_strip_changed)
        alpha_row.addWidget(self.alpha_strip)
        root.addLayout(alpha_row)

        # ── Preview ──
        self.preview = ColorPreview()
        root.addWidget(self.preview)

        # ── RGBA spinboxes ──
        rgba_grid = QGridLayout()
        rgba_grid.setSpacing(6)
        for col, (ch, vmax) in enumerate([("R", 255), ("G", 255), ("B", 255), ("A", 255)]):
            lbl = QLabel(ch)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rgba_grid.addWidget(lbl, 0, col)
            spin = QSpinBox()
            spin.setRange(0, vmax)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            setattr(self, f"spin_{ch.lower()}", spin)
            rgba_grid.addWidget(spin, 1, col)

        self.spin_r.valueChanged.connect(lambda v: self._on_spin_changed())
        self.spin_g.valueChanged.connect(lambda v: self._on_spin_changed())
        self.spin_b.valueChanged.connect(lambda v: self._on_spin_changed())
        self.spin_a.valueChanged.connect(lambda v: self._on_spin_changed())
        root.addLayout(rgba_grid)

        # ── HEX input ──
        hex_row = QHBoxLayout()
        hex_row.setSpacing(8)
        hex_row.addWidget(QLabel("#"))
        self.edit_hex = QLineEdit()
        self.edit_hex.setPlaceholderText("RRGGBBAA")
        self.edit_hex.setMaxLength(8)
        self.edit_hex.editingFinished.connect(self._on_hex_changed)
        hex_row.addWidget(self.edit_hex)
        root.addLayout(hex_row)

        # ── Preset palette ──
        is_zh = Trans.get_language() == "zh_CN"
        self.lbl_palette = QLabel(Trans.t("color_presets", "快捷预设" if is_zh else "Presets"))
        self.lbl_palette.setStyleSheet("color: #666; font-size: 11px;")
        root.addWidget(self.lbl_palette)

        palette_grid = QGridLayout()
        palette_grid.setSpacing(5)
        for idx, preset in enumerate(PRESETS):
            btn = _PresetSwatch(preset)
            btn.clicked_color.connect(self._apply_preset)
            palette_grid.addWidget(btn, idx // 8, idx % 8)
        root.addLayout(palette_grid)

        # ── OK / Cancel ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        is_zh = Trans.get_language() == "zh_CN"
        btn_cancel = QPushButton(Trans.t("cancel", "取消" if is_zh else "Cancel"))
        btn_cancel.setObjectName("btn_cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_ok = QPushButton(Trans.t("ok", "确定" if is_zh else "OK"))
        btn_ok.setObjectName("btn_ok")
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_ok)
        root.addLayout(btn_row)

    # ── Sync helpers ──────────────────────────────────────

    def _current_qcolor(self):
        return QColor(self._r, self._g, self._b, self._a)

    def _sync_from_rgb(self):
        """Update all controls from (r,g,b,a)."""
        if self._updating:
            return
        self._updating = True
        try:
            qc = QColor(self._r, self._g, self._b)
            h, s, v, _ = qc.getHsvF()
            if h < 0:
                h = 0.0

            self.sv_square.set_hsv(h, s, v)
            self.hue_strip.set_hue(h)
            self.alpha_strip.set_color(qc, self._a)

            self.spin_r.setValue(self._r)
            self.spin_g.setValue(self._g)
            self.spin_b.setValue(self._b)
            self.spin_a.setValue(self._a)

            hex_str = f"{self._r:02X}{self._g:02X}{self._b:02X}{self._a:02X}"
            self.edit_hex.setText(hex_str)

            self.preview.set_colors(self._old_color, self._current_qcolor())
        finally:
            self._updating = False

    def _sync_from_hsv(self, h, s, v):
        qc = QColor.fromHsvF(h, s, v)
        self._r = qc.red()
        self._g = qc.green()
        self._b = qc.blue()
        self._sync_from_rgb()

    # ── Slot handlers ─────────────────────────────────────

    def _on_sv_changed(self, s, v):
        if self._updating:
            return
        h = self.hue_strip._hue
        self._sync_from_hsv(h, s, v)

    def _on_hue_changed(self, h):
        if self._updating:
            return
        s = self.sv_square._s
        v = self.sv_square._v
        self._sync_from_hsv(h, s, v)

    def _on_alpha_strip_changed(self, a):
        if self._updating:
            return
        self._a = a
        self._updating = True
        try:
            self.spin_a.setValue(a)
            hex_str = f"{self._r:02X}{self._g:02X}{self._b:02X}{self._a:02X}"
            self.edit_hex.setText(hex_str)
            self.preview.set_colors(self._old_color, self._current_qcolor())
        finally:
            self._updating = False

    def _on_spin_changed(self):
        if self._updating:
            return
        self._r = self.spin_r.value()
        self._g = self.spin_g.value()
        self._b = self.spin_b.value()
        self._a = self.spin_a.value()
        self._sync_from_rgb()

    def _on_hex_changed(self):
        if self._updating:
            return
        text = self.edit_hex.text().strip().lstrip("#")
        try:
            if len(text) == 6:
                self._r = int(text[0:2], 16)
                self._g = int(text[2:4], 16)
                self._b = int(text[4:6], 16)
            elif len(text) == 8:
                self._r = int(text[0:2], 16)
                self._g = int(text[2:4], 16)
                self._b = int(text[4:6], 16)
                self._a = int(text[6:8], 16)
            self._sync_from_rgb()
        except ValueError:
            pass

    def _apply_preset(self, rgba):
        self._r, self._g, self._b, self._a = rgba[0], rgba[1], rgba[2], rgba[3]
        self._sync_from_rgb()

    # ── Result ────────────────────────────────────────────

    def get_rgba(self):
        """Return [R, G, B, A] list."""
        return [self._r, self._g, self._b, self._a]

    @staticmethod
    def get_color(initial_rgba=None, parent=None):
        """Convenience static method mimicking QColorDialog.getColor."""
        dlg = ColorPickerDialog(initial_rgba, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.get_rgba()
        return None


# ──────────────────────────────────────────────────────────
# Preset Swatch
# ──────────────────────────────────────────────────────────
class _PresetSwatch(QWidget):
    clicked_color = pyqtSignal(list)

    def __init__(self, rgba, parent=None):
        super().__init__(parent)
        self.rgba = rgba
        self.setFixedSize(22, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover = False

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked_color.emit(self.rgba)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Checkerboard
        cell = 5
        for row in range(0, h, cell):
            for col in range(0, w, cell):
                is_light = (row // cell + col // cell) % 2 == 0
                c = QColor(80, 80, 80) if is_light else QColor(50, 50, 50)
                p.fillRect(col, row, cell, cell, c)

        # Color fill (rounded)
        p.setBrush(QColor(*self.rgba))
        pen_color = QColor(255, 255, 255, 180) if self._hover else QColor(60, 60, 60)
        p.setPen(QPen(pen_color, 1.5))
        p.drawRoundedRect(1, 1, w - 2, h - 2, 4, 4)
