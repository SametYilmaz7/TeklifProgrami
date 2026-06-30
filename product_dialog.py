from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
)


class ProductDialog(QDialog):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Ürün Ekle")
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Ürün Kodu"))
        self.code_input = QLineEdit()
        layout.addWidget(self.code_input)

        layout.addWidget(QLabel("Ürün Adı"))
        self.name_input = QLineEdit()
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("Ürün Linki"))
        self.product_url_input = QLineEdit()
        self.product_url_input.setPlaceholderText("https://...")
        layout.addWidget(self.product_url_input)

        self.image_path = ""

        self.image_button = QPushButton("Görsel Seç")
        layout.addWidget(self.image_button)

        self.image_label = QLabel("Dosya seçilmedi")
        layout.addWidget(self.image_label)

        self.image_button.clicked.connect(self.select_image)

        self.save_button = QPushButton("Kaydet")
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

