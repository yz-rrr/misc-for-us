# -*- coding: utf-8 -*-
# pixi run python -m src.main

import os
import random
import sys
# import json
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QScrollArea, QGridLayout, QFileDialog, QCheckBox
)
from PyQt5.QtGui import QPixmap, QGuiApplication
from PyQt5.QtCore import Qt

CSV_FILE = "sample_annotation.csv"
# IMAGE_DIR = "./images"  # 定数として画像ディレクトリを指定
IMAGE_DIR = "./images_test"  # 定数として画像ディレクトリを指定
NOSHOW_FILE = "config_noshow.csv"  # 表示しない画像のファイル名を記載したファイル

# 表示プロパティ
SHOW_NUM = 8  # 表示する画像の枚数
HORIZONTAL_NUM = int((SHOW_NUM + 1) // 2) # 横に並べる画像の枚数（例：5枚表示する場合は3枚と2枚に分ける）

CLUSTER_COLUMN = 'cluster'  # クラスタの列名. 自動ではcluster, 手動ならcluster_manを基本とする.
IF_SHOW_UNIQUE = False  # 重複しないファイル名のエントリを抽出するかどうか（True: 重複しないファイル名のエントリを抽出, False: 重複してもいいよな？）


class ImageClusterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Cluster Viewer")
        self.setGeometry(100, 100, 1200, 800)

        self.saved_mode = False  # 保存CSVから読み込んだモードか否か

        # 初回は通常のCSVからdataを作成
        self.data = self.load_data()
        self.clusters = self.group_by_cluster()
        self.current_displayed_entries = []

        # コントロール用レイアウト（Reload, Save View, Load Saved CSV, Save Selected Filenamesボタン）
        control_layout = QHBoxLayout()
        reload_btn = QPushButton("Reload（読み込みもリセット）")
        reload_btn.clicked.connect(self.reload_images)
        control_layout.addWidget(reload_btn)

        save_btn = QPushButton("Save View")
        save_btn.clicked.connect(self.save_view)
        control_layout.addWidget(save_btn)

        load_saved_btn = QPushButton("Load Saved CSV")
        load_saved_btn.clicked.connect(self.load_saved_view)
        control_layout.addWidget(load_saved_btn)

        save_selected_btn = QPushButton("Save Selected Filenames")
        save_selected_btn.clicked.connect(self.save_selected_filenames)
        control_layout.addWidget(save_selected_btn)

        control_layout.addStretch()

        # 全体のレイアウトをまとめるウィジェット
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.create_cluster_views()

        # スクロール可能な領域を作成
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.content_widget)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(control_layout)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    def load_data(self):
        data = []
        if os.path.exists(CSV_FILE):
            df = pd.read_csv(CSV_FILE)
            if df.empty:
                raise ValueError(f"{CSV_FILE} is empty.")
            data = df.to_dict(orient='records')
            for entry in data:
                entry['filepath'] = os.path.join(IMAGE_DIR, entry['filename'])
            print(f"Loaded {len(data)} entries from {CSV_FILE}.")
            # return data
        else:
            print(f"File not found: {CSV_FILE}")
            raise FileNotFoundError(f"{CSV_FILE} not found.")
        
        # noshow_dataを読み込み，表示しないファイル名のセットを取得
        noshow_filenames = self.load_noshow_data()
        # noshow_dataに含まれるファイル名を除外
        data = [entry for entry in data if entry['filename'] not in noshow_filenames]
        print(f"Filtered {len(noshow_filenames)} entries from {CSV_FILE}.")
        return data

    # noshow_dataを読み込み，filenameのセットを返す
    def load_noshow_data(self):
        noshow_filenames = set()
        if os.path.exists(NOSHOW_FILE):
            df = pd.read_csv(NOSHOW_FILE)
            if df.empty:
                print(f"{NOSHOW_FILE} is empty.")
                # raise ValueError(f"{NOSHOW_FILE} is empty.")
            noshow_data = df.to_dict(orient='records')
            noshow_filenames = {entry['filename'] for entry in noshow_data}
            print(f"Loaded {len(noshow_filenames)} entries from {NOSHOW_FILE}.")
        else:
            print(f"File not found: {NOSHOW_FILE}")
            # raise FileNotFoundError(f"{NOSHOW_FILE} not found.")
        return noshow_filenames

    def group_by_cluster(self):
        clusters = {}
        for entry in self.data:
            cluster = entry[CLUSTER_COLUMN]
            if cluster not in clusters:
                clusters[cluster] = []
            clusters[cluster].append(entry)
        # クラスタのキーを昇順にソート
        sorted_clusters = {k: clusters[k] for k in sorted(clusters.keys())}
        return sorted_clusters
    
    def get_comment(self, entry):
        # コメントを取得する関数
        # ただしnanの場合は空文字を返す
        # 数値だったらstrに変換して返す
        comment = entry.get('comment', '')
        if pd.isna(comment):
            return ''
        elif comment == 'nan':
            return ''
        # それ以外は改行を取り除いて返す
        elif isinstance(comment, str):
            comment = comment.replace('\n', '')
        elif isinstance(comment, (int, float)):
            comment = str(comment)
        else:
            # それ以外の型はそのまま返す
            pass
        return str(comment)

    def create_image_widget(self, entry):
        """１つの画像とチェックボックス・コメント欄を含むウィジェットを作成"""
        container = QWidget()
        container.setFixedSize(180, 220)  # 全体のサイズ

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 画像表示領域は常に固定180px、コメント欄は固定40pxを割り当てる
        frame = QWidget(container)
        frame.setFixedSize(180, 180)
        layout.addWidget(frame)

        # 画像ラベル
        image_label = QLabel(frame)
        image_label.setGeometry(0, 0, frame.width(), frame.height())
        image_label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(entry['filepath'])
        # 画像をframeサイズ内で縦横比を維持してスケール
        scaled_pix = pixmap.scaled(frame.width(), frame.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(scaled_pix)

        # 画像の上にx,y座標を表示する
        x_label = QLabel(f"X: {entry.get('x_ratio', 'N/A')}", image_label)
        y_label = QLabel(f"Y: {entry.get('y_ratio', 'N/A')}", image_label)
        x_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        y_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        x_label.setStyleSheet("color: white; background-color: black; font-size: 11px;")
        y_label.setStyleSheet("color: white; background-color: black; font-size: 11px;")
        x_label.move(0, 0)
        y_label.move(0, 20)

        # 右上にチェックボックスを配置
        checkbox = QCheckBox(frame)
        checkbox.setGeometry(frame.width() - 20, 0, 20, 20)
        entry['checkbox'] = checkbox

        # コメント欄は常に40px割当（背景は透過）
        comment_label = QLabel(container)
        comment_label.setFixedHeight(40)
        comment_label.setStyleSheet("background: transparent; font-size: 9px; color: gray;")
        comment_text = self.get_comment(entry)
        if comment_text:
            display_text = comment_text[:20] + ("..." if len(comment_text) > 20 else "")
            comment_label.setText(display_text)
        layout.addWidget(comment_label)

        return container

    def create_cluster_views(self):
        # 既存のウィジェットをクリア
        for i in reversed(range(self.content_layout.count())):
            widget_to_remove = self.content_layout.itemAt(i).widget()
            if widget_to_remove is not None:
                widget_to_remove.setParent(None)

        self.current_displayed_entries = []
        # 各クラスタ毎に表示
        for cluster, entries in self.clusters.items():
            cluster_widget = QWidget()
            cluster_layout = QVBoxLayout(cluster_widget)
            
            cluster_label = QLabel(f"Cluster: {cluster}")
            cluster_layout.addWidget(cluster_label)
            
            grid_layout = QGridLayout()
            # 画像間の余白設定（例：水平・垂直10px）
            grid_layout.setHorizontalSpacing(10)
            grid_layout.setVerticalSpacing(10)
            
            target_entries = entries
            # 重複しないファイル名のエントリを抽出（でも重複してもいいよな？）
            if IF_SHOW_UNIQUE:
                unique_filenames = set()
                unique_entries = []
                for entry in entries:
                    filename = entry['filename']
                    if filename not in unique_filenames:
                        unique_filenames.add(filename)
                        unique_entries.append(entry)
                target_entries = unique_entries
                print(f"Cluster {cluster}: {len(target_entries)} unique entries")
            else:
                print(f"Cluster {cluster}: {len(target_entries)} entries")
            # モードに応じて表示件数を決定：
            # saved_modeの場合は先頭から10件，通常はランダムに10件表示
            if self.saved_mode:
                sample_entries = target_entries[:SHOW_NUM]
            else:
                sample_entries = random.sample(target_entries, min(SHOW_NUM, len(target_entries)))
            
            for i, entry in enumerate(sample_entries):
                img_widget = self.create_image_widget(entry)
                grid_layout.addWidget(img_widget, i // HORIZONTAL_NUM, i % HORIZONTAL_NUM)
                self.current_displayed_entries.append(entry)
            
            # グリッドレイアウトをスクロールエリアにセット
            grid_widget = QWidget()
            grid_widget.setLayout(grid_layout)
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(grid_widget)
            cluster_layout.addWidget(scroll_area)
            
            # クラスタ表示エリアの最低高さを調整（コメント表示等を考慮して拡大）
            cluster_widget.setMinimumHeight(500)
            self.content_layout.addWidget(cluster_widget)

    def save_selected_filenames(self):
        # チェックの入った画像のfilenameを取得してCSVにまとめて保存
        selected_files = [entry['filename'] for entry in self.current_displayed_entries 
                          if entry.get('checkbox') and entry['checkbox'].isChecked()]
        if not selected_files:
            print("No files selected.")
            return

        csv_save_path, _ = QFileDialog.getSaveFileName(self, "Save Selected Filenames", "", "CSV Files (*.csv)")
        if csv_save_path:
            if not csv_save_path.endswith(".csv"):
                csv_save_path += ".csv"
            df = pd.DataFrame({"filename": selected_files})
            df.to_csv(csv_save_path, index=False, encoding="utf-8-sig")
            print("Selected filenames saved to", csv_save_path)

    def reload_images(self):
        print("Reloading images...")
        self.saved_mode = False  # チェックなどは新たに作り直すため初期状態に戻す
        self.data = self.load_data()
        self.clusters = self.group_by_cluster()
        self.create_cluster_views()

    def save_view(self):
        """
        # 現在の画面のスクリーンショットを保存：スクリーンショット単体を保存しても微妙なのでコメントアウトする．
        screen = QGuiApplication.primaryScreen()
        screenshot = screen.grabWindow(self.winId())
        img_save_path, _ = QFileDialog.getSaveFileName(self, "Save Screenshot", "", "PNG Files (*.png)")
        if img_save_path:
            screenshot.save(img_save_path, "png")
            print("Screenshot saved to", img_save_path)
        """
            
        # 現在表示中の画像ファイル名をテキストファイルに保存
        # 復元できるように，エンティティの情報全てを保存する．
        # このため，df_to_dict でdictに変換されたものを，いったんdataframeに戻してから保存する．


        csv_save_path, _ = QFileDialog.getSaveFileName(self, "Save File Names", "", "CSV Files (*.csv)")
        if csv_save_path:
            if not csv_save_path.endswith(".csv"):
                csv_save_path += ".csv"
            # 現在表示中のエントリをDataFrameに変換（ただし filepath はこのアプリで作成する物なので削除しておく）
            df_current_displayed_entries = pd.DataFrame(self.current_displayed_entries).drop("filepath", axis=1)
            df_current_displayed_entries.to_csv(csv_save_path, index=False, encoding="utf-8-sig")
            """
            # 現在表示中のエントリからファイル名を取得して保存する．
            with open(csv_save_path, "w", encoding="utf-8") as f:
                f.write("cluster, filename\n")
                for entry in self.current_displayed_entries:
                    f.write(f"{entry[CLUSTER_COLUMN]}, {os.path.basename(entry['filename'])}\n")
            print("File names saved to", csv_save_path)
            """

    def load_saved_view(self):
        # 保存済みCSVファイルを読み込み，表示モードを切り替える
        csv_load_path, _ = QFileDialog.getOpenFileName(self, "Load Saved CSV View", "", "CSV Files (*.csv)")
        if csv_load_path:
            df = pd.read_csv(csv_load_path)
            records = df.to_dict(orient='records')
            # 保存時に削除していたfilepathを再構築
            for entry in records:
                entry['filepath'] = os.path.join(IMAGE_DIR, entry['filename'])
            self.data = records
            # グループ化のためにself.clustersを再構築
            self.clusters = self.group_by_cluster()
            self.saved_mode = True
            self.create_cluster_views()
            print(f"Loaded saved view from {csv_load_path}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = ImageClusterApp()
    viewer.show()
    sys.exit(app.exec_())