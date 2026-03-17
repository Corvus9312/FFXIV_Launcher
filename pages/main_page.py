import os
import time
import pyotp
import pyautogui
import subprocess
import pygetwindow as gw
import ctypes
from ctypes import wintypes
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt

class MainPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
        self.accounts_data = {}
        self.launcher_path = ""

        self.ui_step_delay = 0.1
        self.launch_delay = 1.0

        pyautogui.PAUSE = self.ui_step_delay
        pyautogui.FAILSAFE = True
        
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

        accounts = getattr(self.controller, "accounts_data", None) or self.accounts_data or {}
        user = accounts.get(name)
        if not user:
            QMessageBox.warning(self, "錯誤", f"找不到帳號資料：{name}\n請到「帳號設定」確認已儲存，或重新開啟程式。")
            return
        try:
            totp = pyotp.TOTP(user['otp_secret'])
            code = totp.now()
            
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"驗證碼生成失敗: {e}")

        launcher_path = getattr(self.controller, "launcher_path", None) or self.launcher_path
    
        if not os.path.exists(launcher_path):
            QMessageBox.critical(self, "錯誤", f"找不到啟動器：\n{launcher_path}")
            return

        # 點擊啟動遊戲後，縮到右下系統匣（通知區域）
        self.controller.hide_to_tray()

        # 盡量讓啟動器不要「跳出來擋視線」：以最小化方式啟動（仍會出現在工作列）
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 2  # SW_SHOWMINIMIZED
            subprocess.Popen([launcher_path], startupinfo=si)
        except Exception:
            subprocess.Popen([launcher_path])

        # 3. 等待啟動器視窗出現並置頂
        target_title = "FINAL FANTASY XIV"
        success = False
        hwnd = None
        
        # 最多等待 20 秒
        for _ in range(20):
            windows = gw.getWindowsWithTitle(target_title)
            if windows:
                launcher_win = windows[0]
                try:
                    hwnd = getattr(launcher_win, "_hWnd", None)
                    if hwnd and self._is_window(hwnd):
                        self._focus_window(hwnd)
                    success = True
                    break
                except Exception:
                    pass
            time.sleep(1)

        if not success:
            QMessageBox.warning(self, "超時", "無法定位啟動器視窗，請手動點擊視窗後觀察。")
            return

        # 全自動：不要依賴 Tab（官方啟動器常不工作），改用相對座標點擊三個欄位後輸入。
        time.sleep(0.5)
        if not hwnd or not self._is_window(hwnd):
            hwnd = self._find_launcher_hwnd(target_title)
        if not hwnd:
            QMessageBox.warning(self, "錯誤", "找不到啟動器視窗控制代碼，無法自動輸入。")
            return
        self._focus_window(hwnd)
        time.sleep(0.5)

        # 全自動點擊座標（相對於視窗）：依「繁中服啟動器」版面校準的預設值。
        # 若日後啟動器 UI 改版，只需調整這四組 rx/ry。
        try:
            # 你要求：y 全部往下 +0.01
            self._type_into_launcher_field(hwnd, rx=0.70, ry=0.38, text=user['username'])
            self._type_into_launcher_field(hwnd, rx=0.70, ry=0.48, text=user['password'])
            self._type_into_launcher_field(hwnd, rx=0.70, ry=0.58, text=code)
        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"自動輸入失敗：{e}")
            return

        # Click login button area (best-effort) then Enter as fallback
        self._click_launcher(hwnd, rx=0.70, ry=0.70)
        time.sleep(self.launch_delay)
        self._click_launcher(hwnd, rx=0.70, ry=0.70)

    def _is_window(self, hwnd: int) -> bool:
        try:
            return bool(ctypes.windll.user32.IsWindow(wintypes.HWND(hwnd)))
        except Exception:
            return False

    def _find_launcher_hwnd(self, title: str):
        try:
            windows = gw.getWindowsWithTitle(title)
            for w in windows:
                h = getattr(w, "_hWnd", None)
                if h and self._is_window(h):
                    return h
        except Exception:
            return None
        return None

    def _focus_window(self, hwnd: int):
        user32 = ctypes.windll.user32
        try:
            user32.ShowWindow(wintypes.HWND(hwnd), 9)  # SW_RESTORE
        except Exception:
            pass
        try:
            user32.SetForegroundWindow(wintypes.HWND(hwnd))
        except Exception:
            pass

    def _get_window_rect(self, hwnd: int):
        rect = wintypes.RECT()
        ok = ctypes.windll.user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect))
        if not ok:
            raise OSError(f"Error code from Windows: {ctypes.GetLastError()}")
        return rect.left, rect.top, rect.right, rect.bottom

    def _click_launcher(self, hwnd: int, rx: float, ry: float):
        if not self._is_window(hwnd):
            raise OSError("Error code from Windows: 1400")
        left, top, right, bottom = self._get_window_rect(hwnd)
        width = right - left
        height = bottom - top
        x = left + int(width * rx)
        y = top + int(height * ry)
        pyautogui.click(x, y)

    def _type_into_launcher_field(self, hwnd: int, rx: float, ry: float, text: str):
        # If hwnd becomes invalid mid-flow, try reacquire once.
        if not self._is_window(hwnd):
            new_hwnd = self._find_launcher_hwnd("FINAL FANTASY XIV")
            if not new_hwnd:
                raise OSError("Error code from Windows: 1400")
            hwnd = new_hwnd
            self._focus_window(hwnd)
            time.sleep(0.2)

        self._click_launcher(hwnd, rx, ry)
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.5)
        # interval 也跟著放慢（避免啟動器吃字/焦點抖動）
        pyautogui.typewrite(text, interval=0.05)
        time.sleep(0.5)