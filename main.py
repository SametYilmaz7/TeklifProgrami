"""
main.py  —  Ürünler ekranı UI (dark theme, amber accent)
Business logic dokunulmadı.
"""

from __future__ import annotations
import sys

from PyQt6.QtCore import (
    Qt,
    QRect,
    pyqtSignal,
    QPropertyAnimation,
    QEasingCurve,
    pyqtProperty,
)
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from product_dialog import ProductDialog
from offer_window import OfferWindow
from splash_window import LargeDocIcon, AmberSweepButton, IconSweepButton
from theme import (
    get_window_size,
    apply_theme,
    CLR_BG,
    CLR_SURFACE,
    CLR_HOVER,
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
from database import (
    create_database,
    add_product,
    get_products,
    delete_product,
    DatabaseError,
    DuplicateProductError,
)

create_database()


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """'#RRGGBB' formatındaki rengi (r, g, b) tuple'a çevirir."""
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# SearchBox animasyonunda renk interpolasyonu için RGB tuple'lar
CLR_TEXT_DIM_RGB = _hex_to_rgb(CLR_TEXT_DIM)
CLR_ACCENT_RGB = _hex_to_rgb(CLR_ACCENT)
CLR_BORDER_RGB = _hex_to_rgb(CLR_BORDER)


# ── Ortak widget sınıfları ─────────────────────────────────────────────────


class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background: {CLR_BORDER}; border: none;")


class SecondaryButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setProperty("class", "secondary")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {CLR_SURFACE};
                color: {CLR_TEXT};
                border: 1.5px solid {CLR_BORDER};
                border-radius: 8px;
                font-size: 13px;
                font-weight: 500;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background: {CLR_HOVER};
                border-color: {CLR_BORDER_DARK};
            }}
            QPushButton:pressed {{
                background: {CLR_BORDER_DARK};
            }}
            """)


class AccentButton(AmberSweepButton):
    """
    Amber primary buton — splash ekranındaki AmberSweepButton'ı kullanır.
    Hover/press animasyonları ana ekranla birebir aynıdır.
    """

    def __init__(self, text: str, parent=None):
        super().__init__(text, height=50, parent=parent)


# ── Özel onay diyaloğu (QMessageBox yerine — buton görünürlüğü garantili) ──


class ConfirmDialog(QDialog):
    """
    QMessageBox.question() yerine kullanılan, tam stil kontrolü bizde olan
    onay diyaloğu. Windows native tema çakışmasından etkilenmez.
    """

    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(420)
        self.setModal(True)
        self.setStyleSheet(f"background: {CLR_SURFACE};")
        self._result = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Gövde
        body = QWidget()
        body.setStyleSheet(f"background: {CLR_BG};")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(24, 22, 24, 20)
        b_lay.setSpacing(20)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"color: {CLR_TEXT}; font-size: 13px;")
        b_lay.addWidget(msg_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        btn_cancel = SecondaryButton("İptal")
        btn_cancel.setFixedSize(96, 38)

        btn_confirm = AccentButton("Evet, Sil")
        btn_confirm.setFixedSize(110, 38)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_confirm)
        b_lay.addLayout(btn_row)
        root.addWidget(body)

        btn_cancel.clicked.connect(self.reject)
        btn_confirm.clicked.connect(self.accept)

    @staticmethod
    def ask(parent, title: str, message: str) -> bool:
        """QMessageBox.question(...) == Yes yerine kullanılır."""
        dialog = ConfirmDialog(title, message, parent)
        return dialog.exec() == QDialog.DialogCode.Accepted


# ── Excel import diyalogu ──────────────────────────────────────────────────


class ExcelImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Excel'den Ürün Aktar")
        self.setMinimumWidth(620)
        self.setModal(True)
        self.excel_path = ""
        self.images_dir = ""
        self.setStyleSheet(f"background: {CLR_BG};")

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        body = QWidget()
        body.setStyleSheet(f"background: {CLR_BG};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(24, 22, 24, 20)
        bl.setSpacing(14)

        def field_lbl(txt):
            l = QLabel(txt.upper())
            l.setStyleSheet(
                f"color: {CLR_TEXT_DIM}; font-size: 10px; font-weight: 700; letter-spacing: 0.7px;"
            )
            return l

        bl.addWidget(field_lbl("Excel Dosyası  (Zorunlu)"))
        er = QHBoxLayout()
        er.setSpacing(8)
        self.excel_edit = QLineEdit()
        self.excel_edit.setPlaceholderText("Excel dosyası seçin…")
        self.excel_edit.setReadOnly(True)
        self.excel_edit.setFixedHeight(38)
        btn_excel = SecondaryButton("Gözat")
        btn_excel.setFixedSize(90, 38)
        er.addWidget(self.excel_edit)
        er.addWidget(btn_excel)
        bl.addLayout(er)

        bl.addWidget(Divider())

        bl.addWidget(field_lbl("Resimler Klasörü  (Opsiyonel)"))
        hint = QLabel(
            "Resimler ürün koduyla eşleştirilir — PRD-001.png gibi adlandırın."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {CLR_TEXT_MUTED}; font-size: 12px;")
        bl.addWidget(hint)

        ir = QHBoxLayout()
        ir.setSpacing(8)
        self.img_edit = QLineEdit()
        self.img_edit.setPlaceholderText("Klasör seçilmedi — resimler atlanır")
        self.img_edit.setReadOnly(True)
        self.img_edit.setFixedHeight(38)
        btn_img = SecondaryButton("Gözat")
        btn_img.setFixedSize(90, 38)
        btn_clr = SecondaryButton("✕")
        btn_clr.setFixedSize(38, 38)
        ir.addWidget(self.img_edit)
        ir.addWidget(btn_img)
        ir.addWidget(btn_clr)
        bl.addLayout(ir)

        bl.addSpacing(6)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()
        btn_cancel = SecondaryButton("İptal")
        btn_cancel.setFixedSize(96, 40)
        btn_ok = AccentButton("Aktarmayı Başlat")
        btn_ok.setFixedSize(170, 40)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        bl.addLayout(btn_row)
        root.addWidget(body)

        btn_excel.clicked.connect(self._pick_excel)
        btn_img.clicked.connect(self._pick_images_dir)
        btn_clr.clicked.connect(self._clear_images_dir)
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._on_accept)

    def _pick_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Excel Dosyası Seç", "", "Excel (*.xlsx *.xls);;Tümü (*)"
        )
        if path:
            self.excel_path = path
            self.excel_edit.setText(path)

    def _pick_images_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Resimler Klasörünü Seç")
        if path:
            self.images_dir = path
            self.img_edit.setText(path)

    def _clear_images_dir(self):
        self.images_dir = ""
        self.img_edit.clear()

    def _on_accept(self):
        if not self.excel_path:
            QMessageBox.warning(self, "Eksik", "Lütfen bir Excel dosyası seçin.")
            return
        self.accept()


# (HexIcon kaldırıldı — artık LargeDocIcon küçük boyutta kullanılıyor)


# ── Üst başlık bandı ────────────────────────────────────────────────────────


class TopBar(QWidget):
    """Sol logo + başlık, sağ pencere kontrolleri (gerçek frameless değilse kontrol görsel)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)
        self.setStyleSheet(f"background: {CLR_BG};")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 0, 20, 0)
        lay.setSpacing(10)

        self.back_btn = IconSweepButton(height=40)
        self.back_btn.setFixedSize(40, 40)
        back_icon_lay = QHBoxLayout(self.back_btn)
        back_icon_lay.setContentsMargins(0, 0, 0, 0)
        back_icon_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        back_icon_lay.addWidget(LargeDocIcon(size=20))
        lay.addWidget(self.back_btn)

        title = QLabel("Ürünler")
        title.setStyleSheet(f"color: {CLR_TEXT}; font-size: 19px; font-weight: 700;")
        lay.addWidget(title)
        lay.addStretch()


