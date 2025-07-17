# -*- coding: utf-8 -*-
# 使用方法例： pixi run python marker.py

"""
# 説明
概要：
* 画像内の位置を指定してアノテーションを付けるためのGUIアプリケーション。（マーク付けまで行う）
動作概要：
* 画像をクリックすると、その位置にアノテーションが追加される。
* アノテーションはJSON形式で保存され、CSVファイルで処理済みの画像を管理する。
* 画像は指定されたディレクトリから読み込まれ、次の画像に進むボタンで切り替えられる。
* 画像のクリック位置は、元の画像サイズに基づいて計算され、座標と割合がアノテーションとして保存される。
* リストからのアノテーションの削除も可能。
"""

import random
import sys
import os
import json
import csv
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QListWidget, QListWidgetItem, QHBoxLayout, QMessageBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

from csv_tool import CSVTool  # CSVToolクラスをインポート


# --- 設定類（適宜変更のこと） ---
# 【要確認・適宜変更】イメージ格納ディレクトリの場所を指定（画像表示に必要・相対パスでも絶対パスでもいい）
IMAGE_DIR = "./images_test/"
# IMAGE_DIR = "./images_test"  # 相対パス・絶対パスともに使用可能
# 【変更不要】位置情報出力後のJSONファイル名（結果出力先・プログラム初回起動時には存在しなくていい）
JSON_FILE = "img_annotation.json"
# 【変更不要】進行状況を保存するためのファイル名（プログラム初回起動時には存在しなくていい）
CSV_FILE = "img_processing_list.csv"
# 【Optional】励ましメッセージCSV
ENCOURAGEMENT_FILE = "encouragement.csv"
# 【Optional】タイトルも表示するなら使用（ファイルがない場合は無視されるはず）
CSV_TITLE_FILE = "CSV_title_data.csv"
# --- ここまで設定類（適宜変更のこと） ---


