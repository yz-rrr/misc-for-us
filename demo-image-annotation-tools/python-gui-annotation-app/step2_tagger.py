# coding: utf-8
"""
画像アノテーションタグ付けツール
このツールは、指定された画像の指定された位置のマークに対して、タグ付けを行うためのものです。
使用方法:
1. 画像ファイルを指定されたディレクトリに配置します。
2. 位置指定済みのJSONファイルを用意します。
3. タグ候補をYAMLファイルで定義します。
4. ツールを起動し、画像を選択してタグ付けを行います。
このツールは、PyQt5を使用してGUIを構築し、画像の表示とアノテーションの管理を行います。
"""

import csv
import sys
import os
import json

# import shlex
import yaml


from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QCheckBox,
    QMessageBox,
    QLineEdit,
    QScrollArea,
)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QBrush, QColor
from PyQt5.QtCore import Qt


from csv_tool import CSVTool  # 同じディレクトリのCSVToolクラスをインポート

# --- 設定類（適宜変更のこと） ---
# 【要確認・適宜変更】イメージ格納ディレクトリの場所を指定（画像表示に必要）
IMAGE_DIR = "./images_test/"
# 【タグ未付与時に存在必須】前段階で位置指定済みのJSONファイル【前段階から変えていなければ内容も変更不要】
JSON_ORIGINAL_FILE = "img_annotation.json"
# 【存在必須・ファイル名変更不要】タグ候補一覧【ファイル内容要編集】（複数ファイルを使い分けるなら↓の名前を変える手がある）
YAML_TAG_FILE = "tags.yaml"
# 【Optional】タイトルも表示するなら使用（ファイルがない場合は無視されるはず）
CSV_TITLE_FILE = "CSV_title_data.csv"
# 【Optional】タグ付け後のJSONファイル名（結果出力先・ファイル名変更不要）
JSON_FILE = "img_annotation_w_tag.json"
# 【Optional】画面左下に表示するタグ付けガイドの内容
GUIDE_CONTENT = "FS最大は帯部分除く最大でOK\n方向は全体が傾斜してたら縦・横もOK\nHTがはみ出てたら「添え」\n「シリーズ名の一部」は非HT的なものに使用\n文字色が〜は続く文字列数文字と異なる場合に\n範囲：色分離は1文字でもunitでも分離すれば✓\n単複はT以外も見て✓だが統計はTのみでいい"
# ガイドがいらない場合は以下をコメントアウト
# GUIDE_CONTENT = ""  # ガイドが不要な場合は空文字列にする
# --- ここまで設定類 ---


