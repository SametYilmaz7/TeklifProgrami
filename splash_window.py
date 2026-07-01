"""
splash_window.py
~~~~~~~~~~~~~~~~
Ana ekran — görseldeki tasarımın birebir uygulaması.

Özellikler:
  - Düz koyu arka plan, dekorasyon yok
  - Native pencere çubuğu (sistem başlık çubuğu)
  - Sol üst köşe: küçük amber belge ikonu
  - Ortada: büyük amber belge ikonu (outline)
  - "TEKLİF" amber + "OLUŞTURUCU" beyaz başlık
  - Alt başlık metni
  - İki koyu buton (sweep hover efektli)
  - Footer: "Developed by DataCrove" (DataCrove amber)
"""

from __future__ import annotations
import math

from PyQt6.QtCore import (
    Qt,
    QPointF,
    QRect,
    pyqtSignal,
    QPropertyAnimation,
    QEasingCurve,
    pyqtProperty,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from theme import get_window_size

# ── Renkler ────────────────────────────────────────────────────────────────
C_BG = "#0F1115"
C_SURFACE = "#1A1D24"
C_SURFACE2 = "#222631"
C_BORDER = "#2E3440"
C_TEXT = "#F5F5F5"
C_MUTED = "#A7B0BE"
C_DIM = "#4A5060"
C_ACCENT = "#F8B458"
C_ACCENT_H = "#E3A653"
C_ACCENT_P = "#CA954D"


# ── Büyük merkez belge ikonu ──────────────────────────────────────────────


class LargeDocIcon(QWidget):
    """
    Amber outline belge ikonu (köşe kıvrımlı sayfa + içerik satırları).
    size parametresiyle farklı boyutlarda kullanılabilir
    (ana ekranda büyük, diğer ekranlarda küçük versiyon için).
    """

    def __init__(self, size: int = 140, parent=None):
        super().__init__(parent)
        self.SIZE = size
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.SIZE
        fold = max(4, int(s * 0.20))
        pad = max(2, int(s * 0.115))
        iw = s - pad * 2
        ih = int(iw * 1.18)
        ox = pad
        oy = (s - ih) // 2

        line_width = max(1.0, s / 56.0)

        # Hafif amber arka plan dolgusu
        bg_path = QPainterPath()
        bg_path.moveTo(ox, oy + fold)
        bg_path.lineTo(ox, oy + ih)
        bg_path.lineTo(ox + iw, oy + ih)
        bg_path.lineTo(ox + iw, oy)
        bg_path.lineTo(ox + fold, oy)
        bg_path.closeSubpath()
        p.setBrush(QColor(248, 180, 88, 12))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(bg_path)

        # Ana outline
        p.setPen(QPen(QColor(C_ACCENT), line_width * 1.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(bg_path)

        # Köşe kıvrımı
        fold_path = QPainterPath()
        fold_path.moveTo(ox, oy + fold)
        fold_path.lineTo(ox + fold, oy)
        fold_path.lineTo(ox + fold, oy + fold)
        fold_path.closeSubpath()
        p.setBrush(QColor(248, 180, 88, 20))
        p.setPen(QPen(QColor(C_ACCENT), line_width))
        p.drawPath(fold_path)

        # İçerik satırları — çok küçük boyutlarda atla (görsel kirlilik olmasın)
        if s >= 18:
            pen = QPen(
                QColor(C_ACCENT),
                line_width * 1.4,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
            p.setPen(pen)
            lx1 = ox + max(2, int(s * 0.115))
            lx2 = ox + iw - max(2, int(s * 0.10))
            line_ys = [
                oy + int(ih * 0.48),
                oy + int(ih * 0.61),
                oy + int(ih * 0.74),
            ]
            for i, ly in enumerate(line_ys):
                x2 = lx2 - max(2, int(s * 0.13)) if i == 2 else lx2
                p.drawLine(lx1, ly, x2, ly)
        p.end()


# ── Sweep hover efektli buton tabanı ──────────────────────────────────────


class _SweepButton(QPushButton):
    def __init__(self, text: str, height: int, parent=None):
        super().__init__(parent)
        self._text = text
        self._sweep = 0.0
        self._press = 0.0

        self.setFixedHeight(height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")

        self._anim_in = QPropertyAnimation(self, b"sweep", self)
        self._anim_in.setDuration(320)
        self._anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._anim_out = QPropertyAnimation(self, b"sweep", self)
        self._anim_out.setDuration(260)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InCubic)

        self._anim_press = QPropertyAnimation(self, b"press", self)
        self._anim_press.setDuration(80)
        self._anim_press.setEasingCurve(QEasingCurve.Type.OutQuad)

        self._anim_release = QPropertyAnimation(self, b"press", self)
        self._anim_release.setDuration(160)
        self._anim_release.setEasingCurve(QEasingCurve.Type.OutElastic)

    def _get_sweep(self):
        return self._sweep

    def _set_sweep(self, v):
        self._sweep = v
        self.update()

    sweep = pyqtProperty(float, _get_sweep, _set_sweep)

    def _get_press(self):
        return self._press

    def _set_press(self, v):
        self._press = v
        self.update()

    press = pyqtProperty(float, _get_press, _set_press)

    def enterEvent(self, event):
        self._anim_out.stop()
        self._anim_in.setStartValue(self._sweep)
        self._anim_in.setEndValue(1.0)
        self._anim_in.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._anim_in.stop()
        self._anim_out.setStartValue(self._sweep)
        self._anim_out.setEndValue(0.0)
        self._anim_out.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._anim_release.stop()
        self._anim_press.setStartValue(self._press)
        self._anim_press.setEndValue(1.0)
        self._anim_press.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._anim_press.stop()
        self._anim_release.setStartValue(self._press)
        self._anim_release.setEndValue(0.0)
        self._anim_release.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        scale = 1.0 - self._press * 0.04
        if scale < 1.0:
            p.translate(w / 2, h / 2)
            p.scale(scale, scale)
            p.translate(-w / 2, -h / 2)
        self._draw(p, w, h)
        p.end()

    def _draw(self, p, w, h):
        pass


# ── Amber taban + sweep buton (dolgu zaten amber olan butonlar için) ──────


class AmberSweepButton(_SweepButton):
    """
    _SweepButton tabanını kullanır ama PrimaryActionButton'ın aksine
    taban rengi her zaman amber'dir (koyu surface değil).
    Hover'da ortadan dışa parlak bir ışık sweep'i genişler, tıklamada
    %4 scale-down basınç efekti olur — splash ekranındakiyle birebir
    aynı _SweepButton mantığı, sadece taban rengi değişti.
    """

    def __init__(self, text: str, height: int = 50, parent=None):
        super().__init__(text, height=height, parent=parent)

    def _draw(self, p, w, h):
        radius = 10.0
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, radius, radius)

        # Taban — her zaman amber
        p.fillPath(path, QColor(C_ACCENT))

        # Sweep: hover'da ortadan dışa genişleyen parlak oval (splash ile aynı mantık)
        if self._sweep > 0:
            cx, cy = w / 2, h / 2
            grad = QRadialGradient(cx, cy, w * 0.6 * self._sweep + w * 0.1)
            grad.setColorAt(0.0, QColor(255, 255, 255, int(55 * self._sweep)))
            grad.setColorAt(0.45, QColor(255, 220, 140, int(30 * self._sweep)))
            grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.save()
            p.setClipPath(path)
            p.setBrush(grad)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(0, 0, w, h)
            p.restore()

        # Metin — her zaman koyu (amber zemin üzerinde kontrast için)
        font = QFont("Inter", 13, QFont.Weight.Bold)
        p.setFont(font)
        p.setPen(QColor("#111111"))
        p.drawText(QRect(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, self._text)


# ── İkon butonu (amber kenarlık + sweep glow) ────────────────────────────


class IconSweepButton(_SweepButton):
    """
    Şeffaf zemin, amber kenarlık. Hover'da kenarlık amber'e parlar ve
    içeride hafif bir amber glow sweep'i yayılır. Ürün Kodu/Teklif gibi
    ekranlardaki küçük ikon butonları için (içine child widget konabilir).
    """

    def __init__(self, height: int = 40, parent=None):
        super().__init__("", height=height, parent=parent)

    def _draw(self, p, w, h):
        from PyQt6.QtGui import QRadialGradient

        radius = 8.0
        path = QPainterPath()
        path.addRoundedRect(1, 1, w - 2, h - 2, radius, radius)

        # Taban — her zaman şeffaf/koyu
        p.fillPath(path, QColor(C_BG if self._sweep == 0 else C_SURFACE))

        # Hover sweep: amber soft glow
        if self._sweep > 0:
            cx, cy = w / 2, h / 2
            grad = QRadialGradient(cx, cy, w * 0.7)
            grad.setColorAt(0.0, QColor(248, 180, 88, int(40 * self._sweep)))
            grad.setColorAt(1.0, QColor(248, 180, 88, 0))
            p.save()
            p.setClipPath(path)
            p.setBrush(grad)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(0, 0, w, h)
            p.restore()

        # Kenarlık — sweep arttıkça amber'leşir
        alpha = int(180 + 75 * self._sweep)
        border_color = QColor(248, 180, 88, alpha)
        p.setPen(QPen(border_color, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)


# ── Primary buton (amber sweep) ────────────────────────────────────────────


class PrimaryActionButton(_SweepButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, height=74, parent=parent)

    def _draw(self, p, w, h):
        radius = 14.0
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, radius, radius)

        # Taban — koyu surface (görselde her iki buton da aynı koyu renk)
        p.fillPath(path, QColor(C_SURFACE))

        # Sweep: ortadan dışa amber parlaklık
        if self._sweep > 0:
            cx, cy = w / 2, h / 2
            grad = QRadialGradient(cx, cy, w * 0.6 * self._sweep + w * 0.1)
            grad.setColorAt(0.0, QColor(248, 180, 88, int(40 * self._sweep)))
            grad.setColorAt(0.5, QColor(248, 180, 88, int(15 * self._sweep)))
            grad.setColorAt(1.0, QColor(248, 180, 88, 0))
            p.save()
            p.setClipPath(path)
            p.setBrush(grad)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(0, 0, w, h)
            p.restore()

        # Kenarlık — hover'da amber'a geçiş
        br = int(46 + (248 - 46) * self._sweep)
        bg = int(52 + (180 - 52) * self._sweep)
        bb = int(64 + (88 - 64) * self._sweep)
        p.setPen(QPen(QColor(br, bg, bb), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        # Metin — beyazdan amber'a
        tr = int(245 + (248 - 245) * self._sweep)
        tg = int(245 - (245 - 180) * self._sweep)
        tb = int(245 - (245 - 88) * self._sweep)
        font = QFont("Inter", 13, QFont.Weight.Bold)
        p.setFont(font)
        p.setPen(QColor(tr, tg, tb))
        p.drawText(QRect(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, self._text)


# ── Secondary buton (aynı stil, daha soluk sweep) ─────────────────────────


class SecondaryActionButton(_SweepButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, height=74, parent=parent)

    def _draw(self, p, w, h):
        radius = 14.0
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, radius, radius)

        p.fillPath(path, QColor(C_SURFACE))

        if self._sweep > 0:
            cx, cy = w / 2, h / 2
            grad = QRadialGradient(cx, cy, w * 0.6 * self._sweep + w * 0.1)
            grad.setColorAt(0.0, QColor(248, 180, 88, int(28 * self._sweep)))
            grad.setColorAt(0.5, QColor(248, 180, 88, int(10 * self._sweep)))
            grad.setColorAt(1.0, QColor(248, 180, 88, 0))
            p.save()
            p.setClipPath(path)
            p.setBrush(grad)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(0, 0, w, h)
            p.restore()

        br = int(46 + (200 - 46) * self._sweep)
        bg = int(52 + (140 - 52) * self._sweep)
        bb = int(64 + (70 - 64) * self._sweep)
        p.setPen(QPen(QColor(br, bg, bb), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        tr = int(167 + (245 - 167) * self._sweep)
        tg = int(176 + (200 - 176) * self._sweep)
        tb = int(190 - (190 - 140) * self._sweep)
        font = QFont("Inter", 13, QFont.Weight.Bold)
        p.setFont(font)
        p.setPen(QColor(tr, tg, tb))
        p.drawText(QRect(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, self._text)


# ── Ana ekran penceresi ────────────────────────────────────────────────────


class SplashWindow(QWidget):
    open_offer = pyqtSignal()
    open_products = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Teklif Oluşturucu")
        # Native pencere çubuğu (sistem butonları) — FramelessWindowHint yok
        _w, _h = get_window_size()
        self.setFixedSize(_w, _h)
        self.setStyleSheet(f"QWidget {{ background: {C_BG}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── İnce yatay çizgi (üst boşluk için) ───────────────────────────
        topbar = QWidget()
        topbar.setFixedHeight(16)
        topbar.setStyleSheet(f"background: {C_BG};")
        root.addWidget(topbar)

        # ── İçerik ────────────────────────────────────────────────────────
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        cl.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Büyük belge ikonu
        cl.addStretch(2)
        icon_wrap = QWidget()
        icon_wrap.setStyleSheet("background: transparent;")
        iw_lay = QHBoxLayout(icon_wrap)
        iw_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        iw_lay.setContentsMargins(0, 0, 0, 0)
        iw_lay.addWidget(LargeDocIcon())
        cl.addWidget(icon_wrap)

        # Başlık
        cl.addSpacing(32)
        title_wrap = QWidget()
        title_wrap.setStyleSheet("background: transparent;")
        tw = QHBoxLayout(title_wrap)
        tw.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tw.setContentsMargins(0, 0, 0, 0)
        tw.setSpacing(0)

        lbl_accent = QLabel("TEKLİF ")
        lbl_accent.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 32px; font-weight: 800; "
            "font-family: Inter, Segoe UI, Arial; background: transparent; letter-spacing: 1px;"
        )
        lbl_white = QLabel("OLUŞTURUCU")
        lbl_white.setStyleSheet(
            f"color: {C_TEXT}; font-size: 32px; font-weight: 800; "
            "font-family: Inter, Segoe UI, Arial; background: transparent; letter-spacing: 1px;"
        )
        tw.addWidget(lbl_accent)
        tw.addWidget(lbl_white)
        cl.addWidget(title_wrap)

        # Alt başlık
        cl.addSpacing(12)
        subtitle = QLabel("Hızlı, Kolay, Profesyonel Teklif Yönetimi")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            f"color: {C_MUTED}; font-size: 13px; "
            "font-family: Inter, Segoe UI, Arial; background: transparent;"
        )
        cl.addWidget(subtitle)

        # Butonlar
        cl.addStretch(2)

        btn_wrap = QWidget()
        btn_wrap.setStyleSheet("background: transparent;")
        bw = QVBoxLayout(btn_wrap)
        bw.setContentsMargins(48, 0, 48, 0)
        bw.setSpacing(18)

        self.btn_offer = PrimaryActionButton("TEKLİF OLUŞTUR")
        self.btn_products = SecondaryActionButton("ÜRÜNLER")
        bw.addWidget(self.btn_offer)
        bw.addWidget(self.btn_products)
        cl.addWidget(btn_wrap)

        cl.addStretch(1)

        # Footer
        footer = QWidget()
        footer.setFixedHeight(48)
        footer.setStyleSheet("background: transparent;")
        fl = QHBoxLayout(footer)
        fl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fl.setSpacing(4)

        # İnce amber çizgiler
        footer_inner = QWidget()
        footer_inner.setStyleSheet("background: transparent;")
        fi = QHBoxLayout(footer_inner)
        fi.setContentsMargins(0, 0, 0, 0)
        fi.setSpacing(10)
        fi.setAlignment(Qt.AlignmentFlag.AlignCenter)

        line_l = QWidget()
        line_l.setFixedSize(60, 1)
        line_l.setStyleSheet(f"background: {C_ACCENT}; opacity: 0.4;")
        line_r = QWidget()
        line_r.setFixedSize(60, 1)
        line_r.setStyleSheet(f"background: {C_ACCENT}; opacity: 0.4;")

        lbl_dev = QLabel("Developed by")
        lbl_dev.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; background: transparent;"
        )
        lbl_brand = QLabel("DataCrove")
        lbl_brand.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 12px; font-weight: 700; background: transparent;"
        )

        fi.addWidget(line_l)
        fi.addWidget(lbl_dev)
        fi.addWidget(lbl_brand)
        fi.addWidget(line_r)
        fl.addWidget(footer_inner)
        cl.addWidget(footer)

        root.addWidget(content, 1)

        # Sinyaller
        self.btn_offer.clicked.connect(self.open_offer)
        self.btn_products.clicked.connect(self.open_products)

    # Pencere sabit — mouse olayları engellendi
    def mousePressEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        pass
