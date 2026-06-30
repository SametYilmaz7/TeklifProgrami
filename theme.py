"""
theme.py
~~~~~~~~
Merkezi QSS tema — dark mode, amber accent.
Tüm pencereler bu modülden stil alır. Renk değiştirmek için sadece bu dosya düzenlenir.
"""

# ── Renk sistemi ────────────────────────────────────────────────────────────
# Zemin katmanları
CLR_BG = "#0F1115"  # en derin arka plan
CLR_SURFACE = "#1A1D24"  # kart / panel
CLR_HOVER = "#242933"  # hover yüzeyi
CLR_HOVER2 = "#2C3240"  # daha belirgin hover

# Kenarlık
CLR_BORDER = "#2E3440"
CLR_BORDER_DARK = "#3D4455"

# Metin
CLR_TEXT = "#F5F5F5"
CLR_TEXT_MUTED = "#A7B0BE"
CLR_TEXT_DIM = "#5C6478"

# Vurgu — Primary Accent (amber)
CLR_ACCENT = "#F8B458"
CLR_ACCENT_HOVER = "#E3A653"
CLR_ACCENT_PRESSED = "#CA954D"
CLR_ACCENT_SOFT = "#2A2214"  # çok hafif amber tint (seçim bg)
CLR_ACCENT_GLOW = "#F8B45820"  # şeffaf glow

# Semantik renkler (değişmez)
CLR_DANGER = "#E05252"
CLR_DANGER_BG = "#2A1515"
CLR_SUCCESS = "#4CAF7D"
CLR_WARNING = "#E8A030"

# Sabitler
CLR_WHITE = "#FFFFFF"
RADIUS = "8px"
FONT = "Inter, Segoe UI, Arial, sans-serif"

