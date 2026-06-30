from __future__ import annotations
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas

BASE_DIR = Path(__file__).resolve().parent
TPL_COVER = BASE_DIR / "assets" / "cover_bg.png"
TPL_PRODUCTS = BASE_DIR / "assets" / "tpl_urunler.png"
TPL_PRODUCTS_NEXT = BASE_DIR / "assets" / "urunler_digersayfa.png"
TPL_TOTALS = BASE_DIR / "assets" / "toplam.png"
TPL_DETAILS = BASE_DIR / "assets" / "detaylar.png"

PW, PH = 595.28, 841.89

# Şablon (1024x1536) → PDF pt dönüşüm
RX = PW / 1024
RY = PH / 1536


def _pt(px_x, px_y):
    """Şablon piksel → PDF pt  (y ekseni tersine)"""
    return round(px_x * RX, 2), round(PH - px_y * RY, 2)


# ── Koordinatlar ────────────────────────────────────────────────────────────
# Sol blok
MUSTERI_PT = _pt(70, 255)  # Müşteri adı
ADRES_PT = _pt(70, 285)  # Adres başlangıcı
GIRIS_PT = _pt(72, 340)  # Giriş metni
GECERLI_PT = _pt(112, 392)  # Geçerlilik satırı

# Sağ blok — Tarih / Teklif No
TARIH_LBL_PT = _pt(670, 281)  # "Tarih" etiketi
TARIH_VAL_PT = _pt(780, 252)  # Tarih değeri
TEKLIF_LBL_PT = _pt(670, 320)  # "Teklif No" etiketi
TEKLIF_VAL_PT = _pt(780, 300)  # Teklif No değeri

# Tablo
TABLE_BAND_TOP = _pt(0, 492)[1]
TABLE_BAND_BOT = _pt(0, 492)[1]  # ürün satırı buradan başlar
NEXT_TABLE_BAND_BOT = _pt(0, 205)[1]  # devam sayfasında üst çizginin altı
ROW_MIN_H = 75.0  # resim sütunu (67pt) + padding'e göre belirlendi
FOOTER_Y = 25.0

# Toplam bloğu, "Örnek - Kopya.png" içindeki sağ alt konuma göre ayarlandı.
TOTAL_BLOCK_X = _pt(578, 970)[0] + 13
TOTAL_BLOCK_TOP_Y = _pt(578, 970)[1]
TOTAL_BLOCK_W = 236.0
TOTAL_BLOCK_GAP = 12.0

# Detaylar.png kendi piksel oranına göre konumlandırılır.
DETAILS_PAYMENT_VALUE_PX = (360, 315)

# ── Tablo sütun genişlikleri [pt] ───────────────────────────────────────────
# Sadece bu bölümü düzenleyerek sütun genişliklerini ayarlayabilirsiniz.

COL_RESIM = 67  # Resim
COL_URUN_KODU = 71.2  # Ürün Kodu
COL_URUN_ADI = 82.0  # Ürün Adı
COL_TEKNIK = 134.2  # Teknik Bilgi
COL_MIKTAR = 57.6  # Miktar
COL_BIRIM_FIYAT = 70  # Birim Fiyat (KDV Hariç)
COL_TUTAR = 73.1  # Tutar (KDV Hariç)

# Tablo sol başlangıcı — değiştirmeyin
_TABLE_LEFT = 20

# Sütun sol kenar x koordinatları — otomatik hesaplanır, değiştirmeyin
COL_X = [_TABLE_LEFT]
for _w in [
    COL_RESIM,
    COL_URUN_KODU,
    COL_URUN_ADI,
    COL_TEKNIK,
    COL_MIKTAR,
    COL_BIRIM_FIYAT,
    COL_TUTAR,
]:
    COL_X.append(round(COL_X[-1] + _w, 1))

# COL_X indeks haritası:
# [0] sol kenar   [1] Resim|Kod   [2] Kod|Ad   [3] Ad|Teknik
# [4] Teknik|Miktar   [5] Miktar|BirimFiyat   [6] Birim|Tutar   [7] sağ kenar

# Renkler
C_BLACK = colors.HexColor("#1A1A2E")
C_RED = colors.HexColor("#C0392B")
C_GRAY = colors.HexColor("#666666")
C_WHITE = colors.white
C_BORDER = colors.HexColor("#CCCCCC")
C_ALTROW = colors.HexColor("#F0F0F0")
C_LINK = colors.HexColor("#1F5FBF")
DETAIL_LINK_TEXT = "Ayrıntılı bilgi için tıklayınız"