# ── Arama kutusu ────────────────────────────────────────────────────────────


class _SearchIcon(QWidget):
    """El çizimi büyüteç ikonu — karakter fontuna bağımlı değil, her zaman net."""

    def __init__(self, size: int = 18, parent=None):
        super().__init__(parent)
        self._size = size
        self._color = QColor(CLR_TEXT_DIM)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_color(self, color: QColor) -> None:
        self._color = color
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self._size
        pen_w = max(1.4, s / 11)
        pen = QPen(self._color, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # Lens (daire) — sol-üstte, sapa yer bırakacak şekilde
        lens_d = s * 0.62
        lens_x = s * 0.06
        lens_y = s * 0.06
        p.drawEllipse(int(lens_x), int(lens_y), int(lens_d), int(lens_d))

        # Sap — daireden sağ-alta uzanan kısa çizgi
        handle_x1 = lens_x + lens_d * 0.82
        handle_y1 = lens_y + lens_d * 0.82
        handle_x2 = s * 0.96
        handle_y2 = s * 0.96
        p.drawLine(int(handle_x1), int(handle_y1), int(handle_x2), int(handle_y2))
        p.end()


class SearchBox(QWidget):
    """
    Modern arama kutusu — el çizimi büyüteç ikonu, focus animasyonu.
    Focus alındığında: kenarlık amber'e geçer + dış glow belirir + ikon
    rengi amber'e döner. Tüm geçişler QPropertyAnimation ile yumuşaktır.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(46)
        self.setFixedWidth(380)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._focus_t = 0.0  # 0=normal, 1=focus (border/glow rengi için)

        self._anim_in = QPropertyAnimation(self, b"focusT", self)
        self._anim_in.setDuration(220)
        self._anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._anim_out = QPropertyAnimation(self, b"focusT", self)
        self._anim_out.setDuration(200)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InCubic)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 12, 0)
        lay.setSpacing(10)

        self._icon = _SearchIcon(17)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ürün adı veya kodu ile ara…")
        self.input.setStyleSheet(
            f"QLineEdit {{ background: transparent; border: none; font-size: 13px; "
            f"color: {CLR_TEXT}; padding: 0; }}"
        )
        self.input.installEventFilter(self)

        lay.addWidget(self._icon)
        lay.addWidget(self.input)

    # ── pyqtProperty: focusT (0→1 arası geçiş değeri) ──────────────────────

    def _get_focus_t(self) -> float:
        return self._focus_t

    def _set_focus_t(self, value: float) -> None:
        self._focus_t = value
        # İkon rengini de aynı geçişe göre interpolate et
        r = int(CLR_TEXT_DIM_RGB[0] + (CLR_ACCENT_RGB[0] - CLR_TEXT_DIM_RGB[0]) * value)
        g = int(CLR_TEXT_DIM_RGB[1] + (CLR_ACCENT_RGB[1] - CLR_TEXT_DIM_RGB[1]) * value)
        b = int(CLR_TEXT_DIM_RGB[2] + (CLR_ACCENT_RGB[2] - CLR_TEXT_DIM_RGB[2]) * value)
        self._icon.set_color(QColor(r, g, b))
        self.update()

    focusT = pyqtProperty(float, _get_focus_t, _set_focus_t)

    # ── Focus olaylarını yakala (QLineEdit child'ı üzerinden) ─────────────

    def eventFilter(self, obj, event):
        if obj is self.input:
            if event.type() == event.Type.FocusIn:
                self._anim_out.stop()
                self._anim_in.setStartValue(self._focus_t)
                self._anim_in.setEndValue(1.0)
                self._anim_in.start()
            elif event.type() == event.Type.FocusOut:
                self._anim_in.stop()
                self._anim_out.setStartValue(self._focus_t)
                self._anim_out.setEndValue(0.0)
                self._anim_out.start()
        return super().eventFilter(obj, event)

    # ── Çizim: zemin + animasyonlu kenarlık + glow ─────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        t = self._focus_t

        path = QPainterPath()
        path.addRoundedRect(1.5, 1.5, w - 3, h - 3, 11, 11)

        # Dış glow — focus arttıkça belirginleşen amber halo
        if t > 0:
            glow_pen = QPen(QColor(248, 180, 88, int(70 * t)), 5.0)
            p.setPen(glow_pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)

        # Zemin
        p.fillPath(path, QColor(CLR_SURFACE))

        # Kenarlık — koyu griden amber'e geçiş
        br = int(CLR_BORDER_RGB[0] + (CLR_ACCENT_RGB[0] - CLR_BORDER_RGB[0]) * t)
        bg = int(CLR_BORDER_RGB[1] + (CLR_ACCENT_RGB[1] - CLR_BORDER_RGB[1]) * t)
        bb = int(CLR_BORDER_RGB[2] + (CLR_ACCENT_RGB[2] - CLR_BORDER_RGB[2]) * t)
        border_pen = QPen(QColor(br, bg, bb), 1.5 + 0.5 * t)
        p.setPen(border_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.end()


# ── Ürün tablosu ─────────────────────────────────────────────────────────────


class _PlainTableItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        bg = index.data(Qt.ItemDataRole.BackgroundRole)
        if bg is not None:
            painter.fillRect(option.rect, bg)
        painter.setFont(option.font)
        painter.setPen(QColor(CLR_TEXT))
        text_rect = option.rect.adjusted(16, 0, -16, 0)
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            str(index.data(Qt.ItemDataRole.DisplayRole) or ""),
        )
        painter.setPen(QPen(QColor(CLR_BORDER), 1))
        painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
        painter.restore()


class ProductTable(QTableWidget):
    """
    Görseldeki gibi: Ürün Kodu (amber başlık) | Ürün Adı, satır başında küçük kutu ikonu.

    Hover efekti, item arka planlarını tek tek boyamak yerine, satırın tam
    genişliğinde yarı saydam bir "highlight bandı" (QWidget overlay) ile
    yapılır. Bu yöntem QSS/item-background çakışmalarından tamamen bağımsız
    çalışır çünkü item verisine hiç dokunmaz, sadece üstüne bir bant çizer.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["", "Ürün Kodu", "Ürün Adı"])
        self.horizontalHeader().setVisible(True)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.setShowGrid(False)
        self.setAlternatingRowColors(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)
        self.setItemDelegate(_PlainTableItemDelegate(self))

        self.setStyleSheet(f"""
            QTableWidget {{
                background: {CLR_BG};
                border: 1px solid {CLR_BORDER};
                border-radius: 12px;
                gridline-color: transparent;
                outline: none;
                font-size: 13px;
            }}
            QTableWidget::item {{
                padding: 0 16px;
                border-bottom: 1px solid {CLR_BORDER};
                color: {CLR_TEXT};
            }}
            QTableWidget::item:selected {{
                background: transparent;
                color: {CLR_TEXT};
            }}
            QHeaderView::section {{
                background: {CLR_SURFACE};
                color: {CLR_TEXT};
                font-size: 13px;
                font-weight: 700;
                padding: 0 16px;
                height: 46px;
                border: none;
                border-bottom: 1.5px solid {CLR_BORDER};
                text-align: left;
            }}
            """)

        hdr = self.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.setColumnWidth(0, 56)
        self.setColumnWidth(1, 180)
        self.verticalHeader().setDefaultSectionSize(56)

        self._hovered_row = -1
        self._selected_row = -1
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)

    # ── Satır bazlı hover (paintEvent'te item'lardan ÖNCE çizilir) ────────

    def eventFilter(self, obj, event):
        if obj is self.viewport():
            if event.type() == event.Type.MouseMove:
                row = self.rowAt(int(event.position().y()))
                if row != self._hovered_row:
                    old_row = self._hovered_row
                    self._hovered_row = row
                    self._refresh_row_state(old_row)
                    self._refresh_row_state(row)
            elif event.type() == event.Type.Leave:
                if self._hovered_row != -1:
                    old_row = self._hovered_row
                    self._hovered_row = -1
                    self._refresh_row_state(old_row)
        elif isinstance(obj, QWidget):
            if event.type() in (event.Type.Enter, event.Type.MouseMove):
                pos = obj.mapTo(self.viewport(), obj.rect().center())
                row = self.rowAt(pos.y())
                if row != self._hovered_row:
                    old_row = self._hovered_row
                    self._hovered_row = row
                    self._refresh_row_state(old_row)
                    self._refresh_row_state(row)
            elif event.type() == event.Type.Leave:
                if self._hovered_row != -1:
                    old_row = self._hovered_row
                    self._hovered_row = -1
                    self._refresh_row_state(old_row)
        return super().eventFilter(obj, event)

    def set_selected_row(self, row: int) -> None:
        if self._selected_row == row:
            return
        old_row = self._selected_row
        self._selected_row = row
        self._refresh_row_state(old_row)
        self._refresh_row_state(row)

    def watch_hover_widget(self, widget: QWidget) -> None:
        for child in [widget, *widget.findChildren(QWidget)]:
            child.setMouseTracking(True)
            child.installEventFilter(self)

    def _row_bg(self, row: int) -> QColor:
        if row >= 0 and (row == self._hovered_row or row == self._selected_row):
            return QColor(CLR_HOVER)
        return QColor(CLR_BG)

    def _refresh_row_state(self, row: int) -> None:
        if row < 0 or row >= self.rowCount():
            return
        bg = self._row_bg(row)
        for col in range(self.columnCount()):
            item = self.item(row, col)
            if item is not None:
                item.setData(Qt.ItemDataRole.BackgroundRole, bg)
        icon_widget = self.cellWidget(row, 0)
        if icon_widget is not None:
            icon_widget.setStyleSheet(f"background: {bg.name()};")
        self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)


