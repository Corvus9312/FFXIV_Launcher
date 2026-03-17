import os
import json
import main
from urllib.parse import urlparse, parse_qs
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QFileDialog, QHBoxLayout)

class SettingPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.layout = QVBoxLayout(self)

        self.layout.addWidget(QLabel("<h2>系統設定</h2>"))
        
        # 啟動器路徑
        self.layout.addWidget(QLabel("官方啟動器路徑 (FFXIV_Launcher.exe):"))
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.browse_btn = QPushButton("瀏覽")
        self.browse_btn.clicked.connect(self.browse_path)
        
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_btn)
        self.layout.addLayout(path_layout)

        # 保存
        self.save_btn = QPushButton("儲存並返回")
        self.save_btn.clicked.connect(self.save_settings)
        self.layout.addWidget(self.save_btn)

        self.load_settings()

    def browse_path(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "選擇官方啟動器", "", "執行檔 (*.exe)")
        if file_path:
            self.path_input.setText(file_path)

    def save_settings(self):
        data = {}
        if os.path.exists(main.CONFIG_PATH):
            with open(main.CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        data['launcher_path'] = self.path_input.text()
        
        with open(main.CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        self.controller.update_list()
        self.controller.stack.setCurrentIndex(0)

    def load_settings(self):
        if os.path.exists(main.CONFIG_PATH):
            with open(main.CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.path_input.setText(data.get('launcher_path', ""))