"""
main.py  —  Ürünler ekranı UI (dark theme, amber accent)
Business logic dokunulmadı.
"""

from __future__ import annotations
import sys

from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, pyqtSignal
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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from product_dialog import ProductDialog
from offer_window import OfferWindow
from splash_window import LargeDocIcon
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
    CLR_DANGER,
    CLR_DANGER_BG,
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


class AccentButton(QPushButton):
    """Amber primary buton — stil garantili (global QSS'e bağımlı değil)."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {CLR_ACCENT};
                color: #111111;
                border: none;
                border-radius: 10px;
                padding: 9px 20px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {CLR_ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background: {CLR_ACCENT_PRESSED};
            }}
            """)


# ── Excel import diyalogu ──────────────────────────────────────────────────


class ExcelImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Excel'den Ürün Aktar")
        self.setMinimumWidth(540)
        self.setModal(True)
        self.excel_path = ""
        self.images_dir = ""

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        header = QWidget()
        header.setFixedHeight(58)
        header.setStyleSheet(
            f"background: {CLR_SURFACE}; border-bottom: 1px solid {CLR_BORDER};"
        )
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(24, 0, 24, 0)
        title_lbl = QLabel("Excel'den Ürün Aktar")
        title_lbl.setStyleSheet(
            f"color: {CLR_TEXT}; font-size: 15px; font-weight: 700;"
        )
        accent_dot = QLabel("●")
        accent_dot.setStyleSheet(
            f"color: {CLR_ACCENT}; font-size: 18px; margin-right: 6px;"
        )
        h_lay.addWidget(accent_dot)
        h_lay.addWidget(title_lbl)
        h_lay.addStretch()
        root.addWidget(header)

        body = QWidget()
        body.setStyleSheet(f"background: {CLR_BG};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(24, 20, 24, 20)
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
        btn_excel.setFixedSize(72, 38)
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
        btn_img.setFixedSize(72, 38)
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
        btn_cancel.setFixedHeight(38)
        btn_ok = AccentButton("Aktarmayı Başlat")
        btn_ok.setFixedHeight(38)
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

        self.back_btn = QPushButton()
        self.back_btn.setFixedSize(40, 40)
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1.5px solid {CLR_ACCENT}; "
            f"border-radius: 8px; }}"
            f"QPushButton:hover {{ background: {CLR_ACCENT_SOFT}; }}"
        )
        # Buton içine ortalanmış küçük belge ikonu (ana ekrandaki ikonun küçük hali)
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


class SearchBox(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setFixedWidth(380)
        self.setStyleSheet(
            f"background: {CLR_SURFACE}; border: 1.5px solid {CLR_BORDER}; border-radius: 10px;"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(8)

        icon = QLabel("⌕")
        icon.setStyleSheet(f"color: {CLR_TEXT_DIM}; font-size: 16px; border: none;")
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ürün adı veya kodu ile ara…")
        self.input.setStyleSheet(
            f"QLineEdit {{ background: transparent; border: none; font-size: 13px; color: {CLR_TEXT}; }}"
        )
        lay.addWidget(icon)
        lay.addWidget(self.input)


# ── Ürün tablosu ─────────────────────────────────────────────────────────────


class ProductTable(QTableWidget):
    """Görseldeki gibi: Ürün Kodu (amber başlık) | Ürün Adı, satır başında küçük kutu ikonu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["", "Ürün Kodu", "Ürün Adı"])
        self.horizontalHeader().setVisible(True)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setShowGrid(False)
        self.setAlternatingRowColors(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

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
            QTableWidget::item:hover {{
                background: {CLR_HOVER};
            }}
            QTableWidget::item:selected {{
                background: {CLR_ACCENT_SOFT};
                color: {CLR_TEXT};
                border-left: 3px solid {CLR_ACCENT};
            }}
            QHeaderView::section {{
                background: {CLR_SURFACE};
                color: {CLR_TEXT_DIM};
                font-size: 12px;
                font-weight: 700;
                padding: 0 16px;
                height: 46px;
                border: none;
                border-bottom: 1.5px solid {CLR_BORDER};
            }}
            QHeaderView::section:nth-child(2) {{
                color: {CLR_ACCENT};
            }}
            """)

        hdr = self.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.setColumnWidth(0, 56)
        self.setColumnWidth(1, 180)
        self.verticalHeader().setDefaultSectionSize(56)

        # "Ürün Kodu" başlığını amber yapmak için ayrı bir özel item kullan
        kod_header_item = QTableWidgetItem("Ürün Kodu")
        self.setHorizontalHeaderItem(1, kod_header_item)


# ── Ana pencere — Ürünler ekranı ────────────────────────────────────────────


class MainWindow(QWidget):

    go_back = pyqtSignal()  # Ana ekrana dön

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ürünler")
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

        self.btn_excel_import = AccentButton("⤓  Excel'den Aktar")
        self.btn_excel_import.setFixedHeight(50)

        self.btn_add = AccentButton("＋  Ürün Ekle")
        self.btn_add.setFixedHeight(50)

        self.btn_delete = AccentButton("🗑  Ürünü Sil")
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
        for row, product in enumerate(products):
            self.table.insertRow(row)

            icon_wrap = QWidget()
            icon_wrap_lay = QHBoxLayout(icon_wrap)
            icon_wrap_lay.setContentsMargins(0, 0, 0, 0)
            icon_wrap_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_wrap_lay.addWidget(LargeDocIcon(size=18))
            self.table.setCellWidget(row, 0, icon_wrap)

            code_item = QTableWidgetItem(product.product_code)
            code_item.setFlags(code_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            code_item.setData(Qt.ItemDataRole.UserRole, product.id)
            self.table.setItem(row, 1, code_item)

            name_item = QTableWidgetItem(product.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
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
            self._selected_product_id = code_item.data(Qt.ItemDataRole.UserRole)

    def _confirm_delete(self, product_id: int):
        confirm = QMessageBox.question(
            self,
            "Ürün Sil",
            "Bu ürünü silmek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
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
