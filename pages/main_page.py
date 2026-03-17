import os
import json
import time
import main
import pyotp
import pyautogui
import subprocess
import pygetwindow as gw
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt

class MainPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.accounts_data = {}
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(QLabel("選擇登入帳號:"))
        self.account_selector = QComboBox()
        self.account_selector.setFixedHeight(30)
        layout.addWidget(self.account_selector)

        self.btn_login = QPushButton("啟動遊戲 ")
        self.btn_login.setFixedHeight(40)
        self.btn_login.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold;")
        self.btn_login.clicked.connect(self.do_login)
        layout.addWidget(self.btn_login)

        self.btn_go_settings = QPushButton("系統設定")
        self.btn_go_settings.clicked.connect(lambda: self.controller.stack.setCurrentIndex(1))
        layout.addWidget(self.btn_go_settings)

        self.btn_go_account_settings = QPushButton("帳號設定")
        self.btn_go_account_settings.clicked.connect(lambda: self.controller.stack.setCurrentIndex(2))
        layout.addWidget(self.btn_go_account_settings)

    def do_login(self):
        name = self.account_selector.currentText()
        if not name: return

        user = self.accounts_data[name]
        try:
            totp = pyotp.TOTP(user['otp_secret'])
            code = totp.now()
            
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"驗證碼生成失敗: {e}")

        launcher_path = self.launcher_path
    
        if not os.path.exists(launcher_path):
            QMessageBox.critical(self, "錯誤", f"找不到啟動器：\n{launcher_path}")
            return

        subprocess.Popen([launcher_path])

        # 3. 等待啟動器視窗出現並置頂
        target_title = "FINAL FANTASY XIV"
        success = False
        
        # 最多等待 20 秒
        for _ in range(20):
            windows = gw.getWindowsWithTitle(target_title)
            if windows:
                launcher_win = windows[0]
                try:
                    launcher_win.activate() # 將視窗移到最上層
                    launcher_win.restore()  # 如果縮小了就還原
                    success = True
                    break
                except Exception:
                    pass
            time.sleep(1)

        if not success:
            QMessageBox.warning(self, "超時", "無法定位啟動器視窗，請手動點擊視窗後觀察。")
            return

        time.sleep(3) 

        # 模擬流程：
        # 假設初始焦點在帳號欄 (若不在，可能需要多按幾次 Tab)
        # 你可以先手動開啟一次啟動器，測試按幾次 Tab 會到帳號、密碼、OTP
        pyautogui.typewrite(user['username'], interval=0.1) # interval 讓打字看起來自然點
        pyautogui.press('tab')
        
        pyautogui.typewrite(user['password'], interval=0.1)
        pyautogui.press('tab')
        
        pyautogui.typewrite(code, interval=0.1)
        
        # 最後按下 Enter 登入
        pyautogui.press('enter')