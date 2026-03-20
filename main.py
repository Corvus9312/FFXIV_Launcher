import os
import sys
import time
import ctypes
import traceback
from ctypes import wintypes

# 抑制 Qt 在 Windows 上設定 DPI 時的「存取被拒」警告（不影響功能）
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.window=false")

import json
from pages import main_page, setting_page, account_page
from PyQt6.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QSystemTrayIcon, QMenu)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer

APP_DATA_ROOT = os.path.join(os.environ['APPDATA'], 'FFXIV_Custom_Launcher')
CONFIG_PATH = os.path.join(APP_DATA_ROOT, 'config.json')

if not os.path.exists(APP_DATA_ROOT):
    os.makedirs(APP_DATA_ROOT)

_SINGLE_INSTANCE_MUTEX = None

# region agent log
def _debug_log(hypothesis_id: str, location: str, message: str, data=None, run_id: str = "pre-fix"):
    try:
        payload = {
            "sessionId": "4db6fa",
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }
        with open("debug-4db6fa.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
# endregion

def _bring_existing_window_to_front(window_title: str, timeout_s: float = 2.0) -> bool:
    """嘗試將已執行的同程式視窗喚到前景（Windows）。"""
    if os.name != "nt":
        return False

    user32 = ctypes.WinDLL("user32", use_last_error=True)

    FindWindowW = user32.FindWindowW
    FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    FindWindowW.restype = wintypes.HWND

    ShowWindow = user32.ShowWindow
    ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    ShowWindow.restype = wintypes.BOOL

    SetForegroundWindow = user32.SetForegroundWindow
    SetForegroundWindow.argtypes = [wintypes.HWND]
    SetForegroundWindow.restype = wintypes.BOOL

    SetWindowPos = user32.SetWindowPos
    SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    SetWindowPos.restype = wintypes.BOOL

    GetWindowLongW = user32.GetWindowLongW
    GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    GetWindowLongW.restype = ctypes.c_long

    SetWindowLongW = user32.SetWindowLongW
    SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    SetWindowLongW.restype = ctypes.c_long

    UpdateWindow = user32.UpdateWindow
    UpdateWindow.argtypes = [wintypes.HWND]
    UpdateWindow.restype = wintypes.BOOL

    RedrawWindow = user32.RedrawWindow
    # (hWnd, lprcUpdate, hrgnUpdate, uFlags)
    RedrawWindow.argtypes = [wintypes.HWND, wintypes.LPCVOID, wintypes.HRGN, wintypes.UINT]
    RedrawWindow.restype = wintypes.BOOL

    SW_RESTORE = 9
    HWND_TOPMOST = wintypes.HWND(-1)
    HWND_NOTOPMOST = wintypes.HWND(-2)
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOZORDER = 0x0004
    SWP_SHOWWINDOW = 0x0040
    SWP_FRAMECHANGED = 0x0020
    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    RDW_INVALIDATE = 0x0001
    RDW_ALLCHILDREN = 0x0080
    RDW_UPDATENOW = 0x0100

    deadline = time.time() + max(0.0, timeout_s)
    while True:
        hwnd = FindWindowW(None, window_title)
        if hwnd:
            # H12: 若之前縮到 tray 時切成 TOOLWINDOW，先恢復成 APPWINDOW 再喚回
            ex_before = int(GetWindowLongW(hwnd, GWL_EXSTYLE))
            ex_after = ex_before
            if ex_before & WS_EX_TOOLWINDOW:
                ex_after = (ex_before & (~WS_EX_TOOLWINDOW)) | WS_EX_APPWINDOW
                SetWindowLongW(hwnd, GWL_EXSTYLE, ex_after)
                SetWindowPos(
                    hwnd, wintypes.HWND(0), 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED
                )
            # region agent log
            _debug_log("H12", "main.py:_bring_existing_window_to_front", "exstyle before/after normalize", {
                "hwnd": int(hwnd),
                "exBefore": ex_before,
                "exAfter": ex_after,
                "hadToolWindow": bool(ex_before & WS_EX_TOOLWINDOW),
            })
            # endregion

            # 視窗保持 minimized（而不是 hidden）時，SW_RESTORE 可正常喚回 Qt 內容
            ok_show = ShowWindow(hwnd, SW_RESTORE)
            # 常見前景限制下的小技巧：先置頂再取消置頂，提升成功率
            ok_top = SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
            ok_notop = SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
            ok_fg = SetForegroundWindow(hwnd)
            # region agent log
            _debug_log("H11", "main.py:_bring_existing_window_to_front", "focus api returns", {
                "hwnd": int(hwnd),
                "ok_show": bool(ok_show),
                "ok_top": bool(ok_top),
                "ok_notop": bool(ok_notop),
                "ok_fg": bool(ok_fg),
            })
            # endregion
            try:
                ok_update = UpdateWindow(hwnd)
                # region agent log
                _debug_log("H11", "main.py:_bring_existing_window_to_front", "UpdateWindow result", {
                    "ok_update": bool(ok_update),
                })
                # endregion
            except Exception:
                pass
            try:
                ok_redraw = RedrawWindow(hwnd, None, None, RDW_INVALIDATE | RDW_ALLCHILDREN | RDW_UPDATENOW)
                # region agent log
                _debug_log("H11", "main.py:_bring_existing_window_to_front", "RedrawWindow result", {
                    "ok_redraw": bool(ok_redraw),
                })
                # endregion
            except Exception:
                pass
            return True

        if time.time() >= deadline:
            return False
        time.sleep(0.1)

def _ensure_single_instance_or_focus_existing(app_id: str, window_title: str) -> bool:
    """
    確保單一實例。
    - 回傳 True：可繼續啟動（第一次實例）
    - 回傳 False：已存在，已嘗試喚回既有視窗，新程序應退出
    """
    global _SINGLE_INSTANCE_MUTEX

    if os.name != "nt":
        return True

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    CreateMutexW = kernel32.CreateMutexW
    CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    CreateMutexW.restype = wintypes.HANDLE

    GetLastError = kernel32.GetLastError
    GetLastError.argtypes = []
    GetLastError.restype = wintypes.DWORD

    ERROR_ALREADY_EXISTS = 183
    name = f"Global\\{app_id}"
    h_mutex = CreateMutexW(None, True, name)
    # region agent log
    _debug_log("H1", "main.py:_ensure_single_instance_or_focus_existing", "mutex created", {
        "mutexName": name,
        "hasHandle": bool(h_mutex),
    })
    # endregion
    if not h_mutex:
        # 建 mutex 失敗時，保守起見仍讓程式繼續跑
        return True

    last_error = int(GetLastError())
    # region agent log
    _debug_log("H1", "main.py:_ensure_single_instance_or_focus_existing", "mutex last error", {
        "lastError": last_error,
        "alreadyExistsCode": ERROR_ALREADY_EXISTS,
    })
    # endregion
    if last_error == ERROR_ALREADY_EXISTS:
        # region agent log
        _debug_log("H4", "main.py:_ensure_single_instance_or_focus_existing", "already exists branch (focus only)", {
            "windowTitle": window_title,
        })
        # endregion
        focused = _bring_existing_window_to_front(window_title)
        # region agent log
        _debug_log("H4", "main.py:_ensure_single_instance_or_focus_existing", "focus result", {
            "focused": bool(focused),
        })
        # endregion
        if not focused:
            # 找不到可喚回視窗時，不阻擋新實例啟動，避免看起來「程式打不開」。
            _SINGLE_INSTANCE_MUTEX = h_mutex
            return True
        return False

    # 必須保留 handle，否則 mutex 會被釋放導致可多開
    _SINGLE_INSTANCE_MUTEX = h_mutex
    return True

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
        # region agent log
        _debug_log("H6", "main.py:LauncherApp.__init__", "constructor start")
        # endregion
        super().__init__()
        self.setWindowTitle("FFXIV Corvus Launcher")
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
        # region agent log
        _debug_log("H6", "main.py:LauncherApp.__init__", "constructor end")
        # endregion

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
        self._set_taskbar_presence(True)
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def hide_to_tray(self):
        """縮到右下系統匣（通知區域）；若無系統匣則改縮到工作列"""
        # 目標：點啟動後「不在畫面上、也不在工作列」。
        # 不使用 hide()（hidden 狀態會讓重複啟動喚回容易白畫面）；
        # 改為 minimized + toolwindow，保持可被 SW_RESTORE 正常喚回。
        if getattr(self, "tray_icon", None) is not None:
            self.tray_icon.show()
            QApplication.processEvents()
            self._set_taskbar_presence(False)
            self.showMinimized()
        else:
            self.showMinimized()

    def _set_taskbar_presence(self, visible_in_taskbar: bool):
        """
        visible_in_taskbar=False 時，把視窗轉成 Tool window，
        通常不會出現在 Windows 工作列。
        """
        try:
            hwnd = int(self.winId())
            if hwnd <= 0:
                return
        except Exception:
            return

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_APPWINDOW = 0x00040000

        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_FRAMECHANGED = 0x0020

        try:
            GetWindowLongW = user32.GetWindowLongW
            SetWindowLongW = user32.SetWindowLongW
            SetWindowPos = user32.SetWindowPos

            GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
            GetWindowLongW.restype = ctypes.c_long
            SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
            SetWindowLongW.restype = ctypes.c_long
            SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]

            exstyle = GetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE)
            if visible_in_taskbar:
                exstyle = exstyle & (~WS_EX_TOOLWINDOW)
                exstyle = exstyle | WS_EX_APPWINDOW
            else:
                exstyle = exstyle | WS_EX_TOOLWINDOW
                exstyle = exstyle & (~WS_EX_APPWINDOW)

            SetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE, exstyle)
            SetWindowPos(
                wintypes.HWND(hwnd),
                wintypes.HWND(0),
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED
            )
        except Exception:
            # 若樣式切換失敗，至少還會 showMinimized()，不影響主要功能。
            return

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
    # region agent log
    _debug_log("H5", "main.py:__main__", "program entry", {"argv": sys.argv})
    # endregion
    if not _ensure_single_instance_or_focus_existing(
        app_id="FFXIV Corvus Launcher_8f3a1c2e",
        window_title="FFXIV Corvus Launcher",
    ):
        # region agent log
        _debug_log("H5", "main.py:__main__", "exiting due to existing instance")
        # endregion
        sys.exit(0)

    try:
        # region agent log
        _debug_log("H5", "main.py:__main__", "creating QApplication")
        # endregion
        app = QApplication(sys.argv)
        # region agent log
        _debug_log("H5", "main.py:__main__", "QApplication created")
        # endregion
        # 必須設定，否則 Windows 系統匣不顯示
        if not QSystemTrayIcon.isSystemTrayAvailable():
            pass  # 若無系統匣則不建立 tray，主視窗仍正常
        icon_path = _icon_path()
        if os.path.isfile(icon_path):
            app.setWindowIcon(QIcon(icon_path))
        # region agent log
        _debug_log("H5", "main.py:__main__", "creating LauncherApp")
        # endregion
        window = LauncherApp()
        # region agent log
        _debug_log("H5", "main.py:__main__", "LauncherApp created")
        # endregion
        # region agent log
        _debug_log("H9", "main.py:__main__", "before window.show", {
            "visible": bool(window.isVisible()),
        })
        # endregion
        app.aboutToQuit.connect(lambda: _debug_log("H10", "main.py:__main__", "aboutToQuit emitted"))
        window.show()
        # region agent log
        _debug_log("H9", "main.py:__main__", "after window.show", {
            "visible": bool(window.isVisible()),
            "minimized": bool(window.isMinimized()),
        })
        # endregion
        # region agent log
        _debug_log("H5", "main.py:__main__", "window shown; entering event loop")
        # endregion
        rc = app.exec()
        # region agent log
        _debug_log("H10", "main.py:__main__", "app.exec returned", {"rc": int(rc)})
        # endregion
        sys.exit(rc)
    except Exception as e:
        # region agent log
        _debug_log("H5", "main.py:__main__", "fatal exception during startup", {
            "error": str(e),
            "traceback": traceback.format_exc(),
        })
        # endregion
        raise