# ── Global QSS ──────────────────────────────────────────────────────────────
GLOBAL_QSS = f"""
/* ════════════════════════════════════════════
   GLOBAL
════════════════════════════════════════════ */
QWidget {{
    font-family: {FONT};
    font-size: 13px;
    color: {CLR_TEXT};
    background-color: {CLR_BG};
}}
QDialog, QMessageBox {{
    background-color: {CLR_SURFACE};
}}

/* ════════════════════════════════════════════
   TYPOGRAPHY
════════════════════════════════════════════ */
QLabel {{
    background: transparent;
    color: {CLR_TEXT_MUTED};
    font-size: 13px;
}}
QLabel[class="title"] {{
    color: {CLR_TEXT};
    font-size: 18px;
    font-weight: 700;
}}
QLabel[class="section-title"] {{
    color: {CLR_TEXT_DIM};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}
QLabel[class="muted"] {{
    color: {CLR_TEXT_MUTED};
    font-size: 12px;
}}
QLabel[class="accent"] {{
    color: {CLR_ACCENT};
    font-weight: 600;
}}

/* ════════════════════════════════════════════
   INPUT ALANLARI
════════════════════════════════════════════ */
QLineEdit, QTextEdit, QDateEdit, QSpinBox {{
    background: {CLR_SURFACE};
    border: 1.5px solid {CLR_BORDER};
    border-radius: {RADIUS};
    padding: 8px 12px;
    font-size: 13px;
    color: {CLR_TEXT};
    selection-background-color: {CLR_ACCENT};
    selection-color: #111111;
}}
QLineEdit:hover, QTextEdit:hover, QDateEdit:hover {{
    border-color: {CLR_BORDER_DARK};
    background: {CLR_HOVER};
}}
QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QSpinBox:focus {{
    border-color: {CLR_ACCENT};
    background: {CLR_SURFACE};
    outline: none;
}}
QLineEdit[readOnly="true"], QLineEdit[readOnly="true"]:hover {{
    background: {CLR_BG};
    color: {CLR_TEXT_MUTED};
    border-color: {CLR_BORDER};
}}
QLineEdit::placeholder, QTextEdit::placeholder {{
    color: {CLR_TEXT_DIM};
}}

/* SpinBox */
QSpinBox {{
    padding: 5px 8px;
    min-width: 56px;
}}
QSpinBox:hover {{
    border-color: {CLR_BORDER_DARK};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 0; border: none; background: transparent;
}}

/* DateEdit */
QDateEdit::drop-down {{
    border: none; width: 28px;
}}
QDateEdit::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {CLR_TEXT_MUTED};
    margin-right: 8px;
}}

/* ════════════════════════════════════════════
   COMBOBOX
════════════════════════════════════════════ */
QComboBox {{
    background: {CLR_SURFACE};
    border: 1.5px solid {CLR_BORDER};
    border-radius: {RADIUS};
    padding: 7px 36px 7px 12px;
    font-size: 13px;
    color: {CLR_TEXT};
    min-width: 140px;
}}
QComboBox:hover {{
    border-color: {CLR_BORDER_DARK};
    background: {CLR_HOVER};
}}
QComboBox:focus {{
    border-color: {CLR_ACCENT};
}}
QComboBox::drop-down {{
    border: none; width: 32px;
}}
QComboBox::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {CLR_TEXT_MUTED};
    margin-right: 10px;
}}
QComboBox QAbstractItemView {{
    background: {CLR_SURFACE};
    border: 1.5px solid {CLR_BORDER};
    border-radius: {RADIUS};
    padding: 4px;
    outline: none;
    selection-background-color: {CLR_ACCENT_SOFT};
    selection-color: {CLR_ACCENT};
}}
QComboBox QAbstractItemView::item {{
    padding: 8px 12px;
    color: {CLR_TEXT};
    border-radius: 6px;
    min-height: 32px;
}}
QComboBox QAbstractItemView::item:hover {{
    background: {CLR_HOVER};
}}

/* ════════════════════════════════════════════
   BUTONLAR
════════════════════════════════════════════ */

/* Primary — amber */
QPushButton {{
    background: {CLR_ACCENT};
    color: #111111;
    border: none;
    border-radius: {RADIUS};
    padding: 9px 20px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.1px;
}}
QPushButton:hover {{
    background: {CLR_ACCENT_HOVER};
}}
QPushButton:pressed {{
    background: {CLR_ACCENT_PRESSED};
}}
QPushButton:disabled {{
    background: {CLR_HOVER};
    color: {CLR_TEXT_DIM};
}}

/* Secondary — outlined */
QPushButton[class="secondary"] {{
    background: {CLR_SURFACE};
    color: {CLR_TEXT};
    border: 1.5px solid {CLR_BORDER};
    font-weight: 500;
}}
QPushButton[class="secondary"]:hover {{
    background: {CLR_HOVER};
    border-color: {CLR_BORDER_DARK};
}}
QPushButton[class="secondary"]:pressed {{
    background: {CLR_HOVER2};
}}

/* Dark — koyu surface */
QPushButton[class="dark"] {{
    background: {CLR_SURFACE};
    color: {CLR_TEXT};
    border: 1.5px solid {CLR_BORDER};
    font-weight: 600;
}}
QPushButton[class="dark"]:hover {{
    background: {CLR_HOVER};
    border-color: {CLR_BORDER_DARK};
}}
QPushButton[class="dark"]:pressed {{
    background: {CLR_HOVER2};
}}

/* Black — (önceki "black" class, artık koyu surface olarak çalışır) */
QPushButton[class="black"] {{
    background: {CLR_ACCENT};
    color: #111111;
    border: none;
    font-weight: 700;
}}
QPushButton[class="black"]:hover {{
    background: {CLR_ACCENT_HOVER};
}}
QPushButton[class="black"]:pressed {{
    background: {CLR_ACCENT_PRESSED};
}}

/* Ghost — şeffaf */
QPushButton[class="ghost"] {{
    background: transparent;
    color: {CLR_TEXT_MUTED};
    border: none;
    padding: 4px 8px;
    font-size: 14px;
    font-weight: 400;
}}
QPushButton[class="ghost"]:hover {{
    color: {CLR_ACCENT};
    background: {CLR_ACCENT_SOFT};
    border-radius: 6px;
}}
QPushButton[class="ghost"]:pressed {{
    background: {CLR_HOVER2};
}}

/* Danger — silme (amber tonlarda, kırmızı kullanılmıyor) */
QPushButton[class="danger"] {{
    background: transparent;
    color: {CLR_TEXT_DIM};
    border: none;
    padding: 4px 8px;
    font-size: 14px;
    font-weight: 400;
    border-radius: 6px;
}}
QPushButton[class="danger"]:hover {{
    color: {CLR_ACCENT};
    background: {CLR_ACCENT_SOFT};
}}
QPushButton[class="danger"]:pressed {{
    background: {CLR_HOVER2};
}}

/* ════════════════════════════════════════════
   CHECKBOX
════════════════════════════════════════════ */
QCheckBox {{
    font-size: 13px;
    color: {CLR_TEXT};
    spacing: 9px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 17px;
    height: 17px;
    border: 1.5px solid {CLR_BORDER_DARK};
    border-radius: 4px;
    background: {CLR_SURFACE};
}}
QCheckBox::indicator:hover {{
    border-color: {CLR_ACCENT};
    background: {CLR_ACCENT_SOFT};
}}
QCheckBox::indicator:checked {{
    background: {CLR_ACCENT};
    border-color: {CLR_ACCENT};
}}
QCheckBox::indicator:checked:hover {{
    background: {CLR_ACCENT_HOVER};
    border-color: {CLR_ACCENT_HOVER};
}}

/* ════════════════════════════════════════════
   TABLE
════════════════════════════════════════════ */
QTableWidget {{
    background: {CLR_BG};
    border: 1px solid {CLR_BORDER};
    border-radius: {RADIUS};
    gridline-color: transparent;
    outline: none;
    font-size: 13px;
    alternate-background-color: {CLR_SURFACE};
}}
QTableWidget::item {{
    padding: 0 12px;
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
QHeaderView::section:last {{
    border-right: none;
}}

/* ════════════════════════════════════════════
   LIST WIDGET
════════════════════════════════════════════ */
QListWidget {{
    background: {CLR_SURFACE};
    border: 1px solid {CLR_BORDER};
    border-radius: {RADIUS};
    outline: none;
    font-size: 13px;
}}
QListWidget::item {{
    padding: 10px 14px;
    border-bottom: 1px solid {CLR_BORDER};
    color: {CLR_TEXT};
    min-height: 36px;
}}
QListWidget::item:last {{
    border-bottom: none;
}}
QListWidget::item:hover {{
    background: {CLR_HOVER};
}}
QListWidget::item:selected {{
    background: {CLR_ACCENT_SOFT};
    color: {CLR_ACCENT};
    border-left: 3px solid {CLR_ACCENT};
}}

/* ════════════════════════════════════════════
   SCROLLBAR
════════════════════════════════════════════ */
QScrollBar:vertical {{
    background: transparent;
    width: 5px;
    margin: 0;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {CLR_BORDER_DARK};
    border-radius: 2px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {CLR_TEXT_DIM};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0; border: none;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 5px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {CLR_BORDER_DARK};
    border-radius: 2px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0; border: none;
}}

/* ════════════════════════════════════════════
   CALENDAR
════════════════════════════════════════════ */
QCalendarWidget {{
    background: {CLR_SURFACE};
    border: 1px solid {CLR_BORDER};
    border-radius: {RADIUS};
    color: {CLR_TEXT};
}}
QCalendarWidget QAbstractItemView {{
    background: {CLR_SURFACE};
    color: {CLR_TEXT};
    selection-background-color: {CLR_ACCENT};
    selection-color: #111111;
}}
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background: {CLR_HOVER};
    border-bottom: 1px solid {CLR_BORDER};
    border-radius: 8px 8px 0 0;
}}
QCalendarWidget QToolButton {{
    background: transparent;
    color: {CLR_TEXT};
    border: none;
    padding: 4px 8px;
    font-weight: 600;
}}
QCalendarWidget QToolButton:hover {{
    background: {CLR_HOVER2};
    border-radius: 6px;
}}

/* ════════════════════════════════════════════
   MESAJ & DİYALOG
════════════════════════════════════════════ */
QMessageBox {{
    background: {CLR_SURFACE};
}}
QMessageBox QLabel {{
    color: {CLR_TEXT};
    font-size: 13px;
    background: transparent;
}}
QMessageBox QPushButton {{
    background: {CLR_ACCENT};
    color: #111111;
    border: none;
    border-radius: 8px;
    min-width: 88px;
    min-height: 30px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 700;
}}
QMessageBox QPushButton:hover {{
    background: {CLR_ACCENT_HOVER};
}}
QMessageBox QPushButton:pressed {{
    background: {CLR_ACCENT_PRESSED};
}}

/* ════════════════════════════════════════════
   TOOLTIP
════════════════════════════════════════════ */
QToolTip {{
    background: {CLR_HOVER2};
    color: {CLR_TEXT};
    border: 1px solid {CLR_BORDER_DARK};
    border-radius: 6px;
    padding: 5px 9px;
    font-size: 12px;
}}

/* ════════════════════════════════════════════
   FRAME / DİVİDER
════════════════════════════════════════════ */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {{
    color: {CLR_BORDER};
    background: {CLR_BORDER};
    border: none;
    max-height: 1px;
}}
"""


def apply_theme(app) -> None:
    """QApplication'a global karanlık tema uygular."""
    app.setStyleSheet(GLOBAL_QSS)


def get_window_size(aspect: str = "landscape") -> tuple[int, int]:
    """
    Ekranın ~%25'ini kaplayan, her monitöre uyumlu pencere boyutu döndürür.
    Tüm ekranlar landscape boyutunu kullanır.
    """
    from PyQt6.QtWidgets import QApplication

    screen = QApplication.primaryScreen()
    if screen is None:
        return (1100, 680)

    sr = screen.availableGeometry()
    sw, sh = sr.width(), sr.height()

    w = int(sw * 0.55)
    h = int(sh * 0.55)
    w = max(960, min(w, 1400))
    h = max(600, min(h, 900))

    return w, h
