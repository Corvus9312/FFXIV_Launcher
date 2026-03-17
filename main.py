import os
import sys
import json
from pages import main_page, setting_page, account_page
from PyQt6.QtWidgets import (QApplication, QMainWindow, QStackedWidget)

APP_DATA_ROOT = os.path.join(os.environ['APPDATA'], 'FFXIV_Custom_Launcher')
CONFIG_PATH = os.path.join(APP_DATA_ROOT, 'config.json')

if not os.path.exists(APP_DATA_ROOT):
    os.makedirs(APP_DATA_ROOT)

# --- 主視窗管理 ---
class LauncherApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFXIV Launcher Beta")
        self.setFixedSize(400, 350)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.main_page = main_page.MainPage(self)
        self.setting_page = setting_page.SettingPage(self)
        self.account_settings_page = account_page.AccountPage(self)

        self.stack.addWidget(self.main_page)
        self.stack.addWidget(self.setting_page)
        self.stack.addWidget(self.account_settings_page)

        self.update_list()

    def update_list(self):
        """重新讀取 JSON 並更新下拉選單"""
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
                self.launcher_path = self.config_data.get('launcher_path', "")
                self.accounts_data = self.config_data.get('accounts', {})
                self.main_page.account_selector.clear()
                self.main_page.account_selector.addItems(self.accounts_data.keys())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LauncherApp()
    window.show()
    sys.exit(app.exec())