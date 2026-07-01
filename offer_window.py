"""
offer_window.py  —  Teklif penceresi UI (dark theme, amber accent)
Business logic (_service, _generate_pdf vb.) dokunulmadı.
Widget isimleri korundu.
"""

from __future__ import annotations
import os, subprocess, sys

from PyQt6.QtCore import (
    Qt,
    QDate,
    QPoint,
    QRect,
    pyqtSignal,
    QPropertyAnimation,
    QEasingCurve,
    pyqtProperty,
)
from PyQt6.QtGui import QColor, QPainter, QPen, QPainterPath
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QAbstractItemView,
)

from database import get_product_by_code, search_products
from offer_service import DuplicateItemError, OfferService
from theme import get_window_size
from theme import (
    CLR_BG,
    CLR_SURFACE,
    CLR_HOVER,
    CLR_HOVER2,
    CLR_BORDER,
    CLR_BORDER_DARK,
    CLR_TEXT,
    CLR_TEXT_MUTED,
    CLR_TEXT_DIM,
    CLR_ACCENT,
    CLR_ACCENT_HOVER,
    CLR_ACCENT_PRESSED,
    CLR_ACCENT_SOFT,
)

VAT_RATE = 0.20
SEARCH_POPUP_MAX_ROWS = 8
SEARCH_POPUP_ROW_H = 42


# ── Ortak yardımcılar ─────────────────────────────────────────────────────


class _Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background: {CLR_BORDER}; border: none;")


class _FieldLabel(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            "color: #F5F5F5; font-size: 13px; font-weight: 700; "
            "background: transparent; border: none; padding: 0; margin: 0;"
        )


def _input_style(multiline=False) -> str:
    base = (
        f"background: {CLR_SURFACE}; color: {CLR_TEXT}; "
        f"border: 1.5px solid {CLR_BORDER}; border-radius: 8px; "
        f"font-size: 13px; padding: 6px 12px; "
    )
    widget = "QTextEdit" if multiline else "QLineEdit"
    combo = "QComboBox" if not multiline else ""
    date = "QDateEdit" if not multiline else ""
    parts = [
        f"{widget} {{ {base} }}",
        f"{widget}:focus {{ border-color: {CLR_ACCENT}; }}",
        f"{widget}:hover {{ border-color: {CLR_BORDER_DARK}; }}",
    ]
    return "\n".join(parts)


# ── Renk interpolasyonu ──────────────────────────────────────────────────


def _hex_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


_BORDER_RGB = _hex_rgb(CLR_BORDER)
_ACCENT_RGB = _hex_rgb(CLR_ACCENT)
_MUTED_RGB = _hex_rgb(CLR_TEXT_MUTED)


# ── Animasyonlu input sınıfları ────────────────────────────────────────────
# Arama kutusundakiyle aynı: focus'ta amber kenarlık + dış glow.


class _AnimatedInput(QLineEdit):
    """QLineEdit — focus/hover'da amber animasyonlu kenarlık + glow."""

    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        if placeholder:
            self.setPlaceholderText(placeholder)
        self.setFixedHeight(40)
        self._t = 0.0
        self._h = 0.0  # hover
        self._anim_in = QPropertyAnimation(self, b"focusT", self)
        self._anim_in.setDuration(220)
        self._anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_out = QPropertyAnimation(self, b"focusT", self)
        self._anim_out.setDuration(180)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim_hov_in = QPropertyAnimation(self, b"hoverT", self)
        self._anim_hov_in.setDuration(150)
        self._anim_hov_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_hov_out = QPropertyAnimation(self, b"hoverT", self)
        self._anim_hov_out.setDuration(150)
        self._anim_hov_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self.setStyleSheet(
            "QLineEdit { background: transparent; border: none; "
            f"font-size: 13px; color: {CLR_TEXT}; padding: 0 2px; }}"
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _get_t(self):
        return self._t

    def _set_t(self, v):
        self._t = v
        self.update()

    focusT = pyqtProperty(float, _get_t, _set_t)

    def _get_h(self):
        return self._h

    def _set_h(self, v):
        self._h = v
        self.update()

    hoverT = pyqtProperty(float, _get_h, _set_h)

    def focusInEvent(self, e):
        self._anim_out.stop()
        self._anim_in.setStartValue(self._t)
        self._anim_in.setEndValue(1.0)
        self._anim_in.start()
        super().focusInEvent(e)

    def focusOutEvent(self, e):
        self._anim_in.stop()
        self._anim_out.setStartValue(self._t)
        self._anim_out.setEndValue(0.0)
        self._anim_out.start()
        super().focusOutEvent(e)

    def enterEvent(self, e):
        self._anim_hov_out.stop()
        self._anim_hov_in.setStartValue(self._h)
        self._anim_hov_in.setEndValue(1.0)
        self._anim_hov_in.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim_hov_in.stop()
        self._anim_hov_out.setStartValue(self._h)
        self._anim_hov_out.setEndValue(0.0)
        self._anim_hov_out.start()
        super().leaveEvent(e)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        t = max(self._t, self._h * 0.35)  # hover hafif, focus tam parlar

        path = QPainterPath()
        path.addRoundedRect(1.5, 1.5, w - 3, h - 3, 8, 8)

        # Glow
        if t > 0.01:
            gp = QPen(QColor(248, 180, 88, int(60 * t)), 5.0)
            p.setPen(gp)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)

        # Zemin
        p.fillPath(path, QColor(CLR_BG if self._t < 0.01 else CLR_SURFACE))

        # Kenarlık
        br = int(_BORDER_RGB[0] + (_ACCENT_RGB[0] - _BORDER_RGB[0]) * t)
        bg = int(_BORDER_RGB[1] + (_ACCENT_RGB[1] - _BORDER_RGB[1]) * t)
        bb = int(_BORDER_RGB[2] + (_ACCENT_RGB[2] - _BORDER_RGB[2]) * t)
        p.setPen(QPen(QColor(br, bg, bb), 1.5 + 0.5 * t))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.end()
        super().paintEvent(event)


