import os
import sys

# 抑制 Qt 在 Windows 上設定 DPI 時的「存取被拒」警告（不影響功能）
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.window=false")

import json
from pages import main_page, setting_page, account_page
from PyQt6.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QSystemTrayIcon, QMenu)
from PyQt6.QtGui import QIcon, QAction

APP_DATA_ROOT = os.path.join(os.environ['APPDATA'], 'FFXIV_Custom_Launcher')
CONFIG_PATH = os.path.join(APP_DATA_ROOT, 'config.json')

if not os.path.exists(APP_DATA_ROOT):
    os.makedirs(APP_DATA_ROOT)

def _icon_path():
    """打包後從 _MEIPASS 讀取，開發時從專案根目錄讀取"""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "favicon.ico")

# --- 主視窗管理 ---
class LauncherApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFXIV Launcher Beta")
        icon_path = _icon_path()
        if os.path.isfile(icon_path):
            icon = QIcon(icon_path)
            self.setWindowIcon(icon)
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
        self._setup_tray()

    def _setup_tray(self):
        """右下角系統匣圖示，點擊可再顯示主視窗"""
        icon_path = _icon_path()
        self.tray_icon = None
        if not os.path.isfile(icon_path):
            return
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(icon_path))
        self.tray_icon.setToolTip("FFXIV Launcher")
        menu = QMenu()
        show_act = QAction("顯示主視窗", self)
        show_act.triggered.connect(self._show_from_tray)
        menu.addAction(show_act)
        menu.addSeparator()
        quit_act = QAction("結束", self)
        quit_act.triggered.connect(QApplication.quit)
        menu.addAction(quit_act)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def hide_to_tray(self):
        """縮到右下系統匣（通知區域）；若無系統匣則改縮到工作列"""
        if getattr(self, "tray_icon", None) and self.tray_icon.isVisible():
            self.hide()
        else:
            self.showMinimized()

    def closeEvent(self, event):
        """按 X 關閉時縮到系統匣，不結束程式"""
        if getattr(self, "tray_icon", None) and self.tray_icon.isVisible():
            event.ignore()
            self.hide_to_tray()
        else:
            event.accept()

    def update_list(self):
        """重新讀取 JSON 並更新下拉選單"""
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
                self.launcher_path = self.config_data.get('launcher_path', "")
                self.accounts_data = self.config_data.get('accounts', {})
                self.main_page.account_selector.clear()
                self.main_page.account_selector.addItems(self.accounts_data.keys())
                # Keep MainPage in sync for direct access too
                self.main_page.accounts_data = self.accounts_data
                self.main_page.launcher_path = self.launcher_path
        else:
            # Ensure UI cleared when config missing
            self.launcher_path = ""
            self.accounts_data = {}
            self.main_page.account_selector.clear()
            self.main_page.accounts_data = {}
            self.main_page.launcher_path = ""

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 必須設定，否則 Windows 系統匣不顯示
    if not QSystemTrayIcon.isSystemTrayAvailable():
        pass  # 若無系統匣則不建立 tray，主視窗仍正常
    icon_path = _icon_path()
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    window = LauncherApp()
    window.show()
    sys.exit(app.exec())