class ImageAnnotator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Annotator (Step1: Positioning)")
        self.setGeometry(100, 100, 1000, 700)

        # self.image_label の上に追加する例
        self.title_label = QLabel("")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px;")

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.mousePressEvent = self.record_click

        # アノテーション表示用リスト
        self.annotation_list = QListWidget(self)

        # 次へボタン
        self.next_button = QPushButton("▶ 次へ")
        self.next_button.clicked.connect(self.next_image)
        self.next_button2 = QPushButton("▶ 次へ")
        self.next_button2.clicked.connect(self.next_image)
        self.next_button = self.set_button_style(self.next_button, fontsize="14px", bgcolor="#4CCFA0")
        self.next_butto2 = self.set_button_style(self.next_button2, fontsize="14px", bgcolor="#4CCFA0")


        # 新規追加: 進捗表示用ラベル（右下）
        self.progress_label = QLabel()
        self.progress_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # 新規追加: 励まし表示用ラベル（左下）
        self.encouragement_label = QLabel()
        self.encouragement_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # 右側のレイアウト
        self.right_layout = QVBoxLayout()
        self.right_layout.addWidget(self.next_button) # 右上にも右下にもほしい
        self.right_layout.addWidget(self.annotation_list)
        self.right_layout.addWidget(self.next_button2) # 右上にも右下にもほしい

        self.exit_button = QPushButton("終了")
        self.exit_button.clicked.connect(self.close_application)
        self.exit_button = self.set_button_style(self.exit_button, fontsize="14px", bgcolor="#c49306")
        self.right_layout.addWidget(self.exit_button)

        # 上側レイアウト：画像表示と右側レイアウトを横に配置
        top_layout = QHBoxLayout()
        top_left_layout = QVBoxLayout()
        top_left_layout.addWidget(self.title_label, 1)        # タイトルラベル追加
        top_left_layout.addWidget(self.image_label, 9)
        top_layout.addLayout(top_left_layout, 2)
        # top_layout.addWidget(self.image_label, 2)
        top_layout.addLayout(self.right_layout, 1)

        # 下側レイアウト：励ましと進捗表示を横に配置
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.encouragement_label, 1)
        bottom_layout.addWidget(self.progress_label, 1)

        # メインレイアウト：上側と下側を縦に配置
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

        self.image_files = []
        self.current_index = 0
        self.annotations = {}
        self.encouragement_messages = []  # 新規追加：励ましメッセージリスト
        self.title_map = self.load_title_map()

        self.load_state()
        self.load_encouragement_messages()  # CSVから励ましメッセージを読み込む
        self.show_image()

    def set_button_style(self, button, fontsize="14px", bgcolor="#4CAF50"):
        # ボタンのスタイルを設定
        button.setStyleSheet(f"""
            QPushButton {{
                font-size: {fontsize};
                background-color: {bgcolor}; /* 緑 */
                color: white;
                margin: 2px;
                padding: 6px 2px;
                border: none;
                border-radius: 5px;
            }}
        """)
        return button

    def load_state(self):
        # CSVファイルの読み込みまたは作成
        csvTool = CSVTool()
        if os.path.exists(CSV_FILE):
            encoding = csvTool.detect_file_encoding(CSV_FILE)
            with open(CSV_FILE, newline='', encoding=encoding) as f:
                reader = csv.DictReader(f)
                self.image_files = [row['filename'] for row in reader if row['processed'] == '0']
        else:
            files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
            files.sort()
            with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['filename', 'processed'])
                writer.writeheader()
                for file in files:
                    writer.writerow({'filename': file, 'processed': '0'})
            self.image_files = files

        # JSONファイルの読み込み
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                self.annotations = json.load(f)


    def load_encouragement_messages(self):
        # 新規追加: 励ましメッセージCSVの読み込み
        if os.path.exists(ENCOURAGEMENT_FILE):
            csvTool = CSVTool()
            encoding = csvTool.detect_file_encoding(ENCOURAGEMENT_FILE)
            with open(ENCOURAGEMENT_FILE, newline='', encoding=encoding) as f:
                reader = csv.DictReader(f)
                self.encouragement_messages = [row['message'] for row in reader if row.get('message')]
        else:
            self.encouragement_messages = ["ガンバレ！"]


    def load_title_map(self):
        title_map = {}
        if os.path.exists(CSV_TITLE_FILE):
            csvTool = CSVTool()
            # CSVファイルのエンコーディングを判定
            encoding = csvTool.detect_file_encoding(CSV_TITLE_FILE)
            with open(CSV_TITLE_FILE, newline='', encoding=encoding) as csvfile:
                reader = csv.DictReader(csvfile, skipinitialspace=True)
                print(f"CSV_TITLE_FILE exists: {CSV_TITLE_FILE}")
                print(reader)
                filename_col = None
                title_col = None

                for i, row in enumerate(reader):
                    if i == 0:
                        print(f"CSV_TITLE_FILE header: {row}")
                        filename_col = 'Filename' if 'Filename' in row else 'filename'
                        title_col = 'Title' if 'Title' in row else 'title'
                    filename = os.path.basename(row[filename_col]).strip()
                    title = row[title_col].strip()
                    title_map[filename] = title
        return title_map

    def update_progress(self):
        # 新規追加: 進捗ラベルの更新（CSVを再読み込み）
        if os.path.exists(CSV_FILE):
            with open(CSV_FILE, newline='', encoding='utf-8') as f:
                rows = list(csv.DictReader(f))
            total = len(rows)
            processed = sum(1 for row in rows if row['processed'] == '1')
            self.progress_label.setText(f"進捗: {str(int(processed + 1))}個目 / {total}個")
        else:
            self.progress_label.setText("進捗: 0 / 0")

    def update_encouragement(self):
        # 新規追加: 励ましメッセージの更新（ランダムに選択）
        if self.encouragement_messages:
            self.encouragement_label.setText(random.choice(self.encouragement_messages))
        else:
            self.encouragement_label.setText("")

    def close_application(self):
        self.close()

    def show_image(self):
        if self.current_index >= len(self.image_files):
            QMessageBox.information(self, "完了", "すべての画像を処理しました。")
            return

        image_path = os.path.join(IMAGE_DIR, self.image_files[self.current_index])
        pixmap = QPixmap(image_path)
        self.image_label.setPixmap(pixmap.scaled(
            self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.annotation_list.clear()

        filename = self.image_files[self.current_index]
        if filename in self.annotations:
            for ann in self.annotations[filename]:
                self.add_annotation_item(ann)


        # 🔽 タイトルの取得と表示．長過ぎたら切る．
        basename = os.path.basename(self.image_files[self.current_index])
        title = self.title_map.get(basename, "")
        # 最大表示幅（ピクセル単位、例：300ピクセル）
        max_width = 800  
        fm = self.title_label.fontMetrics()
        elided_text = fm.elidedText(title, Qt.ElideRight, max_width)
        self.title_label.setText(elided_text)
        # 新規追加: 新画像読み込み時に励ましメッセージ更新
        self.update_encouragement()
        # 進捗更新
        self.update_progress()

    def resizeEvent(self, event):
        self.show_image()

    def record_click(self, event):
        label_size = self.image_label.size()
        pixmap = self.image_label.pixmap()
        if pixmap is None:
            return

        pixmap_size = pixmap.size()
        label_w, label_h = label_size.width(), label_size.height()
        pixmap_w, pixmap_h = pixmap_size.width(), pixmap_size.height()

        # スケールを計算
        scale = min(label_w / pixmap_w, label_h / pixmap_h)
        display_w = pixmap_w * scale
        display_h = pixmap_h * scale

        # オフセット（中央配置における左上の余白）を計算
        offset_x = (label_w - display_w) / 2
        offset_y = (label_h - display_h) / 2

        # 実際に画像の上がクリックされたか確認
        click_x = event.pos().x()
        click_y = event.pos().y()

        if not (offset_x <= click_x <= offset_x + display_w and
                offset_y <= click_y <= offset_y + display_h):
            return  # 画像外の余白をクリックしているので無視

        # 画像内での相対座標（表示サイズ -> 元の画像サイズにスケーリング）
        relative_x = (click_x - offset_x) / display_w
        relative_y = (click_y - offset_y) / display_h
        x = int(relative_x * pixmap_w)
        y = int(relative_y * pixmap_h)

        annotation = {
            "x": x,
            "y": y,
            "x_ratio": round(x / pixmap_w, 3),
            "y_ratio": round(y / pixmap_h, 3)
        }
        filename = self.image_files[self.current_index]

        if filename not in self.annotations:
            self.annotations[filename] = []
        self.annotations[filename].append(annotation)

        self.add_annotation_item(annotation)

    def add_annotation_item(self, annotation):
        annotation_text = f"x: {annotation['x']} y: {annotation['y']} (比率: {annotation['x_ratio']}, {annotation['y_ratio']})"
        list_item = QListWidgetItem()

        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(annotation_text)
        delete_button = QPushButton("🗑")
        delete_button.setFixedWidth(30)

        def delete_item():
            index = self.annotation_list.row(list_item)
            filename = self.image_files[self.current_index]
            if 0 <= index < len(self.annotations.get(filename, [])):
                del self.annotations[filename][index]
                self.annotation_list.takeItem(index)

        delete_button.clicked.connect(delete_item)

        layout.addWidget(label)
        layout.addWidget(delete_button)
        container.setLayout(layout)

        list_item.setSizeHint(container.sizeHint())
        self.annotation_list.addItem(list_item)
        self.annotation_list.setItemWidget(list_item, container)

    def next_image(self):
        # すでに最後の画像が表示されている場合は、何もせず完了を通知する
        self.save_state()
        if self.current_index == len(self.image_files) - 1:
            self.next_button.setEnabled(False)
            self.next_button2.setEnabled(False)
            # 「終了」ボタンを追加
            # self.exit_button = QPushButton("終了")
            # self.exit_button.clicked.connect(self.close_application)
            # self.right_layout.addWidget(self.exit_button)
            return
        self.current_index += 1
        self.show_image()

    def save_state(self):
        # アノテーション保存
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(self.annotations, f, ensure_ascii=False, indent=2)

        # 処理済みマークを更新
        if os.path.exists(CSV_FILE):
            with open(CSV_FILE, newline='', encoding='utf-8') as f:
                rows = list(csv.DictReader(f))
            filename = self.image_files[self.current_index]
            for row in rows:
                if row['filename'] == filename:
                    row['processed'] = '1'
            with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['filename', 'processed'])
                writer.writeheader()
                writer.writerows(rows)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    annotator = ImageAnnotator()
    annotator.show()
    sys.exit(app.exec_())