class _AnimatedTextEdit(QWidget):
    """
    QTextEdit sarmalayıcısı — animasyonlu kenarlık efekti için dış QWidget
    paintEvent'te kenarlığı çizer, içteki QTextEdit metin girişini sağlar.
    QPainter çakışması olmaz çünkü kenarlık parent widget'ta çiziliyor.
    """

    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self._t = 0.0
        self._h = 0.0
        self._anim_in = QPropertyAnimation(self, b"focusT", self)
        self._anim_in.setDuration(220)
        self._anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_out = QPropertyAnimation(self, b"focusT", self)
        self._anim_out.setDuration(180)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim_hov_in = QPropertyAnimation(self, b"hoverT", self)
        self._anim_hov_in.setDuration(150)
        self._anim_hov_out = QPropertyAnimation(self, b"hoverT", self)
        self._anim_hov_out.setDuration(150)

        # İç QTextEdit — sınır/arka plan yok, wrapper çiziyor
        self._edit = QTextEdit()
        if placeholder:
            self._edit.setPlaceholderText(placeholder)
        self._edit.setStyleSheet(
            f"QTextEdit {{ background: transparent; border: none; "
            f"font-size: 13px; color: {CLR_TEXT}; padding: 4px 8px; }}"
        )
        self._edit.installEventFilter(self)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.addWidget(self._edit)
        self.setStyleSheet("background: transparent;")

    # QTextEdit API proxy'leri — dışarıdan toPlainText(), setPlaceholderText() çalışsın
    def toPlainText(self):
        return self._edit.toPlainText()

    def setPlaceholderText(self, t):
        self._edit.setPlaceholderText(t)

    def document(self):
        return self._edit.document()

    def _get_t(self):
        return self._t

    def _set_t(self, v):
        self._t = v
        self.update()

    focusT = pyqtProperty(float, _get_t, _set_t)

    def _get_h(self):
        return self._h

    def _set_h(self, v):
        self._h = v
        self.update()

    hoverT = pyqtProperty(float, _get_h, _set_h)

    def eventFilter(self, obj, event):
        if obj is self._edit:
            if event.type() == event.Type.FocusIn:
                self._anim_out.stop()
                self._anim_in.setStartValue(self._t)
                self._anim_in.setEndValue(1.0)
                self._anim_in.start()
            elif event.type() == event.Type.FocusOut:
                self._anim_in.stop()
                self._anim_out.setStartValue(self._t)
                self._anim_out.setEndValue(0.0)
                self._anim_out.start()
            elif event.type() == event.Type.Enter:
                self._anim_hov_out.stop()
                self._anim_hov_in.setStartValue(self._h)
                self._anim_hov_in.setEndValue(1.0)
                self._anim_hov_in.start()
            elif event.type() == event.Type.Leave:
                self._anim_hov_in.stop()
                self._anim_hov_out.setStartValue(self._h)
                self._anim_hov_out.setEndValue(0.0)
                self._anim_hov_out.start()
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        t = max(self._t, self._h * 0.35)

        path = QPainterPath()
        path.addRoundedRect(1.5, 1.5, w - 3, h - 3, 8, 8)
        p.fillPath(path, QColor(CLR_BG))

        if t > 0.01:
            p.setPen(QPen(QColor(248, 180, 88, int(55 * t)), 5.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)

        br = int(_BORDER_RGB[0] + (_ACCENT_RGB[0] - _BORDER_RGB[0]) * t)
        bg_ = int(_BORDER_RGB[1] + (_ACCENT_RGB[1] - _BORDER_RGB[1]) * t)
        bb = int(_BORDER_RGB[2] + (_ACCENT_RGB[2] - _BORDER_RGB[2]) * t)
        p.setPen(QPen(QColor(br, bg_, bb), 1.5 + 0.5 * t))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.end()


# ── El çizimi arama ikonu ────────────────────────────────────────────────


class _SearchIcon(QWidget):
    def __init__(self, size: int = 16, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.width()
        pen = QPen(
            QColor(CLR_TEXT_DIM),
            max(1.3, s / 11) if s > 0 else 1.3,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        d = s * 0.62
        p.drawEllipse(int(s * 0.06), int(s * 0.06), int(d), int(d))
        p.drawLine(
            int(s * 0.06 + d * 0.82),
            int(s * 0.06 + d * 0.82),
            int(s * 0.96),
            int(s * 0.96),
        )
        p.end()


class _CalendarDateEdit(QWidget):
    """
    GG/AA/YYYY formatında tarih girişi.
    QInputMask ile format zorunlu tutulur, animasyonlu kenarlık eklendi.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self._t = 0.0
        self._h = 0.0
        self._anim_in = QPropertyAnimation(self, b"focusT2", self)
        self._anim_in.setDuration(220)
        self._anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_out = QPropertyAnimation(self, b"focusT2", self)
        self._anim_out.setDuration(180)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim_hov_in = QPropertyAnimation(self, b"hoverT2", self)
        self._anim_hov_in.setDuration(150)
        self._anim_hov_out = QPropertyAnimation(self, b"hoverT2", self)
        self._anim_hov_out.setDuration(150)

        # İç input
        self._edit = QLineEdit()
        self._edit.setInputMask("99/99/9999")
        self._edit.setPlaceholderText("GG/AA/YYYY")
        self._edit.setStyleSheet(
            f"QLineEdit {{ background: transparent; border: none; "
            f"font-size: 13px; color: {CLR_TEXT}; padding: 0 2px; }}"
        )
        self._edit.installEventFilter(self)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 1, 12, 1)
        lay.addWidget(self._edit)
        self.setStyleSheet("background: transparent;")

    # QDate API proxy
    def date(self):
        txt = self._edit.text().replace("_", "").strip()
        try:
            parts = txt.split("/")
            if len(parts) == 3:
                d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                dt = QDate(y, m, d)
                if dt.isValid():
                    return dt
        except Exception:
            pass
        return QDate.currentDate()

    def setDate(self, d: QDate):
        if d.isValid():
            self._edit.setText(d.toString("dd/MM/yyyy"))

    def _get_t2(self):
        return self._t

    def _set_t2(self, v):
        self._t = v
        self.update()

    focusT2 = pyqtProperty(float, _get_t2, _set_t2)

    def _get_h2(self):
        return self._h

    def _set_h2(self, v):
        self._h = v
        self.update()

    hoverT2 = pyqtProperty(float, _get_h2, _set_h2)

    def eventFilter(self, obj, event):
        if obj is self._edit:
            if event.type() == event.Type.FocusIn:
                self._anim_out.stop()
                self._anim_in.setStartValue(self._t)
                self._anim_in.setEndValue(1.0)
                self._anim_in.start()
            elif event.type() == event.Type.FocusOut:
                self._anim_in.stop()
                self._anim_out.setStartValue(self._t)
                self._anim_out.setEndValue(0.0)
                self._anim_out.start()
            elif event.type() == event.Type.Enter:
                self._anim_hov_out.stop()
                self._anim_hov_in.setStartValue(self._h)
                self._anim_hov_in.setEndValue(1.0)
                self._anim_hov_in.start()
            elif event.type() == event.Type.Leave:
                self._anim_hov_in.stop()
                self._anim_hov_out.setStartValue(self._h)
                self._anim_hov_out.setEndValue(0.0)
                self._anim_hov_out.start()
        return super().eventFilter(obj, event)

    def enterEvent(self, e):
        self._anim_hov_out.stop()
        self._anim_hov_in.setStartValue(self._h)
        self._anim_hov_in.setEndValue(1.0)
        self._anim_hov_in.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim_hov_in.stop()
        self._anim_hov_out.setStartValue(self._h)
        self._anim_hov_out.setEndValue(0.0)
        self._anim_hov_out.start()
        super().leaveEvent(e)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        t = max(self._t, self._h * 0.35)

        path = QPainterPath()
        path.addRoundedRect(1.5, 1.5, w - 3, h - 3, 8, 8)
        p.fillPath(path, QColor(CLR_BG))

        if t > 0.01:
            p.setPen(QPen(QColor(248, 180, 88, int(55 * t)), 5.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)

        br = int(_BORDER_RGB[0] + (_ACCENT_RGB[0] - _BORDER_RGB[0]) * t)
        bg_ = int(_BORDER_RGB[1] + (_ACCENT_RGB[1] - _BORDER_RGB[1]) * t)
        bb = int(_BORDER_RGB[2] + (_ACCENT_RGB[2] - _BORDER_RGB[2]) * t)
        p.setPen(QPen(QColor(br, bg_, bb), 1.5 + 0.5 * t))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.end()


class _StyledComboBox(QComboBox):
    """
    QComboBox subclass — drop-down bölgesine el çizimi aşağı ok ikonu ekler.
    Hover animasyonu eklendi.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self._h = 0.0
        self._anim_hov_in = QPropertyAnimation(self, b"hoverT3", self)
        self._anim_hov_in.setDuration(150)
        self._anim_hov_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_hov_out = QPropertyAnimation(self, b"hoverT3", self)
        self._anim_hov_out.setDuration(150)
        self.setStyleSheet(f"""
            QComboBox {{
                background: {CLR_BG}; color: {CLR_TEXT};
                border: 1.5px solid {CLR_BORDER}; border-radius: 8px;
                padding: 6px 38px 6px 12px; font-size: 13px;
            }}
            QComboBox:focus {{ border-color: {CLR_ACCENT}; }}
            QComboBox::drop-down {{
                border: none;
                width: 38px;
                subcontrol-origin: border;
                subcontrol-position: right center;
                background: transparent;
            }}
            QComboBox::down-arrow {{ image: none; width: 0; height: 0; }}
            QComboBox QAbstractItemView {{
                background: {CLR_SURFACE};
                border: 1px solid {CLR_BORDER};
                selection-background-color: {CLR_ACCENT_SOFT};
                selection-color: {CLR_ACCENT};
                outline: none;
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                color: {CLR_TEXT};
                min-height: 32px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background: {CLR_HOVER};
            }}
            """)

    def _get_h3(self):
        return self._h

    def _set_h3(self, v):
        self._h = v
        self.update()

    hoverT3 = pyqtProperty(float, _get_h3, _set_h3)

    def enterEvent(self, e):
        self._anim_hov_out.stop()
        self._anim_hov_in.setStartValue(self._h)
        self._anim_hov_in.setEndValue(1.0)
        self._anim_hov_in.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim_hov_in.stop()
        self._anim_hov_out.setStartValue(self._h)
        self._anim_hov_out.setEndValue(0.0)
        self._anim_hov_out.start()
        super().leaveEvent(e)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        t = self._h * 0.35

        # Eski drop-down ikonunu kapat
        zone_w = 38
        zone_x = w - zone_w
        p.fillRect(zone_x, 2, zone_w - 2, h - 4, QColor(CLR_BG))

        # Animasyonlu kenarlık
        path = QPainterPath()
        path.addRoundedRect(1.5, 1.5, w - 3, h - 3, 8, 8)
        if t > 0.01:
            p.setPen(QPen(QColor(248, 180, 88, int(55 * t)), 5.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
        br = int(_BORDER_RGB[0] + (_ACCENT_RGB[0] - _BORDER_RGB[0]) * t)
        bg_ = int(_BORDER_RGB[1] + (_ACCENT_RGB[1] - _BORDER_RGB[1]) * t)
        bb = int(_BORDER_RGB[2] + (_ACCENT_RGB[2] - _BORDER_RGB[2]) * t)
        p.setPen(QPen(QColor(br, bg_, bb), 1.5 + 0.5 * t))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        # V şeklinde aşağı ok (chevron)
        iw2, ih2 = 12, 8
        ix = w - 26
        iy = (h - ih2) // 2
        pen = QPen(
            QColor(CLR_TEXT_MUTED),
            1.6,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        arrow = QPainterPath()
        arrow.moveTo(ix, iy)
        arrow.lineTo(ix + iw2 / 2, iy + ih2)
        arrow.lineTo(ix + iw2, iy)
        p.drawPath(arrow)
        p.end()


# ── Miktar kontrol widget'ı ───────────────────────────────────────────────


class QuantityWidget(QWidget):
    def __init__(self, product_code: str, current_qty: int, on_change, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(0)

        btn_ss = (
            f"QPushButton {{ background: {CLR_HOVER}; color: {CLR_TEXT_MUTED}; "
            f"border: 1px solid {CLR_BORDER}; font-size: 15px; font-weight: 500; "
            f"min-width: 26px; max-width: 26px; height: 26px; padding: 0; }}"
            f"QPushButton:hover {{ background: {CLR_ACCENT}; color: #111111; border-color: {CLR_ACCENT}; }}"
            f"QPushButton:pressed {{ background: {CLR_ACCENT_PRESSED}; }}"
        )
        self._btn_m = QPushButton("−")
        self._btn_m.setStyleSheet(
            btn_ss + "QPushButton { border-radius: 5px 0 0 5px; }"
        )
        self._btn_m.setCursor(Qt.CursorShape.PointingHandCursor)

        self._spin = QSpinBox()
        self._spin.setMinimum(OfferService.MIN_QUANTITY)
        self._spin.setMaximum(OfferService.MAX_QUANTITY)
        self._spin.setValue(current_qty)
        self._spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self._spin.setFixedSize(46, 26)
        self._spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._spin.setStyleSheet(
            f"QSpinBox {{ background: {CLR_SURFACE}; border: 1px solid {CLR_BORDER}; "
            f"border-left: none; border-right: none; border-radius: 0; "
            f"font-size: 13px; color: {CLR_TEXT}; padding: 0; }}"
            f"QSpinBox:focus {{ border-color: {CLR_ACCENT}; }}"
        )
        self._btn_p = QPushButton("+")
        self._btn_p.setStyleSheet(
            btn_ss + "QPushButton { border-radius: 0 5px 5px 0; }"
        )
        self._btn_p.setCursor(Qt.CursorShape.PointingHandCursor)

        lay.addWidget(self._btn_m)
        lay.addWidget(self._spin)
        lay.addWidget(self._btn_p)

        self._btn_m.clicked.connect(
            lambda: self._spin.setValue(
                max(OfferService.MIN_QUANTITY, self._spin.value() - 1)
            )
        )
        self._btn_p.clicked.connect(lambda: self._spin.setValue(self._spin.value() + 1))
        self._spin.valueChanged.connect(lambda v, code=product_code: on_change(code, v))


# ── Teklif tablosu ────────────────────────────────────────────────────────


class OfferTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(
            ["Ürün Kodu", "Ürün Adı", "Miktar", "Birim Fiyat", "Tutar", ""]
        )
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setShowGrid(False)
        self.setAlternatingRowColors(False)
        self.verticalHeader().setVisible(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.setStyleSheet(f"""
            QTableWidget {{
                background: {CLR_BG};
                border: none;
                gridline-color: transparent;
                outline: none;
                font-size: 13px;
            }}
            QTableWidget::item {{
                padding: 0 12px;
                border-bottom: 1px solid {CLR_BORDER};
                color: {CLR_TEXT};
            }}
            QTableWidget::item:hover {{ background: {CLR_HOVER}; }}
            QTableWidget::item:selected {{
                background: {CLR_ACCENT_SOFT};
                color: {CLR_TEXT};
            }}
            QHeaderView {{
                background: {CLR_SURFACE};
            }}
            QHeaderView::section {{
                background: {CLR_SURFACE};
                color: {CLR_TEXT_MUTED};
                font-size: 12px;
                font-weight: 700;
                padding: 0 12px;
                height: 40px;
                border: none;
                border-bottom: 1px solid {CLR_BORDER};
            }}
            QHeaderView::section:first {{
                color: {CLR_ACCENT};
            }}
        """)

        hdr = self.horizontalHeader()
        hdr.setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(0, 130)
        self.setColumnWidth(2, 110)
        self.setColumnWidth(3, 120)
        self.setColumnWidth(4, 110)
        self.setColumnWidth(5, 44)
        self.verticalHeader().setDefaultSectionSize(52)


# ── Toplamlar paneli ──────────────────────────────────────────────────────


class TotalsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        self.setStyleSheet(f"background: {CLR_SURFACE}; border-radius: 12px;")

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(0)

        # Başlık
        title = QLabel("Teklif Özeti")
        title.setStyleSheet(
            f"color: {CLR_TEXT}; font-size: 18px; font-weight: 700; background: transparent;"
        )
        root.addWidget(title)
        root.addSpacing(20)
        root.addWidget(_Divider())
        root.addSpacing(20)

        # Satırlar
        self.subtotal_label = self._row(root, "Ara Toplam")
        root.addSpacing(16)
        self.vat_label = self._row(root, "KDV (%20)")
        root.addSpacing(20)
        root.addWidget(_Divider())
        root.addSpacing(20)

        # Genel toplam
        gt_row = QWidget()
        gt_row.setStyleSheet("background: transparent;")
        gt_lay = QHBoxLayout(gt_row)
        gt_lay.setContentsMargins(0, 0, 0, 0)
        gt_lbl = QLabel("Genel Toplam")
        gt_lbl.setStyleSheet(
            f"color: {CLR_ACCENT}; font-size: 15px; font-weight: 700; background: transparent;"
        )
        self.total_label = QLabel("0,00 TL")
        self.total_label.setStyleSheet(
            f"color: {CLR_ACCENT}; font-size: 22px; font-weight: 800; background: transparent;"
        )
        self.total_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        gt_lay.addWidget(gt_lbl)
        gt_lay.addStretch()
        gt_lay.addWidget(self.total_label)
        root.addWidget(gt_row)

        root.addStretch()

        # KDV checkbox
        self.vat_checkbox = QCheckBox("KDV Dahil (%20)")
        self.vat_checkbox.setStyleSheet(
            f"color: {CLR_TEXT_MUTED}; font-size: 12px; background: transparent;"
        )
        root.addWidget(self.vat_checkbox)
        root.addSpacing(14)

        # PDF/Teklif oluştur butonu
        self.pdf_button = QPushButton("  Teklifi Oluştur")
        self.pdf_button.setFixedHeight(54)
        self.pdf_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pdf_button.setStyleSheet(f"""
            QPushButton {{
                background: {CLR_ACCENT};
                color: #111111;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
                padding-left: 8px;
            }}
            QPushButton:hover {{ background: {CLR_ACCENT_HOVER}; }}
            QPushButton:pressed {{ background: {CLR_ACCENT_PRESSED}; }}
        """)
        root.addWidget(self.pdf_button)

    def _row(self, layout, label_text: str) -> QLabel:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(
            f"color: {CLR_TEXT_MUTED}; font-size: 13px; background: transparent;"
        )
        val = QLabel("0,00 TL")
        val.setStyleSheet(
            f"color: {CLR_TEXT}; font-size: 13px; font-weight: 600; background: transparent;"
        )
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        rl.addWidget(lbl)
        rl.addStretch()
        rl.addWidget(val)
        layout.addWidget(row)
        return val


# ── Ana teklif penceresi ──────────────────────────────────────────────────


class OfferWindow(QWidget):

    go_back = pyqtSignal()

    OFFER_COLUMNS = {
        "product_code": 0,
        "name": 1,
        "quantity": 2,
        "price": 3,
        "total": 4,
        "delete": 5,
    }

    def __init__(self) -> None:
        super().__init__()
        self._service = OfferService()
        self._setup_ui()
        self._connect_signals()

    # ── UI kurulumu ───────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setWindowTitle("Teklif Oluştur")
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        _w, _h = get_window_size()
        self.setFixedSize(_w, _h)
        self.setStyleSheet(f"background: {CLR_BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Üst bar ────────────────────────────────────────────────
        topbar = QWidget()
        topbar.setFixedHeight(56)
        topbar.setStyleSheet(
            f"background: {CLR_SURFACE}; border-bottom: 1px solid {CLR_BORDER};"
        )
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(20, 0, 24, 0)
        tb.setSpacing(10)

        # Tıklanabilir belge ikonu — ana sayfaya dön
        from splash_window import LargeDocIcon, IconSweepButton

        logo_btn = IconSweepButton(height=40)
        logo_btn.setFixedSize(40, 40)
        logo_btn.clicked.connect(self.go_back)
        logo_lay = QHBoxLayout(logo_btn)
        logo_lay.setContentsMargins(0, 0, 0, 0)
        logo_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_lay.addWidget(LargeDocIcon(size=20))

        win_title = QLabel("Teklif Oluştur")
        win_title.setStyleSheet(
            f"color: {CLR_TEXT}; font-size: 16px; font-weight: 700; background: transparent;"
        )

        tb.addWidget(logo_btn)
        tb.addWidget(win_title)
        tb.addStretch()
        root.addWidget(topbar)

        # ── Ana içerik (padding ile) ────────────────────────────────
        content = QWidget()
        content.setStyleSheet(f"background: {CLR_BG};")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(14)

        # ── Üst form kartı ──────────────────────────────────────────
        form_card = QWidget()
        form_card.setStyleSheet(
            f"background: {CLR_SURFACE}; border-radius: 12px; border: 1px solid {CLR_BORDER};"
        )
        fc = QVBoxLayout(form_card)
        fc.setContentsMargins(20, 18, 20, 18)
        fc.setSpacing(14)

        # Satır 1: Müşteri Adı | Geçerlilik Tarihi | Müşteri Adresi (sağda uzun)
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        # Sol blok: Müşteri Adı + Ödeme Tipi
        left_block = QVBoxLayout()
        left_block.setSpacing(14)

        mu_lay = QVBoxLayout()
        mu_lay.setSpacing(5)
        mu_lay.addWidget(_FieldLabel("Müşteri Adı"))
        self.customer_input = _AnimatedInput("Müşteri seçin...")
        mu_lay.addWidget(self.customer_input)
        left_block.addLayout(mu_lay)

        pt_lay = QVBoxLayout()
        pt_lay.setSpacing(5)
        pt_lay.addWidget(_FieldLabel("Ödeme Tipi"))
        self.payment_type_combo = _StyledComboBox()
        self.payment_type_combo.addItems(["Havale / EFT", "Kredi Kartı"])
        pt_lay.addWidget(self.payment_type_combo)
        left_block.addLayout(pt_lay)

        row1.addLayout(left_block, 2)

        # Orta blok: Geçerlilik Tarihi + KDV
        mid_block = QVBoxLayout()
        mid_block.setSpacing(14)

        date_lay = QVBoxLayout()
        date_lay.setSpacing(5)
        date_lay.addWidget(_FieldLabel("Geçerlilik Tarihi"))
        self.validity_date_input = _CalendarDateEdit()
        self.validity_date_input.setDate(QDate.currentDate().addDays(30))
        date_lay.addWidget(self.validity_date_input)
        mid_block.addLayout(date_lay)

        self.vat_checkbox = QCheckBox("KDV Dahil (%20)")
        self.vat_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {CLR_TEXT};
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px; height: 18px;
                border: 1.5px solid {CLR_BORDER_DARK};
                border-radius: 4px;
                background: {CLR_SURFACE};
            }}
            QCheckBox::indicator:hover {{
                border-color: {CLR_ACCENT};
            }}
            QCheckBox::indicator:checked {{
                background: {CLR_ACCENT};
                border-color: {CLR_ACCENT};
            }}
            """)
        kdv_wrap = QVBoxLayout()
        kdv_wrap.setSpacing(5)
        kdv_wrap.addSpacing(18)  # _FieldLabel yüksekliğiyle hizala
        kdv_wrap.addWidget(self.vat_checkbox)
        mid_block.addLayout(kdv_wrap)

        row1.addLayout(mid_block, 2)

        # Sağ blok: Müşteri Adresi (çok satırlı, tam yükseklikte)
        addr_block = QVBoxLayout()
        addr_block.setSpacing(5)
        addr_block.addWidget(_FieldLabel("Müşteri Adresi"))
        self.customer_address_input = _AnimatedTextEdit("Müşteri adresi girin...")
        addr_block.addWidget(self.customer_address_input, 1)
        row1.addLayout(addr_block, 3)

        fc.addLayout(row1)
        cl.addWidget(form_card)

        # ── Alt alan: tablo + sağ panel ─────────────────────────────
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(14)

        # Sol: arama + tablo kartı
        table_card = QWidget()
        table_card.setStyleSheet(
            f"background: {CLR_SURFACE}; border-radius: 12px; border: 1px solid {CLR_BORDER};"
        )
        tc = QVBoxLayout(table_card)
        tc.setContentsMargins(16, 14, 16, 14)
        tc.setSpacing(10)

        # Arama kutusu
        search_wrap = QWidget()
        search_wrap.setFixedHeight(38)
        search_wrap.setStyleSheet(
            f"background: {CLR_BG}; border: 1.5px solid {CLR_BORDER}; border-radius: 8px;"
        )
        sw = QHBoxLayout(search_wrap)
        sw.setContentsMargins(10, 0, 10, 0)
        sw.setSpacing(8)
        sw.addWidget(_SearchIcon(16))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ürün ara...")
        self.search_input.setStyleSheet(
            f"QLineEdit {{ background: transparent; border: none; font-size: 13px; color: {CLR_TEXT}; }}"
        )
        sw.addWidget(self.search_input)
        tc.addWidget(search_wrap)

        # Tablo
        self.offer_table = OfferTable()
        tc.addWidget(self.offer_table, 1)

        # Boş durum widget'ı (tablo içinde gösterilecek)
        self._empty_widget = QWidget()
        self._empty_widget.setStyleSheet("background: transparent;")
        ew_lay = QVBoxLayout(self._empty_widget)
        ew_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ew_lay.setSpacing(8)

        # Kutu ikonu (ⓔ veya el çizimi)
        from splash_window import LargeDocIcon as _DocIcon

        # Kutu ikonu yerine unicode ⬡ → daha iyisi için özel çizim kullanalım
        empty_icon = QLabel("⬡")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon.setStyleSheet(
            f"color: {CLR_ACCENT}; font-size: 40px; background: transparent; "
            f"border: 2px solid {CLR_BORDER}; border-radius: 40px; "
            f"min-width: 80px; max-width: 80px; min-height: 80px; max-height: 80px;"
        )
        empty_title = QLabel("Ürün eklemek için arama yapın")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_title.setStyleSheet(
            f"color: {CLR_TEXT}; font-size: 14px; font-weight: 600; background: transparent;"
        )
        empty_sub = QLabel(
            "Ürün listesinden arama yaparak veya\nürün ekleyerek teklifinizi oluşturun."
        )
        empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_sub.setWordWrap(True)
        empty_sub.setStyleSheet(
            f"color: {CLR_TEXT_MUTED}; font-size: 12px; background: transparent;"
        )
        ew_lay.addWidget(empty_icon, 0, Qt.AlignmentFlag.AlignHCenter)
        ew_lay.addSpacing(6)
        ew_lay.addWidget(empty_title)
        ew_lay.addWidget(empty_sub)
        tc.addWidget(self._empty_widget)
        self._empty_widget.hide()
        self.offer_table.show()

        bottom_row.addWidget(table_card, 1)

        # Arama popup
        self._search_popup = QListWidget(self)
        self._search_popup.setFrameShape(QFrame.Shape.StyledPanel)
        self._search_popup.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._search_popup.setStyleSheet(f"""
            QListWidget {{
                background: {CLR_SURFACE};
                border: 1.5px solid {CLR_BORDER_DARK};
                border-radius: 8px;
                outline: none;
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 10px 16px;
                border-bottom: 1px solid {CLR_BORDER};
                color: {CLR_TEXT};
                min-height: 38px;
            }}
            QListWidget::item:last {{ border-bottom: none; }}
            QListWidget::item:hover {{ background: {CLR_HOVER}; }}
            QListWidget::item:selected {{
                background: {CLR_ACCENT_SOFT};
                color: {CLR_ACCENT};
            }}
        """)
        self._search_popup.hide()

        # Sağ: toplamlar paneli
        self._totals = TotalsWidget()
        self.subtotal_label = self._totals.subtotal_label
        self.vat_label = self._totals.vat_label
        self.total_label = self._totals.total_label
        self.vat_checkbox = self._totals.vat_checkbox
        self.pdf_button = self._totals.pdf_button
        bottom_row.addWidget(self._totals)

        cl.addLayout(bottom_row, 1)
        root.addWidget(content, 1)

    def mousePressEvent(self, event):
        """Boş alana tıklanınca odağı pencereye taşı — seçili alanlar temizlensin."""
        from PyQt6.QtWidgets import QApplication

        fw = QApplication.focusWidget()
        if fw is not None:
            fw.clearFocus()
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        super().mousePressEvent(event)

    def _connect_signals(self) -> None:
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.returnPressed.connect(self._quick_add_product)
        self._search_popup.itemClicked.connect(self._on_popup_item_clicked)
        self._search_popup.itemDoubleClicked.connect(self._on_popup_item_clicked)
        self.offer_table.cellClicked.connect(self._on_offer_cell_clicked)
        self.vat_checkbox.stateChanged.connect(self._refresh_totals)
        self.pdf_button.clicked.connect(self._generate_pdf)

    # ── Arama ─────────────────────────────────────────────────────────────

    def _on_search_changed(self, text: str) -> None:
        text = text.strip()
        if not text:
            self._search_popup.hide()
            return
        results = search_products(text)
        if not results:
            self._search_popup.hide()
            return

        self._search_popup.clear()
        for product in results:
            item = QListWidgetItem(f"{product.product_code}  —  {product.name}")
            item.setData(Qt.ItemDataRole.UserRole, product.product_code)
            self._search_popup.addItem(item)

        sc = self.search_input.parent()
        sc_pos = sc.mapTo(self, QPoint(0, sc.height()))
        visible_rows = min(len(results), SEARCH_POPUP_MAX_ROWS)
        self._search_popup.setGeometry(
            sc_pos.x(), sc_pos.y(), sc.width(), visible_rows * SEARCH_POPUP_ROW_H + 8
        )
        self._search_popup.raise_()
        self._search_popup.show()

    def _on_popup_item_clicked(self, item: QListWidgetItem) -> None:
        product_code = item.data(Qt.ItemDataRole.UserRole)
        self._search_popup.hide()
        self.search_input.clear()
        self.search_input.setFocus()
        self._add_product_by_code(product_code)

    def _quick_add_product(self) -> None:
        if self._search_popup.count() != 1:
            return
        item = self._search_popup.item(0)
        if item:
            self._on_popup_item_clicked(item)

    # ── Teklif yönetimi (business logic dokunulmadı) ──────────────────────

    def _add_product_by_code(self, product_code: str) -> None:
        product = get_product_by_code(product_code)
        if product is None:
            return
        if any(i.product_code == product_code for i in self._service.items):
            QMessageBox.warning(
                self,
                "Ürün Zaten Eklendi",
                f'"{product.name}" zaten teklif listesinde bulunuyor.',
            )
            return
        price = self._prompt_price(product.name)
        if price is None:
            return
        try:
            self._service.add_product(product, price)
            self._refresh_offer_table()
        except DuplicateItemError as e:
            QMessageBox.warning(self, "Ürün Zaten Eklendi", str(e))

    def _remove_from_offer(self, product_code: str) -> None:
        self._service.remove(product_code)
        self._refresh_offer_table()

    def _update_quantity(self, product_code: str, quantity: int) -> None:
        self._service.update_quantity(product_code, quantity)
        self._refresh_totals()

    def _update_price(self, product_code: str, price: float) -> None:
        self._service.update_price(product_code, price)
        self._refresh_offer_table()

    def _on_offer_cell_clicked(self, row: int, column: int) -> None:
        if column != self.OFFER_COLUMNS["price"]:
            return
        code_cell = self.offer_table.item(row, self.OFFER_COLUMNS["product_code"])
        if code_cell is None:
            return
        product_code = code_cell.text()
        current_item = next(
            (i for i in self._service.items if i.product_code == product_code), None
        )
        if current_item is None:
            return
        price = self._prompt_price(current_item.name, current_item.price)
        if price is not None:
            self._update_price(product_code, price)

    # ── Tablo yenileme ────────────────────────────────────────────────────

    def _refresh_offer_table(self) -> None:
        self.offer_table.setRowCount(0)
        is_empty = self._service.is_empty()
        self.offer_table.setVisible(not is_empty)
        self._empty_widget.setVisible(is_empty)

        for row, item in enumerate(self._service.items):
            self.offer_table.insertRow(row)
            self.offer_table.setRowHeight(row, 52)
            self.offer_table.setItem(
                row,
                self.OFFER_COLUMNS["product_code"],
                self._make_cell(item.product_code),
            )
            self.offer_table.setItem(
                row, self.OFFER_COLUMNS["name"], self._make_cell(item.name)
            )
            self.offer_table.setCellWidget(
                row,
                self.OFFER_COLUMNS["quantity"],
                QuantityWidget(item.product_code, item.quantity, self._update_quantity),
            )
            price_cell = self._make_cell(f"{item.price:,.2f} TL")
            price_cell.setToolTip("Fiyatı değiştirmek için tıklayın")
            self.offer_table.setItem(row, self.OFFER_COLUMNS["price"], price_cell)
            self.offer_table.setItem(
                row,
                self.OFFER_COLUMNS["total"],
                self._make_cell(f"{item.total:,.2f} TL"),
            )
            self.offer_table.setCellWidget(
                row,
                self.OFFER_COLUMNS["delete"],
                self._make_delete_button(item.product_code),
            )

        self._refresh_totals()

    def _refresh_totals(self) -> None:
        vat_rate = VAT_RATE if self.vat_checkbox.isChecked() else 0.0
        subtotal = self._service.subtotal
        vat = self._service.vat_amount(vat_rate)
        grand = self._service.grand_total(vat_rate)
        self.subtotal_label.setText(f"{subtotal:,.2f} TL")
        self.vat_label.setText(f"{vat:,.2f} TL")
        self.total_label.setText(f"{grand:,.2f} TL")

    # ── Widget factory ────────────────────────────────────────────────────

    def _make_cell(self, value: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(value))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return item

    def _make_spinbox(self, product_code: str, current_qty: int) -> QuantityWidget:
        return QuantityWidget(product_code, current_qty, self._update_quantity)

    def _make_delete_button(self, product_code: str) -> QPushButton:
        btn = QPushButton("✕")
        btn.setProperty("class", "danger")
        btn.setFixedSize(32, 32)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _, code=product_code: self._remove_from_offer(code))
        return btn

    def _prompt_price(
        self, product_name: str, current_price: float = 0.0
    ) -> float | None:
        text, ok = QInputDialog.getText(
            self,
            "Birim Fiyat",
            f"{product_name}\nBirim fiyatı giriniz:",
            text=f"{current_price:.2f}" if current_price else "",
        )
        if not ok:
            return None
        try:
            return max(0.0, float(text.strip().replace(",", ".")))
        except ValueError:
            QMessageBox.warning(
                self, "Geçersiz Fiyat", "Lütfen geçerli bir fiyat giriniz."
            )
            return self._prompt_price(product_name, current_price)

    # ── PDF (business logic dokunulmadı) ──────────────────────────────────

    def _generate_pdf(self) -> None:
        if self._service.is_empty():
            QMessageBox.warning(self, "Boş Teklif", "Teklife en az bir ürün ekleyin.")
            return
        customer_name = self.customer_input.text().strip() or "Müşteri"
        customer_address = self.customer_address_input.toPlainText().strip()
        validity_date = self.validity_date_input.date().toString("dd.MM.yyyy")
        payment_type = self.payment_type_combo.currentText()
        vat_rate = VAT_RATE if self.vat_checkbox.isChecked() else 0.0
        try:
            pdf_path = self._service.build_pdf(
                customer_name,
                vat_rate,
                customer_address=customer_address,
                validity_date=validity_date,
                payment_type=payment_type,
            )
            self._open_file(pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "PDF Hatası", f"PDF oluşturulamadı:\n{e}")

    def _open_file(self, path: str) -> None:
        if sys.platform == "win32":
            os.startfile(os.path.abspath(path))
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
