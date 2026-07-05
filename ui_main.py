import os
from datetime import datetime
from functools import partial

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLineEdit, QTextEdit, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QComboBox, QCheckBox, QSplitter
)

from PIL import Image

import database


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Генератор цитат")
        self.resize(1000, 700)
        self.setMinimumSize(800, 500)

        self.db = database.DatabaseManager()
        self.current_image_path = ""

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        filter_layout = QHBoxLayout()
        self.cmb_category_filter = QComboBox()
        self.cmb_category_filter.addItem("Все")
        self.chk_fav_filter = QCheckBox("Только избранные")
        filter_layout.addWidget(QLabel("Категория:"))
        filter_layout.addWidget(self.cmb_category_filter)
        filter_layout.addWidget(self.chk_fav_filter)
        filter_layout.addStretch()
        left_layout.addLayout(filter_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Текст", "Автор", "Категория", "Избранное", "Дата"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setColumnHidden(0, True)  # скрываем ID
        left_layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Добавить")
        self.btn_edit = QPushButton("Изменить")
        self.btn_delete = QPushButton("Удалить")
        self.btn_refresh = QPushButton("Обновить")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_refresh)
        left_layout.addLayout(btn_layout)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        self.le_author = QLineEdit()
        self.le_category = QLineEdit()
        self.le_category.setPlaceholderText("Например: Мотивация")
        self.te_text = QTextEdit()
        self.te_text.setPlaceholderText("Введите текст цитаты...")
        self.te_text.setMaximumHeight(150)
        self.chk_fav = QCheckBox("Избранное")
        self.lbl_date = QLabel("Дата: (будет установлена автоматически)")

        form_layout.addRow("Текст:", self.te_text)
        form_layout.addRow("Автор:", self.le_author)
        form_layout.addRow("Категория:", self.le_category)
        form_layout.addRow(self.chk_fav)
        form_layout.addRow(self.lbl_date)

        right_layout.addWidget(form_widget)

        self.lbl_image = QLabel("Портрет автора / обложка")
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.lbl_image.setMinimumHeight(200)
        self.lbl_image.setStyleSheet("background-color: #f0f0f0; border: 2px dashed #aaa; border-radius: 8px;")
        right_layout.addWidget(self.lbl_image)

        self.btn_load_img = QPushButton("Загрузить изображение")
        right_layout.addWidget(self.btn_load_img)

        self.btn_random = QPushButton("Случайная цитата")
        right_layout.addWidget(self.btn_random)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([550, 350])
        main_layout.addWidget(splitter)

        self._bind_signals()
        self._refresh_categories()
        self._refresh_table()

    def _bind_signals(self):
        self.btn_add.clicked.connect(self._on_add)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_refresh.clicked.connect(self._refresh_table)
        self.btn_load_img.clicked.connect(self._on_load_image)
        self.btn_random.clicked.connect(self._on_random)
        self.table.itemSelectionChanged.connect(self._on_select_row)
        self.cmb_category_filter.currentTextChanged.connect(self._on_filter_changed)
        self.chk_fav_filter.stateChanged.connect(self._on_filter_changed)

    def _refresh_categories(self):
        current = self.cmb_category_filter.currentText()
        self.cmb_category_filter.clear()
        self.cmb_category_filter.addItem("Все")
        categories = self.db.get_categories()
        self.cmb_category_filter.addItems(categories)
        idx = self.cmb_category_filter.findText(current)
        if idx >= 0:
            self.cmb_category_filter.setCurrentIndex(idx)

    def _refresh_table(self):
        category = self.cmb_category_filter.currentText()
        fav_only = self.chk_fav_filter.isChecked()
        records = self.db.get_all(category=(category if category != "Все" else None), fav_only=fav_only)
        self.table.setRowCount(0)
        for i, rec in enumerate(records):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(rec["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(rec["text"][:50] + ("..." if len(rec["text"]) > 50 else "")))
            self.table.setItem(i, 2, QTableWidgetItem(rec["author"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(rec["category"] or ""))
            self.table.setItem(i, 4, QTableWidgetItem("★" if rec["is_fav"] else ""))
            self.table.setItem(i, 5, QTableWidgetItem(rec["date"] or ""))
        self._refresh_categories()

    def _on_filter_changed(self):
        self._refresh_table()

    def _on_select_row(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            self._clear_fields()
            return
        row = selected[0].row()
        item_id = int(self.table.item(row, 0).text())

        import sqlite3
        conn = sqlite3.connect(database.DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT text, author, category, is_fav, image_path FROM quotes WHERE id=?", (item_id,))
        rec = cur.fetchone()
        conn.close()

        if rec:
            self.te_text.setText(rec["text"])
            self.le_author.setText(rec["author"] or "")
            self.le_category.setText(rec["category"] or "")
            self.chk_fav.setChecked(bool(rec["is_fav"]))
            self.current_image_path = rec["image_path"] or ""
            if self.current_image_path and os.path.exists(self.current_image_path):
                self._show_image(self.current_image_path)
            else:
                self.lbl_image.setText("Портрет автора / обложка")
                self.lbl_image.setStyleSheet("background-color: #f0f0f0; border: 2px dashed #aaa; border-radius: 8px;")
            self.lbl_date.setText("Дата: (будет обновлена при сохранении)")

    def _on_add(self):
        text = self.te_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Ошибка", "Введите текст цитаты.")
            return
        data = {
            "text": text,
            "author": self.le_author.text().strip(),
            "category": self.le_category.text().strip(),
            "is_fav": 1 if self.chk_fav.isChecked() else 0,
            "date": datetime.now().isoformat(),
            "image_path": self.current_image_path
        }
        self.db.insert(data)
        self._refresh_table()
        self._clear_fields()
        QMessageBox.information(self, "Успех", "Цитата добавлена.")

    def _on_edit(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выберите цитату для редактирования.")
            return
        row = selected[0].row()
        item_id = int(self.table.item(row, 0).text())

        text = self.te_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Ошибка", "Введите текст цитаты.")
            return
        data = {
            "id": item_id,
            "text": text,
            "author": self.le_author.text().strip(),
            "category": self.le_category.text().strip(),
            "is_fav": 1 if self.chk_fav.isChecked() else 0,
            "date": datetime.now().isoformat(),
            "image_path": self.current_image_path
        }
        self.db.update(data)
        self._refresh_table()
        self._clear_fields()
        QMessageBox.information(self, "Успех", "Цитата обновлена.")

    def _on_delete(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выберите цитату для удаления.")
            return
        reply = QMessageBox.question(self, "Подтверждение", "Удалить выбранную цитату?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            row = selected[0].row()
            item_id = int(self.table.item(row, 0).text())
            self.db.delete(item_id)
            self._refresh_table()
            self._clear_fields()

    def _on_load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "",
                                              "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            self.current_image_path = path
            self._show_image(path)

    def _show_image(self, path):
        try:
            img = Image.open(path).convert("RGBA")
            img.thumbnail((260, 260), Image.LANCZOS)
            qt_img = QImage(img.tobytes(), img.width, img.height, QImage.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qt_img)
            self.lbl_image.setPixmap(pixmap)
            self.lbl_image.setScaledContents(False)
            self.lbl_image.setStyleSheet("background-color: transparent; border: none;")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить изображение:\n{e}")

    def _on_random(self):
        records = self.db.get_all()
        if not records:
            QMessageBox.information(self, "Нет цитат", "Добавьте хотя бы одну цитату.")
            return
        import random
        rec = random.choice(records)
        for row in range(self.table.rowCount()):
            if int(self.table.item(row, 0).text()) == rec["id"]:
                self.table.selectRow(row)
                self._on_select_row()
                break

    def _clear_fields(self):
        self.te_text.clear()
        self.le_author.clear()
        self.le_category.clear()
        self.chk_fav.setChecked(False)
        self.current_image_path = ""
        self.lbl_image.setText("Портрет автора / обложка")
        self.lbl_image.setStyleSheet("background-color: #f0f0f0; border: 2px dashed #aaa; border-radius: 8px;")
        self.lbl_date.setText("Дата: (будет установлена автоматически)")

    def closeEvent(self, event):
        reply = QMessageBox.question(self, "Выход", "Сохранить изменения перед выходом?",
                                     QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if reply == QMessageBox.Yes:
            self.db.close()
            event.accept()
        elif reply == QMessageBox.No:
            self.db.close()
            event.accept()
        else:
            event.ignore()