# ── Font ────────────────────────────────────────────────────────────────────
def _reg_fonts():
    r = BASE_DIR / "assets" / "fonts" / "Inter-Regular.ttf"
    b = BASE_DIR / "assets" / "fonts" / "Inter-Bold.ttf"
    pdfmetrics.registerFont(TTFont("IR", str(r)))
    pdfmetrics.registerFont(TTFont("IB", str(b)))


def _sw(t, f, s):
    return pdfmetrics.stringWidth(t, f, s)


def _wrap(text, max_w, font, size):
    words = str(text).split()
    lines, cur = [], ""
    for w in words:
        c = (cur + " " + w).strip()
        if _sw(c, font, size) <= max_w:
            cur = c
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _fmt(v, cur="TL"):
    s = f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} {cur}"


def _safe(s):
    return re.sub(r'[<>:"/\\|?*]', "_", s)


def _normalize_url(url):
    url = str(url or "").strip()
    if not url:
        return ""
    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
        return "https://" + url
    return url


def _draw_detail_link(c, url, x, y, font, size):
    normalized_url = _normalize_url(url)
    if not normalized_url:
        return

    c.setFont(font, size)
    c.setFillColor(C_LINK)
    c.drawString(x, y, DETAIL_LINK_TEXT)

    text_w = _sw(DETAIL_LINK_TEXT, font, size)
    c.setStrokeColor(C_LINK)
    c.setLineWidth(0.35)
    c.line(x, y - 1.2, x + text_w, y - 1.2)
    c.linkURL(
        normalized_url,
        (x, y - 2, x + text_w, y + size + 2),
        relative=0,
        thickness=0,
        NewWindow=True,
    )


# ── Ürün satırı yüksekliği ──────────────────────────────────────────────────
def _row_h(item):
    pad_y = 7
    fs_name = 9
    fs_tech = 7.5

    # Ürün Adı yüksekliği
    name_w = COL_X[3] - COL_X[2] - 12
    name_lines = _wrap(str(item.get("name", "")), name_w, "IB", fs_name)
    h_name = pad_y + 7.5 + 4 + len(name_lines) * fs_name * 1.4 + pad_y

    # Teknik Bilgi yüksekliği
    if item.get("product_url"):
        h_tech = pad_y + fs_tech * 1.38 + pad_y
    else:
        h_tech = pad_y * 2

    return max(ROW_MIN_H, h_name, h_tech)


# ── Sayfa yazıcıları ────────────────────────────────────────────────────────
def _draw_header_data(c, name, address, offer_no, validity):
    today = datetime.now().strftime("%d.%m.%Y")
    valid = validity or (datetime.now() + timedelta(days=30)).strftime("%d.%m.%Y")

    c.setFont("IB", 11)
    c.setFillColor(C_BLACK)
    c.drawString(*MUSTERI_PT, name.upper())

    if address:
        c.setFont("IR", 8)
        c.setFillColor(C_BLACK)
        ax, ay = ADRES_PT
        max_w = COL_X[3] - ax - 10
        lines = _wrap(address, max_w, "IR", 8)
        for i, ln in enumerate(lines[:3]):
            c.drawString(ax, ay - i * 11, ln)

    gvx, gvy = GECERLI_PT
    c.setFont("IB", 8)
    c.setFillColor(C_RED)
    c.drawString(gvx, gvy, valid)

    c.setFont("IB", 9)
    c.setFillColor(C_BLACK)
    c.drawString(*TARIH_VAL_PT, today)
    c.drawString(*TEKLIF_VAL_PT, offer_no)


