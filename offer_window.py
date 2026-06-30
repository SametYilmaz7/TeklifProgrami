"""
offer_window.py  —  Teklif penceresi UI (dark theme, amber accent)
Business logic (_service, _generate_pdf vb.) dokunulmadı.
"""

from __future__ import annotations
import os, subprocess, sys

from PyQt6.QtCore import Qt, QDate, QPoint, pyqtSignal
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
    CLR_DANGER_BG,
)

# Pencere boyutu çalışma zamanında hesaplanır
VAT_RATE = 0.20
SEARCH_POPUP_MAX_ROWS = 8
SEARCH_POPUP_ROW_H = 42


# ── Yardımcı widget'lar ────────────────────────────────────────────────────


class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background: {CLR_BORDER}; border: none;")


class FieldLabel(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text.upper(), parent)
        self.setStyleSheet(
            f"color: {CLR_TEXT_DIM}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 0.7px;"
        )


class AccentButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(38)


class SecondaryButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setProperty("class", "secondary")
        self.setCursor(Qt.CursorShape.PointingHandCursor)


# ── Toplamlar kartı ────────────────────────────────────────────────────────


class TotalsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(272)
        self.setStyleSheet(
            f"background: {CLR_SURFACE}; border-left: 1px solid {CLR_BORDER};"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Başlık
        hdr = QWidget()
        hdr.setFixedHeight(52)
        hdr.setStyleSheet(
            f"background: {CLR_SURFACE}; border-bottom: 1px solid {CLR_BORDER};"
        )
        h = QHBoxLayout(hdr)
        h.setContentsMargins(20, 0, 20, 0)
        t = QLabel("Özet")
        t.setStyleSheet(f"color: {CLR_TEXT}; font-size: 14px; font-weight: 700;")
        h.addWidget(t)
        root.addWidget(hdr)

        # KDV checkbox
        vw = QWidget()
        vw.setStyleSheet(f"background: {CLR_SURFACE};")
        vl = QHBoxLayout(vw)
        vl.setContentsMargins(20, 14, 20, 14)
        self.vat_checkbox = QCheckBox("KDV Dahil (%20)")
        vl.addWidget(self.vat_checkbox)
        root.addWidget(vw)
        root.addWidget(Divider())

        # Satırlar
        rows = QWidget()
        rows.setStyleSheet(f"background: {CLR_SURFACE};")
        rl = QVBoxLayout(rows)
        rl.setContentsMargins(20, 18, 20, 18)
        rl.setSpacing(14)
        self.subtotal_label = self._row(rl, "Ara Toplam")
        self.vat_label = self._row(rl, "KDV (%20)")
        root.addWidget(rows)
        root.addWidget(Divider())

        # Genel toplam bloğu — amber vurgulu
        total_card = QWidget()
        total_card.setFixedHeight(82)
        total_card.setStyleSheet(
            f"background: {CLR_BG}; border-bottom: 1px solid {CLR_BORDER};"
        )
        tc = QVBoxLayout(total_card)
        tc.setContentsMargins(20, 0, 20, 0)
        tc.setSpacing(2)
        tc_lbl = QLabel("GENEL TOPLAM")
        tc_lbl.setStyleSheet(
            f"color: {CLR_TEXT_DIM}; font-size: 10px; font-weight: 700; letter-spacing: 0.7px;"
        )
        self.total_label = QLabel("0,00 TL")
        self.total_label.setStyleSheet(
            f"color: {CLR_ACCENT}; font-size: 24px; font-weight: 700;"
        )
        tc.addStretch()
        tc.addWidget(tc_lbl)
        tc.addWidget(self.total_label)
        tc.addStretch()
        root.addWidget(total_card)

        root.addStretch()

        # PDF butonu
        pw = QWidget()
        pw.setStyleSheet(f"background: {CLR_SURFACE};")
        pl = QVBoxLayout(pw)
        pl.setContentsMargins(16, 16, 16, 18)
        self.pdf_button = AccentButton("PDF Oluştur")
        self.pdf_button.setFixedHeight(42)
        pl.addWidget(self.pdf_button)
        root.addWidget(pw)

    def _row(self, layout, label_text: str) -> QLabel:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {CLR_TEXT_MUTED}; font-size: 12px;")
        val = QLabel("0,00 TL")
        val.setStyleSheet(f"color: {CLR_TEXT}; font-size: 13px; font-weight: 600;")
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        rl.addWidget(lbl)
        rl.addStretch()
        rl.addWidget(val)
        layout.addWidget(row)
        return val


# ── Miktar kontrol widget'ı ────────────────────────────────────────────────


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


# ── Teklif tablosu ─────────────────────────────────────────────────────────


class OfferTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(
            ["Kod", "Ürün", "Miktar", "Birim Fiyat", "Tutar", ""]
        )
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)

        self.setStyleSheet(f"""
            QTableWidget {{
                background: {CLR_BG};
                alternate-background-color: {CLR_SURFACE};
                border: none;
                border-radius: 0;
                gridline-color: transparent;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 0 12px;
                border-bottom: 1px solid {CLR_BORDER};
                color: {CLR_TEXT};
                font-size: 13px;
            }}
            QTableWidget::item:hover {{
                background: {CLR_HOVER};
            }}
            QTableWidget::item:selected {{
                background: {CLR_ACCENT_SOFT};
                color: {CLR_TEXT};
                border-left: 3px solid {CLR_ACCENT};
            }}
            QHeaderView {{
                background: {CLR_SURFACE};
            }}
            QHeaderView::section {{
                background: {CLR_SURFACE};
                color: {CLR_TEXT_DIM};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.5px;
                padding: 0 12px;
                height: 36px;
                border: none;
                border-bottom: 1px solid {CLR_BORDER};
                border-right: 1px solid {CLR_BORDER};
            }}
            QHeaderView::section:last {{ border-right: none; }}
            """)

        hdr = self.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(0, 110)
        self.setColumnWidth(2, 128)
        self.setColumnWidth(3, 130)
        self.setColumnWidth(4, 118)
        self.setColumnWidth(5, 48)
        self.verticalHeader().setDefaultSectionSize(52)


