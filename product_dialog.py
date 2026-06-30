"""
product_dialog.py
~~~~~~~~~~~~~~~~~~
Tekil ürün ekleme diyaloğu — dark theme, amber accent.
Business logic (select_image, get_product_code vb.) dokunulmadı,
widget isimleri (code_input, name_input, vb.) korundu.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from theme import (
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
)


class _FieldLabel(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            f"color: {CLR_ACCENT}; font-size: 13px; font-weight: 600; background: transparent;"
        )


class _Input(QLineEdit):
    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        if placeholder:
            self.setPlaceholderText(placeholder)
        self.setFixedHeight(42)
        self.setStyleSheet(f"""
            QLineEdit {{
                background: {CLR_SURFACE};
                color: {CLR_TEXT};
                border: 1.5px solid {CLR_BORDER};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
            }}
            QLineEdit:hover {{
                border-color: {CLR_BORDER_DARK};
            }}
            QLineEdit:focus {{
                border-color: {CLR_ACCENT};
            }}
            """)


class _AccentButton(QPushButton):
    """Amber dolgu, koyu yazı — Kaydet / Görsel Seç butonları için."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {CLR_ACCENT};
                color: #111111;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {CLR_ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background: {CLR_ACCENT_PRESSED};
            }}
            """)


class ProductDialog(QDialog):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Ürün Ekle")
        self.setFixedWidth(300)
        self.setStyleSheet(f"background: {CLR_BG};")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        layout.addWidget(_FieldLabel("Ürün Kodu"))
        self.code_input = _Input()
        layout.addWidget(self.code_input)

        layout.addSpacing(4)
        layout.addWidget(_FieldLabel("Ürün Adı"))
        self.name_input = _Input()
        layout.addWidget(self.name_input)

        layout.addSpacing(4)
        layout.addWidget(_FieldLabel("Ürün Linki"))
        self.product_url_input = _Input("https://...")
        layout.addWidget(self.product_url_input)

        self.image_path = ""

        layout.addSpacing(10)
        self.image_button = _AccentButton("Görsel Seç")
        layout.addWidget(self.image_button)

        self.image_label = QLabel("Dosya seçilmedi")
        self.image_label.setStyleSheet(
            f"color: {CLR_TEXT_MUTED}; font-size: 12px; background: transparent; padding: 2px 0;"
        )
        layout.addWidget(self.image_label)

        self.image_button.clicked.connect(self.select_image)

        layout.addSpacing(4)
        self.save_button = _AccentButton("Kaydet")
        layout.addWidget(self.save_button)

        self.save_button.clicked.connect(self.accept)

        self.setLayout(layout)

    def select_image(self):

        file_name, _ = QFileDialog.getOpenFileName(
            self, "Görsel Seç", "", "Images (*.png *.jpg *.jpeg)"
        )

        if file_name:

            self.image_path = file_name

            self.image_label.setText(file_name.split("/")[-1])

    def get_product_code(self):

        return self.code_input.text()

    def get_product_name(self):

        return self.name_input.text()

    def get_product_url(self):

        return self.product_url_input.text()