def _draw_product_row(c, item, y_top, row_h, idx):
    y_bot = y_top - row_h
    pad_x, pad_y = 6, 7

    # Arka plan
    bg = C_ALTROW if idx % 2 == 0 else C_WHITE
    c.setFillColor(bg)
    c.rect(COL_X[0], y_bot, COL_X[-1] - COL_X[0], row_h, fill=1, stroke=0)

    # Dış çerçeve
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(0.4)
    c.rect(COL_X[0], y_bot, COL_X[-1] - COL_X[0], row_h, fill=0, stroke=1)

    # Dikey sütun çizgileri
    for cx in COL_X[1:-1]:
        c.line(cx, y_top, cx, y_bot)

    # [0→1] Resim
    _draw_img(c, item.get("image_path"), COL_X[0], COL_X[1], y_bot, row_h)

    # [1] Ürün Kodu — bağımsız y konumu
    # URUN_KODU_OFFSET: y_top'tan kaç pt aşağıda — bu sayıyı değiştirerek taşı
    URUN_KODU_OFFSET = 35
    c.setFont("IB", 7.5)
    c.setFillColor(C_BLACK)
    c.drawString(
        COL_X[1] + pad_x, y_top - URUN_KODU_OFFSET, str(item.get("product_code", ""))
    )

    # [2→3] Ürün Adı — sabit, üstten pad_y mesafesinde (değişmez)
    name_w = COL_X[3] - COL_X[2] - pad_x * 2
    name_lines = _wrap(str(item.get("name", "")), name_w, "IB", 9)
    ty = y_top - pad_y - 9
    c.setFont("IB", 9)
    c.setFillColor(C_BLACK)
    for ln in name_lines:
        c.drawString(COL_X[2] + pad_x, ty, ln)
        ty -= 9 * 1.4

    # [3→4] Teknik Bilgi
    fs = 9
    ty = y_top - pad_y - fs - 20
    product_url = item.get("product_url", "")
    if product_url:
        _draw_detail_link(c, product_url, COL_X[3] + pad_x + 8, ty, "IR", fs)

    # [4→5] Miktar (ortalı)
    qty = f"{item.get('quantity', 1)} {item.get('unit', 'AD')}"
    cy = y_bot + row_h / 2 - 8 / 2 + 1
    c.setFont("IR", 8)
    c.setFillColor(C_BLACK)
    c.drawCentredString((COL_X[4] + COL_X[5]) / 2, cy, qty)

    # [5→6] Birim Fiyat (sağa)
    c.setFont("IR", 8)
    c.setFillColor(C_BLACK)
    c.drawRightString(COL_X[6] - pad_x, cy, _fmt(item.get("price", 0)))

    # [6→7] Tutar (sağa, bold)
    c.setFont("IB", 8)
    c.setFillColor(C_BLACK)
    c.drawRightString(COL_X[-1] - pad_x, cy, _fmt(item.get("total", 0)))


def _draw_img(c, path, x0, x1, y_bot, row_h):
    w = x1 - x0
    sz = min(w - 10, row_h - 10)  # sütun ve satır yüksekliğine göre dinamik
    ix = x0 + (w - sz) / 2
    iy = y_bot + (row_h - sz) / 2
    drawn = False
    if path:
        p = Path(path) if Path(path).is_absolute() else BASE_DIR / path
        if p.exists():
            try:
                c.drawImage(
                    ImageReader(str(p)),
                    ix,
                    iy,
                    sz,
                    sz,
                    preserveAspectRatio=True,
                    mask="auto",
                )
                drawn = True
            except Exception:
                pass
    if not drawn:
        c.setFillColor(colors.HexColor("#EEEEEE"))
        c.setStrokeColor(C_BORDER)
        c.setLineWidth(0.4)
        c.rect(ix, iy, sz, sz, fill=1, stroke=1)
        c.setFont("IR", 7)
        c.setFillColor(C_GRAY)
        c.drawCentredString(ix + sz / 2, iy + sz / 2 + 3, "RESİM")
        c.drawCentredString(ix + sz / 2, iy + sz / 2 - 6, "YOK")


def _draw_footer(c, page_no):
    c.setFont("IB", 7.5)
    c.setFillColor(C_BLACK)
    c.drawRightString(PW - 20, 14, f"Sayfa {page_no}")


def _total_block_h() -> float:
    if not TPL_TOTALS.exists():
        return 0.0

    img_w, img_h = ImageReader(str(TPL_TOTALS)).getSize()
    return TOTAL_BLOCK_W * img_h / img_w


