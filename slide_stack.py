"""
slide_stack.py
~~~~~~~~~~~~~~
QStackedWidget yerine kullanılan, sayfa geçişlerinde fade-in/fade-out
animasyonu uygulayan kapsayıcı widget.

Fade efekti QGraphicsOpacityEffect ile yapılır — bu Qt'nin kendi
compositing katmanında çalışır, manuel pixmap/pozisyon hesaplaması
gerektirmez ve çok daha hafif/akıcıdır.

Kullanım:
    stack = SlideStackedWidget()
    stack.addWidget(page1)
    stack.addWidget(page2)
    stack.slide_to(1)   # yeni sayfaya fade ile geç
    stack.slide_to(0)   # geri dön, fade ile

Business logic içermez — sadece görsel geçiş efekti sağlar.
"""

from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, pyqtSignal
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QWidget


class SlideStackedWidget(QWidget):
    """
    Sayfalar arası fade-in / fade-out animasyonu yapan kapsayıcı.
    "direction" parametresi geriye dönük uyumluluk için kabul edilir
    ama artık görsel bir etkisi yoktur (fade yönsüzdür).
    """

    transition_finished = pyqtSignal(int)

    def __init__(self, parent=None, duration: int = 260):
        super().__init__(parent)
        self._pages: list[QWidget] = []
        self._current_index = -1
        self._duration = duration
        self._animating = False
        self._anim_out: QPropertyAnimation | None = None
        self._anim_in: QPropertyAnimation | None = None

    # ── Sayfa yönetimi ────────────────────────────────────────────────────

    def addWidget(self, widget: QWidget) -> int:
        widget.setParent(self)
        if self._pages:
            widget.hide()
        else:
            widget.show()
            self._current_index = 0
        widget.move(0, 0)
        self._pages.append(widget)
        self._resize_current()
        return len(self._pages) - 1

    def currentIndex(self) -> int:
        return self._current_index

    def setCurrentIndex(self, index: int) -> None:
        """Animasyonsuz anlık geçiş (ilk açılış için)."""
        if not (0 <= index < len(self._pages)):
            return
        for i, page in enumerate(self._pages):
            page.move(0, 0)
            page.setVisible(i == index)
            page.setGraphicsEffect(None)
        self._current_index = index
        self._resize_current()

    def widget(self, index: int) -> QWidget | None:
        if 0 <= index < len(self._pages):
            return self._pages[index]
        return None

    # ── Fade animasyonu ─────────────────────────────────────────────────────

    def slide_to(self, index: int, direction: str = "right") -> None:
        """
        Mevcut sayfadan hedef sayfaya fade-out / fade-in animasyonuyla geçer.
        'direction' parametresi API uyumluluğu için tutulur, kullanılmaz.
        """
        if self._animating:
            return
        if not (0 <= index < len(self._pages)) or index == self._current_index:
            return

        old_widget = self._pages[self._current_index]
        new_widget = self._pages[index]

        w, h = self.width(), self.height()
        if w > 0 and h > 0:
            new_widget.setMinimumSize(w, h)
            new_widget.setMaximumSize(w, h)
            old_widget.setMinimumSize(w, h)
            old_widget.setMaximumSize(w, h)
            new_widget.resize(w, h)
            old_widget.resize(w, h)

        new_widget.move(0, 0)
        old_widget.move(0, 0)

        self._animating = True

        # ── Eski sayfa: fade-out ──────────────────────────────────────────
        old_effect = QGraphicsOpacityEffect(old_widget)
        old_widget.setGraphicsEffect(old_effect)
        old_effect.setOpacity(1.0)

        anim_out = QPropertyAnimation(old_effect, b"opacity", self)
        anim_out.setDuration(self._duration)
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.0)
        anim_out.setEasingCurve(QEasingCurve.Type.OutCubic)

        # ── Yeni sayfa: fade-in (eski biraz solduktan sonra başlar) ───────
        new_effect = QGraphicsOpacityEffect(new_widget)
        new_widget.setGraphicsEffect(new_effect)
        new_effect.setOpacity(0.0)
        new_widget.show()
        new_widget.raise_()

        anim_in = QPropertyAnimation(new_effect, b"opacity", self)
        anim_in.setDuration(self._duration)
        anim_in.setStartValue(0.0)
        anim_in.setEndValue(1.0)
        anim_in.setEasingCurve(QEasingCurve.Type.InCubic)

        def _on_finished():
            old_widget.hide()
            old_widget.setGraphicsEffect(None)
            new_widget.setGraphicsEffect(None)
            self._current_index = index
            self._animating = False
            self.transition_finished.emit(index)

        # Her iki animasyon paralel başlar; bitiş new fade tamamlandığında sayılır
        anim_in.finished.connect(_on_finished)

        self._anim_out = anim_out
        self._anim_in = new_in_keep = anim_in  # referansı tut

        anim_out.start()
        anim_in.start()

    # ── Boyutlandırma ──────────────────────────────────────────────────────

    def _resize_current(self) -> None:
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        for page in self._pages:
            page.setMinimumSize(w, h)
            page.setMaximumSize(w, h)
            page.resize(w, h)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._resize_current()
