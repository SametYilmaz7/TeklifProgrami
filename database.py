"""
database.py
~~~~~~~~~~~
Veritabanı erişim katmanı.

Tasarım kararları:
  - Product dataclass: tuple index yerine isimli alan erişimi
  - DatabaseError: hatalar sessizce yutulmaz, anlamlı mesajla yukarı taşınır
  - get_db_path(): DB, exe/script'in yanına yazılır — os.getcwd()'e değil
  - _connection(): bağlantı yönetimi tek noktada, tekrar yok
  - update_product: ürün düzenleme için hazır
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional

# ---------------------------------------------------------------------------
# DB yolu — exe yanına yazar, çalışma dizinine değil
# ---------------------------------------------------------------------------


def get_db_path() -> Path:
    """
    Veritabanı dosyasının yolunu döndürür.
    PyInstaller ile paketlendiğinde exe'nin yanına,
    geliştirme ortamında script'in yanına yazar.
    """
    return Path(__file__).resolve().parent / "teklif.db"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@dataclass
class Product:
    """
    Veritabanındaki bir ürünü temsil eder.
    Tuple index yerine isimli alanlara erişim sağlar.
    """

    id: int
    product_code: str
    name: str
    image_path: str
    product_url: str

    @classmethod
    def from_row(cls, row: tuple) -> "Product":
        """SQLite satırından Product nesnesi oluşturur."""
        return cls(
            id=row[0],
            product_code=row[1],
            name=row[2],
            image_path=row[3] or "",
            product_url=row[4] or "",
        )


# ---------------------------------------------------------------------------
# Hata sınıfları
# ---------------------------------------------------------------------------


class DatabaseError(Exception):
    """Veritabanı işlemlerinde oluşan hatalar için."""

    pass


class DuplicateProductError(DatabaseError):
    """Aynı ürün kodu zaten kayıtlı."""

    pass


# ---------------------------------------------------------------------------
# Bağlantı yönetimi
# ---------------------------------------------------------------------------


@contextmanager
def _connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Güvenli bağlantı context manager'ı.
    Başarılı işlemde commit, hata durumunda rollback yapar.
    """
    conn = sqlite3.connect(str(get_db_path()))
    try:
        yield conn
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if "UNIQUE constraint failed" in str(e):
            raise DuplicateProductError(
                "Bu ürün kodu zaten kayıtlı. Lütfen farklı bir kod giriniz."
            ) from e
        raise DatabaseError(f"Veri bütünlüğü hatası: {e}") from e
    except sqlite3.Error as e:
        conn.rollback()
        raise DatabaseError(f"Veritabanı hatası: {e}") from e
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def create_database() -> None:
    """
    Veritabanını ve tabloları oluşturur.
    Uygulama her başladığında çağrılır; tablo zaten varsa eksik/fazla alanlar düzeltilir.
    """
    with _connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                product_code   TEXT    NOT NULL UNIQUE,
                name           TEXT    NOT NULL,
                image_path     TEXT,
                product_url    TEXT
            )
        """)
        _ensure_products_schema(conn)


def _ensure_products_schema(conn: sqlite3.Connection) -> None:
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(products)").fetchall()
    }

    if "product_url" not in columns:
        conn.execute("ALTER TABLE products ADD COLUMN product_url TEXT")
        columns.add("product_url")

    if "technical_info" in columns or "price" in columns:
        _rebuild_products_schema(conn)


def _rebuild_products_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE products_new (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code   TEXT    NOT NULL UNIQUE,
            name           TEXT    NOT NULL,
            image_path     TEXT,
            product_url    TEXT
        )
    """)
    conn.execute("""
        INSERT INTO products_new (
            id, product_code, name, image_path, product_url
        )
        SELECT id, product_code, name, image_path, COALESCE(product_url, '')
        FROM products
    """)
    conn.execute("DROP TABLE products")
    conn.execute("ALTER TABLE products_new RENAME TO products")


_PRODUCT_COLUMNS = "id, product_code, name, image_path, product_url"


# ---------------------------------------------------------------------------
# CRUD işlemleri
# ---------------------------------------------------------------------------


def add_product(
    product_code: str,
    name: str,
    image_path: str,
    product_url: str = "",
) -> Product:
    """
    Yeni ürün ekler.
    Aynı product_code zaten varsa DuplicateProductError fırlatır.
    Eklenen ürünü Product nesnesi olarak döndürür.
    """
    with _connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO products (product_code, name, image_path, product_url)
            VALUES (?, ?, ?, ?)
            """,
            (product_code, name, image_path, product_url),
        )
        return Product(
            id=cursor.lastrowid,
            product_code=product_code,
            name=name,
            image_path=image_path or "",
            product_url=product_url or "",
        )


def update_product(
    product_id: int,
    product_code: str,
    name: str,
    image_path: str,
    product_url: str = "",
) -> None:
    """
    Mevcut ürünü günceller.
    Ürün bulunamazsa DatabaseError fırlatır.
    """
    with _connection() as conn:
        cursor = conn.execute(
            """
            UPDATE products
            SET product_code = ?,
                name         = ?,
                image_path   = ?,
                product_url  = ?
            WHERE id = ?
            """,
            (
                product_code,
                name,
                image_path,
                product_url,
                product_id,
            ),
        )
        if cursor.rowcount == 0:
            raise DatabaseError(f"Ürün bulunamadı (id={product_id})")


def delete_product(product_id: int) -> None:
    """
    Ürünü siler.
    Ürün bulunamazsa DatabaseError fırlatır.
    """
    with _connection() as conn:
        cursor = conn.execute(
            "DELETE FROM products WHERE id = ?",
            (product_id,),
        )
        if cursor.rowcount == 0:
            raise DatabaseError(f"Silinecek ürün bulunamadı (id={product_id})")


def get_products() -> list[Product]:
    """Tüm ürünleri ürün koduna göre sıralı döndürür."""
    with _connection() as conn:
        rows = conn.execute(
            f"SELECT {_PRODUCT_COLUMNS} FROM products ORDER BY product_code"
        ).fetchall()
        return [Product.from_row(tuple(row)) for row in rows]


def get_product_by_id(product_id: int) -> Optional[Product]:
    """ID ile ürün arar. Bulunamazsa None döner."""
    with _connection() as conn:
        row = conn.execute(
            f"SELECT {_PRODUCT_COLUMNS} FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
        return Product.from_row(tuple(row)) if row else None


def get_product_by_code(product_code: str) -> Optional[Product]:
    """Ürün kodu ile ürün arar. Bulunamazsa None döner."""
    with _connection() as conn:
        row = conn.execute(
            f"SELECT {_PRODUCT_COLUMNS} FROM products WHERE product_code = ?",
            (product_code,),
        ).fetchone()
        return Product.from_row(tuple(row)) if row else None


def search_products(search_text: str) -> list[Product]:
    """
    Ürün kodu veya adında arama yapar.
    Boş arama metni tüm ürünleri döndürür.
    """
    pattern = f"%{search_text}%"
    with _connection() as conn:
        rows = conn.execute(
            f"""
            SELECT {_PRODUCT_COLUMNS}
            FROM products
            WHERE product_code LIKE ?
               OR name         LIKE ?
            ORDER BY product_code
            """,
            (pattern, pattern),
        ).fetchall()
        return [Product.from_row(tuple(row)) for row in rows]