def _draw_totals_block(c, top_y, subtotal, vat_rate, currency):
    if not TPL_TOTALS.exists():
        return

    block_h = _total_block_h()
    block_y = top_y - block_h
    c.drawImage(
        ImageReader(str(TPL_TOTALS)),
        TOTAL_BLOCK_X,
        block_y,
        TOTAL_BLOCK_W,
        block_h,
        preserveAspectRatio=True,
        mask="auto",
    )

    vat = subtotal * vat_rate
    grand_total = subtotal + vat
    value_x = TOTAL_BLOCK_X + TOTAL_BLOCK_W - 12
    row_h = block_h / 3
    value_ys = [
        block_y + row_h * 2 + row_h / 2 - 8,
        block_y + row_h + row_h / 2 + 2,
        block_y + row_h / 2 + 12,
    ]
    values = [
        (_fmt(subtotal, currency), C_BLACK),
        (_fmt(vat, currency), C_BLACK),
        (_fmt(grand_total, currency), C_WHITE),
    ]

    c.setFont("IB", 9)
    for (value, color), y in zip(values, value_ys):
        c.setFillColor(color)
        c.drawRightString(value_x, y, value)


def _details_pt(px_x, px_y):
    img_w, img_h = ImageReader(str(TPL_DETAILS)).getSize()
    return round(px_x * PW / img_w, 2), round(PH - px_y * PH / img_h, 2)


def _draw_details_page(c, payment_type):
    if not TPL_DETAILS.exists():
        return

    c.drawImage(
        ImageReader(str(TPL_DETAILS)),
        0,
        0,
        PW,
        PH,
        preserveAspectRatio=False,
        mask="auto",
    )

    value = str(payment_type or "").strip()
    if not value:
        return

    c.setFont("IB", 10)
    c.setFillColor(C_BLACK)
    c.drawString(*_details_pt(*DETAILS_PAYMENT_VALUE_PX), value)


# ── Ana fonksiyon ────────────────────────────────────────────────────────────
def create_pdf(
    customer_name: str,
    items: list[dict],
    total_price: float,
    vat_rate: Optional[float] = None,
    customer_address: str = "",
    validity_date: str = "",
    offer_no: Optional[str] = None,
    currency: str = "TL",
    **kwargs,
) -> str:
    _reg_fonts()

    out_dir = BASE_DIR / "pdfs"
    out_dir.mkdir(parents=True, exist_ok=True)

    name = (customer_name or "Müşteri").strip()
    o_no = offer_no or datetime.now().strftime("TKF-%Y%m%d-%H%M%S")
    payment_type = kwargs.get("payment_type", "")

    pdf_path = out_dir / f"{_safe(name)}_teklif.pdf"
    cv = rl_canvas.Canvas(str(pdf_path), pagesize=(PW, PH))
    cv.setTitle(name)

    if TPL_COVER.exists():
        cv.drawImage(
            ImageReader(str(TPL_COVER)),
            0,
            0,
            PW,
            PH,
            preserveAspectRatio=False,
            mask="auto",
        )
    cv.showPage()

    page_no = 2
    item_idx = 0
    product_page_idx = 0
    totals_h = _total_block_h()
    totals_space = totals_h + TOTAL_BLOCK_GAP

    while item_idx < len(items):
        is_first_product_page = product_page_idx == 0
        page_template = TPL_PRODUCTS if is_first_product_page else TPL_PRODUCTS_NEXT
        if page_template.exists():
            cv.drawImage(
                ImageReader(str(page_template)),
                0,
                0,
                PW,
                PH,
                preserveAspectRatio=False,
                mask="auto",
            )

        if is_first_product_page:
            _draw_header_data(cv, name, customer_address, o_no, validity_date)

        cursor_y = TABLE_BAND_BOT if is_first_product_page else NEXT_TABLE_BAND_BOT

        while item_idx < len(items):
            rh = _row_h(items[item_idx])
            reserve_for_totals = totals_space if item_idx == len(items) - 1 else 0
            if cursor_y - rh - reserve_for_totals < FOOTER_Y:
                break
            _draw_product_row(cv, items[item_idx], cursor_y, rh, item_idx)
            cursor_y -= rh
            item_idx += 1

        if item_idx >= len(items):
            vat = vat_rate if vat_rate is not None else 0.0
            totals_top_y = cursor_y - 18
            _draw_totals_block(cv, totals_top_y, total_price, vat, currency)

        _draw_footer(cv, page_no)
        page_no += 1
        product_page_idx += 1

        if item_idx < len(items):
            cv.showPage()

    if TPL_DETAILS.exists():
        cv.showPage()
        _draw_details_page(cv, payment_type)
        _draw_footer(cv, page_no)

    cv.save()
    return str(pdf_path)
