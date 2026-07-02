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
    QEvent,
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
    QDialog,
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
    QStyle,
    QStyleOptionButton,
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
    CLR_DANGER,
)

VAT_RATE = 0.20
SEARCH_POPUP_MAX_ROWS = 8
SEARCH_POPUP_ROW_H = 56
DELETE_BUTTON_Y_OFFSET = 0


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


class _StyledCheckBox(QCheckBox):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet(f"""
            QCheckBox {{
                color: {CLR_TEXT};
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                spacing: 10px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border: none;
                background: transparent;
            }}
        """)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        rect = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator, opt, self
        )
        bg = QColor(CLR_SURFACE)
        border = QColor(CLR_BORDER_DARK if self.underMouse() else CLR_BORDER)
        if self.isChecked():
            bg = QColor(CLR_ACCENT)
            border = QColor(CLR_ACCENT)

        box = rect.adjusted(1, 1, -1, -1)
        p.setPen(QPen(border, 1.5))
        p.setBrush(bg)
        p.drawRoundedRect(box, 5, 5)

        if self.isChecked():
            pen = QPen(
                QColor("#111111"),
                2.0,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
            p.setPen(pen)
            x = box.x()
            y = box.y()
            p.drawLine(x + 5, y + 10, x + 8, y + 13)
            p.drawLine(x + 8, y + 13, x + 15, y + 6)
        p.end()


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


def _format_try_money(cents: int) -> str:
    lira = cents // 100
    kurus = cents % 100
    lira_text = f"{lira:,}".replace(",", ".")
    return f"{lira_text},{kurus:02d}TL"


def _parse_try_money(text: str) -> float:
    clean = text.strip().upper().replace("TL", "").replace(".", "").replace(",", ".")
    return float(clean)


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
    Rakamlar yazıldıkça GG/AA/YYYY biçimine alınır, animasyonlu kenarlık eklendi.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self._t = 0.0
        self._h = 0.0
        self._invalid_date = False
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

        self._formatting = False

        # İç input
        self._edit = QLineEdit()
        self._edit.setMaxLength(10)
        self._edit.setPlaceholderText("GG/AA/YYYY")
        self._edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._edit.setStyleSheet(
            f"QLineEdit {{ background: transparent; border: none; "
            f"font-size: 13px; font-weight: 600; color: {CLR_TEXT}; padding: 0 2px; }}"
        )
        self._edit.installEventFilter(self)
        self._edit.textChanged.connect(self._format_date_text)
        self._edit.returnPressed.connect(self._finish_if_valid)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 1, 12, 1)
        lay.addWidget(self._edit)
        self.setStyleSheet("background: transparent;")

    def _set_invalid_date(self, invalid: bool, message: str = ""):
        if self._invalid_date == invalid and self.toolTip() == message:
            return
        self._invalid_date = invalid
        self.setToolTip(message)
        self._edit.setToolTip(message)
        self._edit.setStyleSheet(
            f"QLineEdit {{ background: transparent; border: none; "
            f"font-size: 13px; font-weight: 600; "
            f"color: {CLR_DANGER if invalid else CLR_TEXT}; padding: 0 2px; }}"
        )
        self.update()

    def _validate_date_parts(self, digits: str):
        if len(digits) >= 2 and int(digits[:2]) > 31:
            self._set_invalid_date(True, "Gün 31'den büyük olamaz.")
            return
        if len(digits) >= 4 and int(digits[2:4]) > 12:
            self._set_invalid_date(True, "Ay 12'den büyük olamaz.")
            return
        self._set_invalid_date(False)

    def _date_from_text(self) -> QDate | None:
        digits = "".join(ch for ch in self._edit.text() if ch.isdigit())
        if len(digits) != 8:
            return None
        d, m, y = int(digits[:2]), int(digits[2:4]), int(digits[4:8])
        dt = QDate(y, m, d)
        return dt if dt.isValid() else None

    def _finish_if_valid(self):
        if self._date_from_text() is None:
            self._set_invalid_date(True, "Geçerli bir tarih girin.")
            return
        self._set_invalid_date(False)
        self._edit.clearFocus()
        self.clearFocus()

    def _format_date_text(self, text: str):
        if self._formatting:
            return
        digits = "".join(ch for ch in text if ch.isdigit())[:8]
        self._validate_date_parts(digits)
        parts = []
        if digits:
            parts.append(digits[:2])
        if len(digits) > 2:
            parts.append(digits[2:4])
        if len(digits) > 4:
            parts.append(digits[4:8])
        formatted = "/".join(parts)
        if formatted == text:
            return
        self._formatting = True
        self._edit.setText(formatted)
        self._edit.setCursorPosition(len(formatted))
        self._formatting = False

    # QDate API proxy
    def date(self):
        return self._date_from_text() or QDate.currentDate()

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

        if self._invalid_date:
            p.setPen(QPen(QColor(224, 82, 82, 55), 5.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            p.setPen(QPen(QColor(CLR_DANGER), 1.8))
            p.drawPath(path)
            p.end()
            return

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


class _PriceDialog(QDialog):
    """Ürün fiyatı giriş diyaloğu — dark theme, amber accent."""

    def __init__(self, product_name: str, current_price: float = 0.0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Birim Fiyat")
        self.setFixedWidth(360)
        self.setModal(True)
        self.setStyleSheet(f"background: {CLR_BG};")
        self._formatting_price = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Gövde
        body = QWidget()
        body.setStyleSheet(f"background: {CLR_BG};")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(20, 18, 20, 18)
        b_lay.setSpacing(12)

        name_lbl = QLabel(product_name)
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet(
            f"color: {CLR_ACCENT}; font-size: 13px; font-weight: 600;"
        )
        b_lay.addWidget(name_lbl)

        field_lbl = QLabel("BİRİM FİYAT")
        field_lbl.setStyleSheet(
            f"color: {CLR_TEXT_DIM}; font-size: 10px; font-weight: 700; letter-spacing: 0.7px;"
        )
        b_lay.addWidget(field_lbl)

        self._input = _AnimatedInput()
        self._input.setPlaceholderText("0,00TL")
        self._input.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        if current_price:
            self._input.setText(_format_try_money(int(round(current_price * 100))))
        b_lay.addWidget(self._input)

        b_lay.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedSize(88, 38)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background: {CLR_SURFACE}; color: {CLR_TEXT}; "
            f"border: 1.5px solid {CLR_BORDER}; border-radius: 8px; font-size: 13px; font-weight: 500; }}"
            f"QPushButton:hover {{ background: {CLR_HOVER}; border-color: {CLR_BORDER_DARK}; }}"
        )

        btn_ok = QPushButton("Kaydet")
        btn_ok.setFixedSize(96, 38)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet(
            f"QPushButton {{ background: {CLR_ACCENT}; color: #111111; "
            f"border: none; border-radius: 8px; font-size: 13px; font-weight: 700; }}"
            f"QPushButton:hover {{ background: {CLR_ACCENT_HOVER}; }}"
            f"QPushButton:pressed {{ background: {CLR_ACCENT_PRESSED}; }}"
        )

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        b_lay.addLayout(btn_row)
        root.addWidget(body)

        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._on_accept)
        self._input.returnPressed.connect(self._on_accept)
        self._input.textChanged.connect(self._format_price_input)

    def _format_price_input(self, text: str) -> None:
        if self._formatting_price:
            return
        digits = "".join(ch for ch in text if ch.isdigit())
        self._formatting_price = True
        if not digits:
            self._input.clear()
            self._formatting_price = False
            return
        formatted = _format_try_money(int(digits))
        self._input.setText(formatted)
        self._input.setCursorPosition(max(0, len(formatted) - 2))
        self._formatting_price = False

    def _on_accept(self):
        try:
            val = _parse_try_money(self._input.text())
            if val < 0:
                raise ValueError
            self.accept()
        except ValueError:
            self._input.clear()
            self._input.setPlaceholderText("Geçersiz fiyat!")

    def price_value(self) -> float:
        try:
            return max(0.0, _parse_try_money(self._input.text()))
        except ValueError:
            return 0.0


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


class QuantityButton(QPushButton):
    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self._kind = kind
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet("border: none; background: transparent;")

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        bg = QColor(CLR_HOVER)
        border = QColor(CLR_BORDER)
        icon = QColor(CLR_TEXT_MUTED)
        if self.isDown():
            bg = QColor(CLR_ACCENT_PRESSED)
            border = QColor(CLR_ACCENT_PRESSED)
            icon = QColor("#111111")
        elif self.underMouse():
            bg = QColor(CLR_HOVER2)
            border = QColor(CLR_ACCENT)
            icon = QColor(CLR_ACCENT)

        rect = self.rect().adjusted(2, 2, -2, -2)
        p.setPen(QPen(border, 1))
        p.setBrush(bg)
        p.drawRoundedRect(rect, 6, 6)

        pen = QPen(icon, 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        cx = self.width() / 2
        cy = self.height() / 2
        half = 4.5
        p.drawLine(int(cx - half), int(cy), int(cx + half), int(cy))
        if self._kind == "plus":
            p.drawLine(int(cx), int(cy - half), int(cx), int(cy + half))
        p.end()


class QuantityValueBox(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self.setFixedSize(34, 28)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet(
            f"background: {CLR_HOVER}; border: 1px solid {CLR_BORDER}; "
            f"border-radius: 6px; font-size: 13px; font-weight: 600; "
            f"color: {CLR_TEXT}; padding: 0;"
        )

    def setValue(self, value: int) -> None:
        self._value = value
        self.setText(str(value))

    def value(self) -> int:
        return self._value


class QuantityWidget(QWidget):
    def __init__(self, product_code: str, current_qty: int, on_change, parent=None):
        super().__init__(parent)
        self._product_code = product_code
        self._on_change = on_change
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._btn_m = QuantityButton("minus")

        self._spin = QuantityValueBox()
        self._spin.setValue(current_qty)
        self._btn_p = QuantityButton("plus")

        lay.addWidget(self._btn_m)
        lay.addSpacing(5)
        lay.addWidget(self._spin)
        lay.addSpacing(12)
        lay.addWidget(self._btn_p)
        lay.addSpacing(4)

        self._btn_m.clicked.connect(
            lambda: self._set_quantity(
                max(OfferService.MIN_QUANTITY, self._spin.value() - 1)
            )
        )
        self._btn_p.clicked.connect(
            lambda: self._set_quantity(
                min(OfferService.MAX_QUANTITY, self._spin.value() + 1)
            )
        )

    def _set_quantity(self, value: int) -> None:
        if value == self._spin.value():
            return
        self._spin.setValue(value)
        self._on_change(self._product_code, value)


class DeleteButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet("border: none; background: transparent;")

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        icon = QColor(CLR_TEXT_DIM)
        if self.isDown():
            icon = QColor(CLR_DANGER)
        elif self.underMouse():
            icon = QColor(CLR_DANGER)

        pen = QPen(icon, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        cx = self.width() / 2
        cy = self.height() / 2
        half = 5.0
        p.drawLine(int(cx - half), int(cy - half), int(cx + half), int(cy + half))
        p.drawLine(int(cx + half), int(cy - half), int(cx - half), int(cy + half))
        p.end()


class DeleteCellWidget(QWidget):
    def __init__(self, button: DeleteButton, y_offset: int = 0, parent=None):
        super().__init__(parent)
        self._button = button
        self._y_offset = y_offset
        self._button.setParent(self)
        self.setStyleSheet("background: transparent;")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        x = (self.width() - self._button.width()) // 2
        y = (self.height() - self._button.height()) // 2 + self._y_offset
        self._button.move(x, y)


# ── Teklif tablosu ────────────────────────────────────────────────────────


class OfferTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered_row = -1
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(
            ["Ürün Kodu", "Miktar", "Birim Fiyat", "Tutar", ""]
        )
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.setShowGrid(False)
        self.setAlternatingRowColors(False)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
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
            QTableWidget::item:selected {{
                background: transparent;
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
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(1, 120)
        self.setColumnWidth(2, 130)
        self.setColumnWidth(3, 120)
        self.setColumnWidth(4, 44)
        self.verticalHeader().setDefaultSectionSize(52)

        # Miktar, Birim Fiyat, Tutar başlıklarını ortala
        for col, text in [(1, "Miktar"), (2, "Birim Fiyat"), (3, "Tutar")]:
            item = QTableWidgetItem(text)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            self.setHorizontalHeaderItem(col, item)

    def _set_hovered_row(self, row: int) -> None:
        if self._hovered_row == row:
            return
        self._hovered_row = row
        self.viewport().update()

    def mouseMoveEvent(self, event) -> None:
        self._set_hovered_row(self.rowAt(event.position().toPoint().y()))
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._set_hovered_row(-1)
        super().leaveEvent(event)

    def eventFilter(self, obj, event) -> bool:
        if event.type() in (QEvent.Type.Enter, QEvent.Type.MouseMove):
            pos = obj.mapTo(self.viewport(), QPoint(1, 1))
            self._set_hovered_row(self.rowAt(pos.y()))
        elif event.type() == QEvent.Type.Leave:
            self._set_hovered_row(-1)
        return super().eventFilter(obj, event)

    def watch_hover_widget(self, widget: QWidget) -> None:
        for child in [widget, *widget.findChildren(QWidget)]:
            child.setMouseTracking(True)
            child.installEventFilter(self)

    def paintEvent(self, event) -> None:
        if self._hovered_row >= 0:
            p = QPainter(self.viewport())
            row_top = self.rowViewportPosition(self._hovered_row)
            row_h = self.rowHeight(self._hovered_row)
            p.fillRect(0, row_top, self.viewport().width(), row_h, QColor(CLR_HOVER))
            p.end()
        super().paintEvent(event)


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
        "name": 0,  # artık kullanılmıyor ama business logic uyumu için tutuldu
        "quantity": 1,
        "price": 2,
        "total": 3,
        "delete": 4,
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
        form_card.setStyleSheet(f"background: {CLR_SURFACE}; border-radius: 12px;")
        fc = QVBoxLayout(form_card)
        fc.setContentsMargins(20, 18, 20, 18)
        fc.setSpacing(14)

        # Satır 1: Müşteri Adı | Geçerlilik Tarihi | Müşteri Adresi (sağda uzun)
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        # Sol-Orta blok: QGridLayout ile 2 sütun tam hizalı
        from PyQt6.QtWidgets import QGridLayout

        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_widget)
        grid.setSpacing(12)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        # Satır 0: Müşteri Adı | Geçerlilik Tarihi (başlıklar)
        grid.addWidget(_FieldLabel("Müşteri Adı"), 0, 0)
        grid.addWidget(_FieldLabel("Geçerlilik Tarihi"), 0, 1)

        # Satır 1: inputlar
        self.customer_input = _AnimatedInput(" Müşteri veya firma adını girin.")
        grid.addWidget(self.customer_input, 1, 0)

        self.validity_date_input = _CalendarDateEdit()
        grid.addWidget(self.validity_date_input, 1, 1)

        # Satır 2: Ödeme Tipi | KDV (başlıklar)
        grid.addWidget(_FieldLabel("Ödeme Tipi"), 2, 0)

        # Satır 3: inputlar
        self.payment_type_combo = _StyledComboBox()
        self.payment_type_combo.addItems(["Havale / EFT", "Kredi Kartı"])
        grid.addWidget(self.payment_type_combo, 3, 0)

        self.vat_checkbox = _StyledCheckBox("KDV Dahil (%20)")
        grid.addWidget(self.vat_checkbox, 3, 1, Qt.AlignmentFlag.AlignVCenter)

        row1.addWidget(grid_widget, 2)

        # Sağ blok: Müşteri Adresi (çok satırlı, tam yükseklikte)
        addr_block = QVBoxLayout()
        addr_block.setSpacing(5)
        addr_block.addWidget(_FieldLabel("Müşteri Adresi"))
        self.customer_address_input = _AnimatedTextEdit(
            " Müşterinin veya firmanın adresini girin."
        )
        addr_block.addWidget(self.customer_address_input, 1)
        row1.addLayout(addr_block, 3)

        fc.addLayout(row1)
        cl.addWidget(form_card)

        # ── Alt alan: tablo + sağ panel ─────────────────────────────
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(14)

        # Sol: arama + tablo kartı
        table_card = QWidget()
        table_card.setStyleSheet(f"background: {CLR_SURFACE}; border-radius: 12px;")
        tc = QVBoxLayout(table_card)
        tc.setContentsMargins(16, 14, 16, 14)
        tc.setSpacing(10)

        # Arama kutusu
        self.search_input = _AnimatedInput(" Ürün kodu veya ürün adıyla arama yapın.")
        self.search_input.setFixedHeight(40)
        # Büyüteç ikonunu sol tarafta göstermek için wrapper
        search_wrap = QWidget()
        search_wrap.setFixedHeight(40)
        search_wrap.setStyleSheet("background: transparent;")
        sw2 = QHBoxLayout(search_wrap)
        sw2.setContentsMargins(0, 0, 0, 0)
        sw2.setSpacing(0)
        sw2.addWidget(self.search_input)
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

        from splash_window import LargeDocIcon as _DocIcon

        empty_icon = QWidget()
        empty_icon.setFixedSize(80, 80)
        empty_icon.setStyleSheet(
            f"background: transparent; border: 2px solid {CLR_BORDER}; "
            f"border-radius: 40px;"
        )
        empty_icon_lay = QHBoxLayout(empty_icon)
        empty_icon_lay.setContentsMargins(0, 0, 0, 0)
        empty_icon_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon_lay.addWidget(_DocIcon(size=38))
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
                min-height: 52px;
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
        # Sabit boyut — içerik miktarına göre değişmez
        POPUP_W = 500
        POPUP_H = 170
        self._search_popup.setGeometry(sc_pos.x(), sc_pos.y(), POPUP_W, POPUP_H)
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
        current_item = next(
            (i for i in self._service.items if i.product_code == product_code), None
        )
        if current_item is not None:
            for row in range(self.offer_table.rowCount()):
                code_cell = self.offer_table.item(
                    row, self.OFFER_COLUMNS["product_code"]
                )
                if code_cell is None or code_cell.text() != product_code:
                    continue
                total_cell = self.offer_table.item(row, self.OFFER_COLUMNS["total"])
                if total_cell is not None:
                    total_cell.setText(f"{current_item.total:,.2f} TL")
                break
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
            qty_widget = QuantityWidget(
                item.product_code, item.quantity, self._update_quantity
            )
            self.offer_table.setCellWidget(
                row,
                self.OFFER_COLUMNS["quantity"],
                qty_widget,
            )
            self.offer_table.watch_hover_widget(qty_widget)
            price_cell = self._make_cell(f"{item.price:,.2f} TL")
            price_cell.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            price_cell.setToolTip("Fiyatı değiştirmek için tıklayın")
            self.offer_table.setItem(row, self.OFFER_COLUMNS["price"], price_cell)
            total_cell = self._make_cell(f"{item.total:,.2f} TL")
            total_cell.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            self.offer_table.setItem(row, self.OFFER_COLUMNS["total"], total_cell)
            delete_button = self._make_delete_button(item.product_code)
            delete_widget = DeleteCellWidget(
                delete_button, y_offset=DELETE_BUTTON_Y_OFFSET
            )
            self.offer_table.setCellWidget(
                row,
                self.OFFER_COLUMNS["delete"],
                delete_widget,
            )
            self.offer_table.watch_hover_widget(delete_widget)

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

    def _make_delete_button(self, product_code: str) -> DeleteButton:
        btn = DeleteButton()
        btn.clicked.connect(lambda _, code=product_code: self._remove_from_offer(code))
        return btn

    def _prompt_price(
        self, product_name: str, current_price: float = 0.0
    ) -> float | None:
        dialog = _PriceDialog(product_name, current_price, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.price_value()

    # ── PDF (business logic dokunulmadı) ──────────────────────────────────

    def _generate_pdf(self) -> None:
        if self._service.is_empty():
            QMessageBox.warning(self, "Boş Teklif", "Teklife en az bir ürün ekleyin.")
            return
        customer_name = self.customer_input.text().strip() or "Müşteri"
        customer_address = self.customer_address_input.toPlainText().strip() or "-"
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
