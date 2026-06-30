"""
offer_service.py
~~~~~~~~~~~~~~~~
Teklif iş mantığı katmanı.

OfferWindow'dan tamamen bağımsızdır; PyQt6 import etmez.
Aynı mantık farklı bir UI (web, CLI, test) tarafından da kullanılabilir.

Sorumluluklar:
  - Teklif kalemlerini yönetmek (ekle, güncelle, sil)
  - Fiyat ve KDV hesaplamalarını yapmak
  - Duplicate kontrolü
  - PDF oluşturma isteğini pdf_generator'a iletmek
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from database import Product

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@dataclass
class OfferItem:
    """
    Teklife eklenmiş bir ürün kalemini temsil eder.
    Dict yerine dataclass: item["price"] yerine item.price — okunabilir ve tip güvenli.
    """

    product_code: str
    name: str
    quantity: int
    price: float
    image_path: str
    product_url: str
    unit: str = "AD"

    @property
    def total(self) -> float:
        return self.quantity * self.price

    def to_pdf_dict(self) -> dict:
        """pdf_generator'ın beklediği formata dönüştürür."""
        return {
            "product_code": self.product_code,
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "price": self.price,
            "total": self.total,
            "image_path": self.image_path,
            "product_url": self.product_url,
        }


# ---------------------------------------------------------------------------
# Hata sınıfı
# ---------------------------------------------------------------------------


class DuplicateItemError(Exception):
    """Aynı ürün teklif listesinde zaten var."""

    pass


# ---------------------------------------------------------------------------
# Servis
# ---------------------------------------------------------------------------


class OfferService:
    """
    Tek bir teklife ait iş mantığını yönetir.

    OfferWindow bu sınıfı oluşturur ve metodlarını çağırır.
    UI bileşenlerine (QWidget vb.) hiçbir bağımlılığı yoktur.
    """

    DEFAULT_QUANTITY = 1
    MIN_QUANTITY = 1
    MAX_QUANTITY = 10_000

    def __init__(self) -> None:
        self._items: list[OfferItem] = []

    # ------------------------------------------------------------------
    # Erişimciler

    @property
    def items(self) -> list[OfferItem]:
        """Teklif kalemlerinin kopyasını döndürür (dışarıdan değiştirilemez)."""
        return list(self._items)

    @property
    def subtotal(self) -> float:
        return sum(item.total for item in self._items)

    def grand_total(self, vat_rate: float) -> float:
        return self.subtotal * (1 + vat_rate)

    def vat_amount(self, vat_rate: float) -> float:
        return self.subtotal * vat_rate

    def is_empty(self) -> bool:
        return len(self._items) == 0

    # ------------------------------------------------------------------
    # Kalem yönetimi

    def add_product(self, product: Product, price: float) -> OfferItem:
        """
        Ürünü teklif listesine ekler.
        Aynı product_code zaten varsa DuplicateItemError fırlatır.
        Eklenen OfferItem'ı döndürür.
        """
        if self._find(product.product_code) is not None:
            raise DuplicateItemError(
                f'"{product.name}" zaten teklif listesinde bulunuyor.'
            )

        item = OfferItem(
            product_code=product.product_code,
            name=product.name,
            quantity=self.DEFAULT_QUANTITY,
            price=max(0.0, float(price)),
            image_path=product.image_path,
            product_url=product.product_url,
        )
        self._items.append(item)
        return item

    def update_quantity(self, product_code: str, quantity: int) -> None:
        """
        Kalemin miktarını günceller.
        Ürün listede yoksa sessizce geçer.
        """
        quantity = max(self.MIN_QUANTITY, min(self.MAX_QUANTITY, quantity))
        item = self._find(product_code)
        if item is not None:
            item.quantity = quantity

    def update_price(self, product_code: str, price: float) -> None:
        """
        Kalemin birim fiyatını günceller.
        Ürün listede yoksa sessizce geçer.
        """
        item = self._find(product_code)
        if item is not None:
            item.price = max(0.0, float(price))

    def remove(self, product_code: str) -> None:
        """Kalemi listeden çıkarır. Bulunamazsa sessizce geçer."""
        self._items = [i for i in self._items if i.product_code != product_code]

    def clear(self) -> None:
        """Tüm kalemleri temizler."""
        self._items.clear()

    # ------------------------------------------------------------------
    # PDF

    def build_pdf(
        self,
        customer_name: str,
        vat_rate: float,
        customer_address: str = "",
        validity_date: str = "",
        **kwargs,
    ) -> str:
        """
        PDF'i oluşturur ve dosya yolunu döndürür.
        pdf_generator.create_pdf() ile arayüz bu metod üzerinden geçer.
        Ek parametreler (notes, payment_type vb.) **kwargs ile iletilir.
        """
        from pdf_generator import create_pdf  # lazy import — PDF lazım olduğunda yükle

        return create_pdf(
            customer_name=customer_name,
            items=[item.to_pdf_dict() for item in self._items],
            total_price=self.subtotal,
            vat_rate=vat_rate,
            customer_address=customer_address,
            validity_date=validity_date,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Yardımcı

    def _find(self, product_code: str) -> Optional[OfferItem]:
        return next(
            (item for item in self._items if item.product_code == product_code),
            None,
        )