class AnnotationTagger(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "画像アノテーションタグ付けツール（使用データ：位置指定済・さらに非HT自動手動削除通した後がよい）"
        )
        self.setGeometry(100, 100, 1000, 700)

        # データ
        self.annotation_data = self.load_json()
        self.image_paths = list(self.annotation_data.keys())
        self.current_index = 0
        self.tags = self.load_tags()
        self.title_map = self.load_title_map()

        # GUI部品
        # 左側：ファイル名リストなど
        self.file_list = QListWidget()
        self.file_list.setFixedWidth(250)
        self.populate_file_list()
        self.file_list.clicked.connect(self.file_list_clicked)

        # 中央：画像表示
        # self.image_label = QLabel()
        # self.image_label.setAlignment(Qt.AlignCenter)
        # 中央：画像表示 を従来の QLabel から ImageDisplayLabel に変更
        self.image_label = ImageDisplayLabel()
        self.image_label.setAlignment(Qt.AlignCenter)

        # self.image_label の上に追加する例
        self.title_label = QLabel("")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 8px;"
        )

        # 右側：タグリスト、操作ボタン、カウント表示（右下）
        self.annotation_list = QListWidget()

        self.prev_button = QPushButton("← 戻る")
        self.next_button = QPushButton("次へ →")
        self.save_button = QPushButton("保存")
        self.quit_button = QPushButton("終了")
        self.prev_button = self.set_button_style(self.prev_button, bgcolor="#6e6e6e")
        self.next_button = self.set_button_style(self.next_button, bgcolor="#808080")
        self.save_button = self.set_button_style(self.save_button, bgcolor="#33c0c0")
        self.quit_button = self.set_button_style(self.quit_button, bgcolor="#c49306")

        self.prev_button.clicked.connect(self.prev_image)
        self.next_button.clicked.connect(self.next_image)
        self.save_button.clicked.connect(self.save_json)
        self.quit_button.clicked.connect(self.close)

        # 右下：個数表示用ラベル
        self.count_label = QLabel()
        self.count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # レイアウト作成
        # vbox_right = QVBoxLayout()

        # 左側レイアウト
        vbox_left = QVBoxLayout()

        # ファイル一覧
        vbox_file_list = QVBoxLayout()
        vbox_file_list.addWidget(QLabel("ファイル一覧（クリックでジャンプ）"))
        vbox_file_list.addWidget(self.file_list)
        self.file_list.setStyleSheet("* { font-size: 14px; }")

        # 案内
        vbox_guide = QVBoxLayout()
        vbox_guide.addWidget(
            QLabel(GUIDE_CONTENT)
        )

        vbox_left.addLayout(vbox_file_list, 9)
        vbox_left.addLayout(vbox_guide, 2)

        # 中央レイアウト：タイトルと画像表示
        vbox_middle = QWidget()
        vbox_image = QVBoxLayout()
        vbox_image.addWidget(self.title_label, 1)
        vbox_image.addWidget(self.image_label, 8)

        vbox_middle.setLayout(vbox_image)
        vbox_middle.setMinimumWidth(300)
        vbox_middle.setMaximumWidth(3000)

        # 右側レイアウト：タグ設定部、操作ボタン、カウント表示
        vbox_tags = QVBoxLayout()
        vbox_tags.addWidget(QLabel("指定した位置に対するタグの設定："))
        vbox_tags.addWidget(self.annotation_list)
        self.annotation_list.setStyleSheet("* { font-size: 14px; }")
        self.annotation_list.setMinimumWidth(300)
        # self.annotation_list.setMaximumWidth(2000)
        h_controls = QHBoxLayout()
        h_controls.addWidget(self.prev_button)
        h_controls.addWidget(self.next_button)
        h_controls.addWidget(self.save_button)
        h_controls.addWidget(self.quit_button)
        vbox_tags.addLayout(h_controls)
        vbox_tags.addWidget(self.count_label)

        # メインレイアウト：左＝ファイル一覧、中央＝画像、右＝タグ設定
        hbox = QHBoxLayout()
        hbox.addLayout(vbox_left, 1)
        hbox.addWidget(vbox_middle, 3)
        hbox.addLayout(vbox_tags, 2)

        self.setLayout(hbox)

        self.update_display()

    def set_button_style(self, button, fontsize="14px", bgcolor="#4CAF50"):
        # ボタンのスタイルを設定
        button.setStyleSheet(
            f"""
            QPushButton {{
                font-size: {fontsize};
                background-color: {bgcolor}; /* 緑 */
                color: white;
                margin: 2px;
                padding: 6px 2px;
                border: none;
                border-radius: 5px;
            }}
        """
        )
        return button

    def set_list_style(self, list_widget, fontsize="14px"):
        # リストのスタイルを設定
        list_widget.setStyleSheet(
            f"""
            QListWidget {{
                font-size: {fontsize};
            }}
        """
        )
        return list_widget

    def load_json(self):
        # JSON_FILE が存在する場合は読み込み、ない場合は JSON_ORIGINAL_FILE をコピー
        print("Loading JSON data...")
        print(f"JSON_FILE: {JSON_FILE}")
        print(f"JSON_ORIGINAL_FILE: {JSON_ORIGINAL_FILE}")

        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        elif os.path.exists(JSON_ORIGINAL_FILE):
            with open(JSON_ORIGINAL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            with open(JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return data
        else:
            QMessageBox.warning(self, "エラー", "JSONファイルが見つかりません。")
            return {}
        return {}

    def load_tags(self):
        if os.path.exists(YAML_TAG_FILE):
            with open(YAML_TAG_FILE, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return []

    def load_title_map(self):
        title_map = {}
        if os.path.exists(CSV_TITLE_FILE):
            csvTool = CSVTool()
            # CSVファイルのエンコーディングを判定
            encoding = csvTool.detect_file_encoding(CSV_TITLE_FILE)
            with open(CSV_TITLE_FILE, newline="", encoding=encoding) as csvfile:
                reader = csv.DictReader(csvfile, skipinitialspace=True)
                print(f"CSV_TITLE_FILE exists: {CSV_TITLE_FILE}")
                print(reader)
                filename_col = None
                title_col = None

                for i, row in enumerate(reader):
                    if i == 0:
                        # print(f"CSV_TITLE_FILE header: {row}")
                        filename_col = "Filename" if "Filename" in row else "filename"
                        title_col = "Title" if "Title" in row else "title"
                    filename = os.path.basename(row[filename_col]).strip()
                    title = row[title_col].strip()
                    title_map[filename] = title
        return title_map

    def populate_file_list(self):
        """ファイル一覧を更新・表示します。"""
        self.file_list.clear()
        for filename in self.image_paths:
            # タグがついているかチェック（任意：1件でも tags キーがあり非空なら [与] を付与）
            anns = self.annotation_data.get(filename, [])
            marked = any("tags" in ann and ann["tags"] for ann in anns)
            display_text = f"{filename} {'[与]' if marked else ''}"
            self.file_list.addItem(display_text)

    def file_list_clicked(self, index):
        row = index.row()
        if 0 <= row < len(self.image_paths):
            self.current_index = row
            self.update_display()

    def update_display(self):
        """画像、タイトル、タグリスト、カウント表示、ファイル一覧の選択状態を更新します。"""
        self.annotation_list.clear()
        if not self.image_paths:
            return

        # 中央：画像とタイトル
        current_file = self.image_paths[self.current_index]
        img_path = os.path.join(IMAGE_DIR, current_file)

        pixmap = QPixmap(img_path)
        self.image_label.setPixmap(
            pixmap.scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )

        # 🔽 タイトルの取得と表示．長過ぎたら切る．
        basename = os.path.basename(current_file)
        title = self.title_map.get(basename, "")
        # 最大表示幅（ピクセル単位、例：300ピクセル）
        max_width = 800
        fm = self.title_label.fontMetrics()
        elided_text = fm.elidedText(title, Qt.ElideRight, max_width)
        self.title_label.setText(elided_text)

        annotations = self.annotation_data[current_file]

        # 画像上にアノテーション丸を重ねるため、ImageDisplayLabel のメソッドを利用
        self.image_label.setPixmapWithAnnotations(pixmap, annotations)

        for i, ann in enumerate(annotations):

            # 位置情報
            x_ratio = ann.get("x_ratio", 0)
            y_ratio = ann.get("y_ratio", 0)

            # アノテーションのコンテンツウィジェットの作成
            content_widget = QWidget()
            layout = QVBoxLayout(content_widget)
            layout.addWidget(QLabel(f"(位置割合: {x_ratio:.3f}, {y_ratio:.3f})"))
            # タグ情報についてチェックボックス
            checkboxes = []
            for j, tag in enumerate(self.tags):
                cb = QCheckBox(tag)
                if "tags" in ann and tag in ann["tags"]:
                    cb.setChecked(True)
                cb.stateChanged.connect(self.save_tags)
                layout.addWidget(cb)
                checkboxes.append(cb)
                if j % 2 == 0:
                    cb.setProperty("even", True)
                    # 全体のスタイル（evenプロパティがTrueのときだけ適用）
                    cb.setStyleSheet(
                        'QCheckBox[even="true"] { background-color: #e0e0e0; }'
                    )

            # フリーコメント欄
            comment_edit = QLineEdit()
            comment_edit.setPlaceholderText("コメントがあれば入力")
            comment_edit.setText(ann.get("comment", ""))
            comment_edit.editingFinished.connect(self.save_tags)
            layout.addWidget(comment_edit)

            # コンテンツウィジェットをスクロールエリアでラップ
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(content_widget)
            # objectNameを設定
            scroll_area.setObjectName("scrollAreaOuter")
            scroll_area.setViewportMargins(0, 0, 0, 0)

            # パーツの色をiを使って変える
            # rgbの基礎値を設定
            color_r_base = 254 - (i * 60) % 200
            color_g_base = 254 - (i * 90) % 200
            color_b_base = 254 - (i * 150) % 200

            # ボーダーの色をiを使って変える
            border_color = f"rgb({(i * 200) % 255}, {(i * 30) % 255}, {(i * 55) % 255})"
            # 背景色をiを使って変える
            # border_color = f"rgb({color_r_base}, {color_g_base}, {color_b_base})"
            background_color = f"rgb({(color_r_base // 10) + 229}, {(color_g_base // 10) + 229}, {(color_b_base // 10) + 229})"
            # print(f"i: {i}, border_color: {border_color}, background_color: {background_color}")
            # scroll_area.setStyleSheet(f"{{background-color: {background_color};}}")
            # scroll_area.setStyleSheet(
            #    f"#scrollAreaOuter {{margin: 2px 15px 2px 1px; border: 1px solid {border_color}; border-radius: 3px; }}"
            # )
            scroll_area.setStyleSheet(
                f"* {{ background-color: {background_color}; }} "
                f"#scrollAreaOuter {{ margin: 2px 15px 2px 1px; border: 1px solid {border_color}; border-radius: 3px; }}"
            )

            item = QListWidgetItem()
            item.setSizeHint(scroll_area.sizeHint())
            self.annotation_list.addItem(item)
            self.annotation_list.setItemWidget(item, scroll_area)

        # 右下：進行状況表示（例： 現在の番号/全体の個数 ）
        self.count_label.setText(f"{self.current_index + 1} / {len(self.image_paths)}")

        # ファイルリストの選択状態更新
        self.file_list.setCurrentRow(self.current_index)
        # ファイル一覧のマーク更新（タグ付け済み [済] 表示）
        self.populate_file_list()

    def save_tags(self):
        """タグ付け内容の変更を self.annotation_data に反映します。"""
        current_file = self.image_paths[self.current_index]
        annotations = self.annotation_data[current_file]

        for i in range(self.annotation_list.count()):
            item = self.annotation_list.item(i)
            scroll_area = self.annotation_list.itemWidget(item)
            # QScrollAreaの中のウィジェットを取得する
            content_widget = scroll_area.widget()
            layout = content_widget.layout()
            tags = []
            comment_text = ""
            # layout の全ウィジェットをチェック（QCheckBox:タグ、QLineEdit:フリーコメント）
            for j in range(1, layout.count()):
                child = layout.itemAt(j).widget()
                if isinstance(child, QCheckBox):
                    if child.isChecked():
                        tags.append(child.text())
                elif isinstance(child, QLineEdit):
                    raw_text = child.text()
                    if raw_text and raw_text.strip():
                        comment_text = raw_text.strip()
            annotations[i]["tags"] = tags
            if comment_text:
                annotations[i]["comment"] = comment_text
            else:
                if "comment" in annotations[i].keys():
                    del annotations[i]["comment"]

        # 更新後、ファイルリストのマークも更新
        self.populate_file_list()

    def next_image(self):
        self.save_tags()
        if self.current_index < len(self.image_paths) - 1:
            self.current_index += 1
            self.update_display()

    def prev_image(self):
        self.save_tags()
        if self.current_index > 0:
            self.current_index -= 1
            self.update_display()

    def save_json(self):
        self.save_tags()
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(self.annotation_data, f, indent=2, ensure_ascii=False)
        QMessageBox.information(self, "保存完了", "JSONファイルを保存しました。")


class ImageDisplayLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap_to_display = None
        self.annotations = []  # 各アノテーション（辞書型：x_ratio, y_ratio など）

    def setPixmapWithAnnotations(self, pixmap, annotations):
        self.pixmap_to_display = pixmap
        self.annotations = annotations
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.pixmap_to_display:
            return

        painter = QPainter(self)
        # ウィジェットサイズに合わせたスケール済み pixmap を取得
        scaled_pixmap = self.pixmap_to_display.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        # pixmap をウィジェット中央に配置
        pixmap_rect = scaled_pixmap.rect()
        pixmap_rect.moveCenter(self.rect().center())
        painter.drawPixmap(pixmap_rect.topLeft(), scaled_pixmap)

        # アノテーション描画用の設定
        radius = 10  # 円の半径
        color = QColor(Qt.blue)  # 円の色
        color.setAlpha(128)  # 半透明にする（0～255）
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)  # 塗りつぶさない設定

        # 各アノテーションの x_ratio, y_ratio を元に円を描画
        for ann in self.annotations:
            # 画像内の描画位置（scaled_pixmap 内での位置）を算出する
            x = ann.get("x_ratio", 0) * scaled_pixmap.width() + pixmap_rect.left()
            y = ann.get("y_ratio", 0) * scaled_pixmap.height() + pixmap_rect.top()
            painter.drawEllipse(
                int(x - radius), int(y - radius), int(radius * 2), int(radius * 2)
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = AnnotationTagger()
    viewer.show()
    sys.exit(app.exec_())