# ── Ana pencere — Ürünler ekranı ────────────────────────────────────────────


class MainWindow(QWidget):

    go_back = pyqtSignal()  # Ana ekrana dön

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ürünler")
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        _w, _h = get_window_size()
        self.setFixedSize(_w, _h)
        self.setStyleSheet(f"background: {CLR_BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Üst bar ──────────────────────────────────────────────────
        self._topbar = TopBar()
        root.addWidget(self._topbar)
        root.addWidget(Divider())

        # ── Arama satırı (sağa yaslı) ───────────────────────────────
        search_row = QWidget()
        search_row.setFixedHeight(76)
        search_row.setStyleSheet(f"background: {CLR_BG};")
        sr_lay = QHBoxLayout(search_row)
        sr_lay.setContentsMargins(28, 16, 28, 16)
        sr_lay.addStretch()
        self._search = SearchBox()
        sr_lay.addWidget(self._search)
        root.addWidget(search_row)

        # ── Tablo alanı ──────────────────────────────────────────────
        table_wrap = QWidget()
        table_wrap.setStyleSheet(f"background: {CLR_BG};")
        tw_lay = QVBoxLayout(table_wrap)
        tw_lay.setContentsMargins(28, 0, 28, 16)
        self.table = ProductTable()
        tw_lay.addWidget(self.table)
        root.addWidget(table_wrap, 1)

        # ── Alt buton satırı (3 eşit genişlikte amber buton) ──────────
        btn_bar = QWidget()
        btn_bar.setFixedHeight(76)
        btn_bar.setStyleSheet(f"background: {CLR_BG};")
        bb_lay = QHBoxLayout(btn_bar)
        bb_lay.setContentsMargins(28, 10, 28, 10)
        bb_lay.setSpacing(14)

        self.btn_excel_import = AccentButton("⤓ Excel'den Aktar")
        self.btn_excel_import.setFixedHeight(50)

        self.btn_add = AccentButton("Ürün Ekle")
        self.btn_add.setFixedHeight(50)

        self.btn_delete = AccentButton("Ürünü Sil")
        self.btn_delete.setFixedHeight(50)

        bb_lay.addWidget(self.btn_excel_import, 1)
        bb_lay.addWidget(self.btn_add, 1)
        bb_lay.addWidget(self.btn_delete, 1)
        root.addWidget(btn_bar)

        # ── Footer ───────────────────────────────────────────────────
        footer = QWidget()
        footer.setFixedHeight(36)
        footer.setStyleSheet(f"background: {CLR_BG};")
        f_lay = QHBoxLayout(footer)
        f_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f_lbl1 = QLabel("Developed by ")
        f_lbl1.setStyleSheet(f"color: {CLR_TEXT_MUTED}; font-size: 12px;")
        f_lbl2 = QLabel("Datacrove")
        f_lbl2.setStyleSheet(f"color: {CLR_TEXT}; font-size: 12px; font-weight: 700;")
        f_lay.addWidget(f_lbl1)
        f_lay.addWidget(f_lbl2)
        root.addWidget(footer)

        # ── Geriye dönük uyumluluk: gizli QListWidget (eski kod bunu bekleyebilir) ──
        self.product_list = QListWidget()
        self.product_list.hide()
        self.btn_excel_template = QPushButton()
        self.btn_excel_template.hide()

        # ── Sinyal bağlantıları ─────────────────────────────────────
        self._topbar.back_btn.clicked.connect(self.go_back)
        self._search.input.textChanged.connect(self._on_search_changed)
        self.table.cellClicked.connect(self._on_row_clicked)
        self.btn_add.clicked.connect(self.add_product_ui)
        self.btn_delete.clicked.connect(self.delete_product_ui)
        self.btn_excel_import.clicked.connect(self.import_from_excel_ui)

        self._all_products = []
        self._selected_product_id = None
        self.load_products()

    # ── Ürün listesi ───────────────────────────────────────────────────────

    def load_products(self):
        self._all_products = get_products()
        self._populate_table(self._all_products)

    def _populate_table(self, products):
        self.table.setRowCount(0)
        self.table.set_selected_row(-1)
        self._selected_product_id = None
        for row, product in enumerate(products):
            self.table.insertRow(row)

            icon_wrap = QWidget()
            icon_wrap.setStyleSheet(f"background: {CLR_BG};")
            icon_wrap_lay = QHBoxLayout(icon_wrap)
            icon_wrap_lay.setContentsMargins(0, 0, 0, 0)
            icon_wrap_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_wrap_lay.addWidget(LargeDocIcon(size=18))
            icon_item = QTableWidgetItem("")
            icon_item.setFlags(icon_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            icon_item.setData(Qt.ItemDataRole.BackgroundRole, QColor(CLR_BG))
            self.table.setItem(row, 0, icon_item)
            self.table.setCellWidget(row, 0, icon_wrap)
            self.table.watch_hover_widget(icon_wrap)

            code_item = QTableWidgetItem(product.product_code)
            code_item.setFlags(code_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            code_item.setData(Qt.ItemDataRole.UserRole, product.id)
            code_item.setData(Qt.ItemDataRole.BackgroundRole, QColor(CLR_BG))
            self.table.setItem(row, 1, code_item)

            name_item = QTableWidgetItem(product.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setData(Qt.ItemDataRole.BackgroundRole, QColor(CLR_BG))
            self.table.setItem(row, 2, name_item)

    def _on_search_changed(self, text: str):
        text = text.strip().lower()
        if not text:
            self._populate_table(self._all_products)
            return
        filtered = [
            p
            for p in self._all_products
            if text in p.product_code.lower() or text in p.name.lower()
        ]
        self._populate_table(filtered)

    def _on_row_clicked(self, row: int, column: int):
        code_item = self.table.item(row, 1)
        if code_item:
            self.table.set_selected_row(row)
            self._selected_product_id = code_item.data(Qt.ItemDataRole.UserRole)

    def _confirm_delete(self, product_id: int):
        confirmed = ConfirmDialog.ask(
            self, "Ürün Sil", "Bu ürünü silmek istediğinizden emin misiniz?"
        )
        if not confirmed:
            return
        try:
            delete_product(product_id)
            self._selected_product_id = None
            self.load_products()
        except DatabaseError as e:
            QMessageBox.critical(self, "Veritabanı Hatası", str(e))

    # ── Business logic — dokunulmadı ──────────────────────────────────────

    def add_product_ui(self):
        dialog = ProductDialog()
        if not dialog.exec():
            return
        product_code = dialog.get_product_code().strip()
        name = dialog.get_product_name().strip()
        product_url = dialog.get_product_url().strip()
        if not product_code or not name:
            QMessageBox.warning(self, "Eksik Bilgi", "Ürün kodu ve adı zorunludur.")
            return
        try:
            add_product(product_code, name, dialog.image_path, product_url)
            self.load_products()
        except DuplicateProductError as e:
            QMessageBox.warning(self, "Kayıt Hatası", str(e))
        except DatabaseError as e:
            QMessageBox.critical(self, "Veritabanı Hatası", str(e))

    def delete_product_ui(self):
        if not self._selected_product_id:
            QMessageBox.warning(
                self, "Uyarı", "Lütfen silinecek ürünü tablodan seçiniz."
            )
            return
        self._confirm_delete(self._selected_product_id)

    def import_from_excel_ui(self):
        dialog = ExcelImportDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            from excel_import import import_from_excel
        except ImportError:
            QMessageBox.critical(self, "Modül Eksik", "excel_import.py bulunamadı.")
            return
        images_dir = dialog.images_dir or None
        result = import_from_excel(dialog.excel_path, images_dir)
        self.load_products()
        if result.errors and result.added == 0:
            QMessageBox.critical(self, "İçe Aktarma Hatası", result.summary())
        elif result.errors or result.skipped_duplicate or result.skipped_missing_fields:
            QMessageBox.warning(self, "İçe Aktarma Tamamlandı", result.summary())
        else:
            QMessageBox.information(self, "İçe Aktarma Başarılı", result.summary())

    def download_excel_template(self):
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Şablonu Kaydet", "urun_sablonu.xlsx", "Excel Dosyası (*.xlsx)"
        )
        if not save_path:
            return
        try:
            from excel_import import create_template

            create_template(save_path)
            QMessageBox.information(
                self,
                "Şablon Hazır",
                f"Şablon kaydedildi:\n{save_path}\n\n"
                "Resimler ürün koduyla eşleştirilir: PRD-001.png",
            )
        except Exception as e:
            QMessageBox.critical(self, "Şablon Hatası", f"Şablon oluşturulamadı:\n{e}")

    def open_offer_window(self):
        self.offer_window = OfferWindow()
        self.offer_window.show()

    def mousePressEvent(self, event):
        """
        Boş bir alana (arka plan, layout boşluğu) tıklanınca odağı pencereye
        taşır. Bu sayede arama kutusu gibi widget'lar FocusOut alır ve
        focus animasyonları (glow vb.) doğru şekilde söner.

        Not: Bu metod yalnızca tıklama hiçbir alt widget tarafından
        yakalanmadığında (yani gerçekten boş bir alana tıklandığında)
        çağrılır — Qt'nin event propagation modeli gereği.
        """
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        super().mousePressEvent(event)


if __name__ == "__main__":
    from slide_stack import SlideStackedWidget
    from splash_window import SplashWindow

    app = QApplication(sys.argv)
    apply_theme(app)

    stack = SlideStackedWidget()
    stack.setWindowTitle("Teklif Oluşturucu")

    splash = SplashWindow()
    products = MainWindow()
    offer = OfferWindow()

    stack.addWidget(splash)
    stack.addWidget(products)
    stack.addWidget(offer)

    splash.open_offer.connect(lambda: stack.slide_to(2, direction="right"))
    splash.open_products.connect(lambda: stack.slide_to(1, direction="right"))

    products.go_back.connect(lambda: stack.slide_to(0, direction="left"))
    offer.go_back.connect(lambda: stack.slide_to(0, direction="left"))

    stack.setCurrentIndex(0)

    def on_page_changed(idx):
        w, h = get_window_size()
        stack.setFixedSize(w, h)
        screen = app.primaryScreen().availableGeometry()
        stack.move(
            screen.x() + (screen.width() - w) // 2,
            screen.y() + (screen.height() - h) // 2,
        )

    stack.transition_finished.connect(on_page_changed)

    _sw, _sh = get_window_size()
    stack.setFixedSize(_sw, _sh)
    screen_geo = app.primaryScreen().availableGeometry()
    stack.move(
        screen_geo.x() + (screen_geo.width() - _sw) // 2,
        screen_geo.y() + (screen_geo.height() - _sh) // 2,
    )
    stack.show()
    sys.exit(app.exec())