# ── Ana teklif penceresi ───────────────────────────────────────────────────


class OfferWindow(QWidget):

    go_back = pyqtSignal()  # Ana ekrana dön

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

    # ── UI kurulumu ────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setWindowTitle("Teklif Oluştur")
        _w, _h = get_window_size()
        self.setFixedSize(_w, _h)
        self.setStyleSheet(f"background: {CLR_BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Üst bar ────────────────────────────────────────────────────
        topbar = QWidget()
        topbar.setFixedHeight(60)
        topbar.setStyleSheet(
            f"background: {CLR_SURFACE}; border-bottom: 1px solid {CLR_BORDER};"
        )
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(20, 0, 24, 0)
        tb.setSpacing(14)

        back_btn = QPushButton("←")
        back_btn.setProperty("class", "ghost")
        back_btn.setFixedSize(34, 34)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(
            f"QPushButton {{ background: {CLR_HOVER}; color: {CLR_TEXT_MUTED}; "
            f"border: 1px solid {CLR_BORDER}; border-radius: 8px; font-size: 15px; }}"
            f"QPushButton:hover {{ background: {CLR_HOVER2}; color: {CLR_TEXT}; }}"
        )
        back_btn.clicked.connect(self.go_back)

        win_title = QLabel("Yeni Teklif")
        win_title.setStyleSheet(
            f"color: {CLR_TEXT}; font-size: 15px; font-weight: 700;"
        )

        # Vurgu çizgisi (ince amber şerit)
        dot = QLabel("◆")
        dot.setStyleSheet(f"color: {CLR_ACCENT}; font-size: 12px;")

        tb.addWidget(back_btn)
        tb.addWidget(dot)
        tb.addWidget(win_title)
        tb.addStretch()
        root.addWidget(topbar)

        # ── Gövde ──────────────────────────────────────────────────────
        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        # Sol: form + tablo
        left = QWidget()
        left.setStyleSheet(f"background: {CLR_BG};")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        # Müşteri bilgileri satırı
        cbar = QWidget()
        cbar.setFixedHeight(96)
        cbar.setStyleSheet(
            f"background: {CLR_BG}; border-bottom: 1px solid {CLR_BORDER};"
        )
        cb = QHBoxLayout(cbar)
        cb.setContentsMargins(24, 12, 24, 12)
        cb.setSpacing(16)

        def field(label, widget, stretch=1):
            w = QVBoxLayout()
            w.setSpacing(5)
            w.addWidget(FieldLabel(label))
            w.addWidget(widget)
            cb.addLayout(w, stretch)

        self.customer_input = QLineEdit()
        self.customer_input.setPlaceholderText("Müşteri adını giriniz…")
        self.customer_input.setFixedHeight(38)

        self.validity_date_input = QDateEdit()
        self.validity_date_input.setCalendarPopup(True)
        self.validity_date_input.setDisplayFormat("dd.MM.yyyy")
        self.validity_date_input.setDate(QDate.currentDate().addDays(30))
        self.validity_date_input.setFixedHeight(38)

        self.payment_type_combo = QComboBox()
        self.payment_type_combo.addItems(["Havale / EFT", "Kredi Kartı"])
        self.payment_type_combo.setFixedHeight(38)

        field("Müşteri Adı", self.customer_input, 2)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {CLR_BORDER}; background: {CLR_BORDER};")
        sep.setFixedWidth(1)
        cb.addWidget(sep)

        field("Geçerlilik Tarihi", self.validity_date_input, 1)
        field("Ödeme Tipi", self.payment_type_combo, 1)
        ll.addWidget(cbar)

        # Adres satırı
        abar = QWidget()
        abar.setFixedHeight(62)
        abar.setStyleSheet(
            f"background: {CLR_BG}; border-bottom: 1px solid {CLR_BORDER};"
        )
        ab = QHBoxLayout(abar)
        ab.setContentsMargins(24, 8, 24, 8)
        ab.setSpacing(12)
        ab.addWidget(FieldLabel("Müşteri Adresi"))
        self.customer_address_input = QTextEdit()
        self.customer_address_input.setPlaceholderText("Müşteri adresini giriniz…")
        self.customer_address_input.setFixedHeight(40)
        self.customer_address_input.setStyleSheet(
            f"QTextEdit {{ background: {CLR_SURFACE}; border: 1.5px solid {CLR_BORDER}; "
            f"border-radius: 8px; padding: 6px 10px; font-size: 13px; color: {CLR_TEXT}; }}"
            f"QTextEdit:focus {{ border-color: {CLR_ACCENT}; }}"
        )
        ab.addWidget(self.customer_address_input, 1)
        ll.addWidget(abar)

        # Arama çubuğu
        sbar = QWidget()
        sbar.setFixedHeight(58)
        sbar.setStyleSheet(
            f"background: {CLR_BG}; border-bottom: 1px solid {CLR_BORDER};"
        )
        sb = QHBoxLayout(sbar)
        sb.setContentsMargins(24, 9, 24, 9)

        search_wrap = QWidget()
        search_wrap.setFixedHeight(40)
        search_wrap.setStyleSheet(
            f"background: {CLR_SURFACE}; border: 1.5px solid {CLR_BORDER}; border-radius: 8px;"
        )
        sw = QHBoxLayout(search_wrap)
        sw.setContentsMargins(10, 0, 10, 0)
        sw.setSpacing(8)

        search_icon = QLabel("⌕")
        search_icon.setFixedWidth(20)
        search_icon.setStyleSheet(
            f"color: {CLR_TEXT_DIM}; font-size: 16px; border: none;"
        )

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ürün kodu veya ürün adı ile ara…")
        self.search_input.setStyleSheet(
            f"QLineEdit {{ background: transparent; border: none; font-size: 13px; color: {CLR_TEXT}; }}"
        )

        sw.addWidget(search_icon)
        sw.addWidget(self.search_input)
        sb.addWidget(search_wrap)
        ll.addWidget(sbar)

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
            QListWidget::item:hover {{
                background: {CLR_HOVER};
            }}
            QListWidget::item:selected {{
                background: {CLR_ACCENT_SOFT};
                color: {CLR_ACCENT};
                border-left: 3px solid {CLR_ACCENT};
            }}
            """)
        self._search_popup.hide()

        # Tablo
        self.offer_table = OfferTable()
        ll.addWidget(self.offer_table, 1)

        body_lay.addWidget(left, 1)

        # Sağ: toplamlar
        self._totals = TotalsWidget()
        self.subtotal_label = self._totals.subtotal_label
        self.vat_label = self._totals.vat_label
        self.total_label = self._totals.total_label
        self.vat_checkbox = self._totals.vat_checkbox
        self.pdf_button = self._totals.pdf_button
        body_lay.addWidget(self._totals)

        root.addWidget(body, 1)

    def _connect_signals(self) -> None:
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.returnPressed.connect(self._quick_add_product)
        self._search_popup.itemClicked.connect(self._on_popup_item_clicked)
        self._search_popup.itemDoubleClicked.connect(self._on_popup_item_clicked)
        self.offer_table.cellClicked.connect(self._on_offer_cell_clicked)
        self.vat_checkbox.stateChanged.connect(self._refresh_totals)
        self.pdf_button.clicked.connect(self._generate_pdf)

    # ── Arama (business logic dokunulmadı) ────────────────────────────────

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
