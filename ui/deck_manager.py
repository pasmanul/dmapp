import os
import uuid

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from models.card import Card
from models.deck import Deck

DECKS_DIR = "data/decks"
THUMB_W, THUMB_H = 52, 73


class DeckManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("デッキ管理")
        self.resize(720, 520)
        self.current_deck: Deck | None = None
        self.selected_card: Card | None = None
        self._img_path: str = ""
        self._setup_ui()
        self._load_deck_list()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        root = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---- Left: deck list ----
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.addWidget(QLabel("デッキ一覧"))

        self.deck_list = QListWidget()
        self.deck_list.currentTextChanged.connect(self._on_deck_selected)
        ll.addWidget(self.deck_list)

        btn_row = QHBoxLayout()
        new_btn = QPushButton("新規作成")
        new_btn.clicked.connect(self._new_deck)
        del_btn = QPushButton("削除")
        del_btn.clicked.connect(self._delete_deck)
        btn_row.addWidget(new_btn)
        btn_row.addWidget(del_btn)
        ll.addLayout(btn_row)
        splitter.addWidget(left)

        # ---- Right: editor ----
        right = QWidget()
        rl = QVBoxLayout(right)

        # Deck name row
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("デッキ名:"))
        self.deck_name_edit = QLineEdit()
        self.deck_name_edit.textChanged.connect(self._on_deck_name_changed)
        name_row.addWidget(self.deck_name_edit)
        self.count_label = QLabel("0 / 40")
        name_row.addWidget(self.count_label)
        rl.addLayout(name_row)

        rl.addWidget(QLabel("カード一覧"))
        self.card_list = QListWidget()
        self.card_list.currentRowChanged.connect(self._on_card_row_changed)
        rl.addWidget(self.card_list)

        # Card editor
        editor = QWidget()
        el = QVBoxLayout(editor)
        el.setContentsMargins(0, 0, 0, 0)

        # Image row
        img_row = QHBoxLayout()
        self.img_label = QLabel()
        self.img_label.setFixedSize(THUMB_W, THUMB_H)
        self.img_label.setStyleSheet("border: 1px solid #888;")
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_row.addWidget(self.img_label)

        img_right = QVBoxLayout()
        self.img_path_label = QLabel("画像未選択")
        self.img_path_label.setWordWrap(True)
        img_right.addWidget(self.img_path_label)
        sel_btn = QPushButton("画像を選択…")
        sel_btn.clicked.connect(self._select_image)
        img_right.addWidget(sel_btn)
        img_row.addLayout(img_right)
        el.addLayout(img_row)

        # Name
        cn_row = QHBoxLayout()
        cn_row.addWidget(QLabel("カード名:"))
        self.card_name_edit = QLineEdit()
        cn_row.addWidget(self.card_name_edit)
        el.addLayout(cn_row)

        # Count
        cc_row = QHBoxLayout()
        cc_row.addWidget(QLabel("枚数:"))
        self.card_count_spin = QSpinBox()
        self.card_count_spin.setRange(1, 40)
        cc_row.addWidget(self.card_count_spin)
        cc_row.addStretch()
        el.addLayout(cc_row)

        # Card buttons
        cb_row = QHBoxLayout()
        add_btn = QPushButton("カードを追加")
        add_btn.clicked.connect(self._add_card)
        upd_btn = QPushButton("更新")
        upd_btn.clicked.connect(self._update_card)
        del_card_btn = QPushButton("削除")
        del_card_btn.clicked.connect(self._delete_card)
        cb_row.addWidget(add_btn)
        cb_row.addWidget(upd_btn)
        cb_row.addWidget(del_card_btn)
        el.addLayout(cb_row)

        rl.addWidget(editor)

        save_btn = QPushButton("デッキを保存")
        save_btn.clicked.connect(self._save_deck)
        rl.addWidget(save_btn)

        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.accept)
        rl.addWidget(close_btn)

        splitter.addWidget(right)
        root.addWidget(splitter)

    # ------------------------------------------------------------------
    # Deck list operations
    # ------------------------------------------------------------------

    def _load_deck_list(self):
        self.deck_list.clear()
        os.makedirs(DECKS_DIR, exist_ok=True)
        for f in sorted(os.listdir(DECKS_DIR)):
            if f.endswith(".json"):
                self.deck_list.addItem(f[:-5])

    def _on_deck_selected(self, name: str):
        if not name:
            return
        path = os.path.join(DECKS_DIR, f"{name}.json")
        try:
            self.current_deck = Deck.load(path)
            self.deck_name_edit.setText(self.current_deck.name)
            self._refresh_card_list()
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"読み込み失敗: {e}")

    def _new_deck(self):
        self.current_deck = Deck()
        self.deck_name_edit.setText(self.current_deck.name)
        self._refresh_card_list()

    def _delete_deck(self):
        item = self.deck_list.currentItem()
        if not item:
            return
        name = item.text()
        if QMessageBox.question(self, "確認", f"「{name}」を削除しますか？") != QMessageBox.StandardButton.Yes:
            return
        path = os.path.join(DECKS_DIR, f"{name}.json")
        if os.path.exists(path):
            os.remove(path)
        self.current_deck = None
        self._load_deck_list()

    def _on_deck_name_changed(self, text: str):
        if self.current_deck:
            self.current_deck.name = text

    # ------------------------------------------------------------------
    # Card list operations
    # ------------------------------------------------------------------

    def _refresh_card_list(self):
        self.card_list.clear()
        if not self.current_deck:
            return
        for c in self.current_deck.cards:
            self.card_list.addItem(f"{c.name}  ×{c.count}")
        total = self.current_deck.total_count
        self.count_label.setText(f"{total} / 40")

    def _on_card_row_changed(self, row: int):
        if not self.current_deck or row < 0 or row >= len(self.current_deck.cards):
            return
        card = self.current_deck.cards[row]
        self.selected_card = card
        self.card_name_edit.setText(card.name)
        self.card_count_spin.setValue(card.count)
        self._img_path = card.image_path
        self.img_path_label.setText(os.path.basename(card.image_path))
        self._show_thumb(card.image_path)

    def _select_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "カード画像を選択", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif)"
        )
        if path:
            self._img_path = path
            self.img_path_label.setText(os.path.basename(path))
            self._show_thumb(path)

    def _show_thumb(self, path: str):
        pix = QPixmap(path)
        if not pix.isNull():
            pix = pix.scaled(THUMB_W, THUMB_H,
                              Qt.AspectRatioMode.IgnoreAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
            self.img_label.setPixmap(pix)
        else:
            self.img_label.clear()

    def _add_card(self):
        if not self.current_deck:
            QMessageBox.warning(self, "エラー", "先にデッキを作成してください")
            return
        name = self.card_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "エラー", "カード名を入力してください")
            return
        if not self._img_path:
            QMessageBox.warning(self, "エラー", "画像を選択してください")
            return
        count = self.card_count_spin.value()
        if self.current_deck.total_count + count > Deck.MAX_SIZE:
            remaining = Deck.MAX_SIZE - self.current_deck.total_count
            QMessageBox.warning(self, "エラー", f"枚数上限を超えます（残り {remaining} 枚）")
            return
        self.current_deck.cards.append(Card(name=name, image_path=self._img_path, count=count))
        self._refresh_card_list()

    def _update_card(self):
        if not self.selected_card:
            return
        new_count = self.card_count_spin.value()
        diff = new_count - self.selected_card.count
        if self.current_deck and self.current_deck.total_count + diff > Deck.MAX_SIZE:
            QMessageBox.warning(self, "エラー", "40枚を超えます")
            return
        self.selected_card.name = self.card_name_edit.text().strip()
        self.selected_card.count = new_count
        if self._img_path:
            self.selected_card.image_path = self._img_path
        self._refresh_card_list()

    def _delete_card(self):
        if not self.selected_card or not self.current_deck:
            return
        self.current_deck.cards = [c for c in self.current_deck.cards if c.id != self.selected_card.id]
        self.selected_card = None
        self._refresh_card_list()

    def _save_deck(self):
        if not self.current_deck:
            return
        name = self.current_deck.name.strip()
        if not name:
            QMessageBox.warning(self, "エラー", "デッキ名を入力してください")
            return
        path = os.path.join(DECKS_DIR, f"{name}.json")
        try:
            self.current_deck.save(path)
            self._load_deck_list()
            QMessageBox.information(self, "保存完了", f"「{name}」を保存しました")
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"保存失敗: {e}")
