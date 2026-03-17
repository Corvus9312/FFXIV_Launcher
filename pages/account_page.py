import os
import cv2
import json
import base64
import main
import numpy as np
from urllib.parse import urlparse, parse_qs
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QFileDialog, QMessageBox)

class AccountPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.temp_secret = ""
        
        layout = QVBoxLayout(self)

        self.acc_input = QLineEdit(placeholderText="帳號")
        self.pwd_input = QLineEdit(placeholderText="密碼")
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.qr_btn = QPushButton("上傳 QR Code (Google Authenticator)")
        self.qr_btn.clicked.connect(self.scan_qr)
        
        self.status_label = QLabel("狀態: 尚未綁定 OTP")
        
        self.save_btn = QPushButton("儲存並返回")
        self.save_btn.clicked.connect(self.save_data)
        self.save_btn.setEnabled(False)

        layout.addWidget(QLabel("新增帳號設定"))
        layout.addWidget(self.acc_input)
        layout.addWidget(self.pwd_input)
        layout.addWidget(self.qr_btn)
        layout.addWidget(self.status_label)
        layout.addWidget(self.save_btn)
        
        back_btn = QPushButton("取消")
        back_btn.clicked.connect(lambda: self.controller.stack.setCurrentIndex(0))
        layout.addWidget(back_btn)

    def scan_qr(self):
        path, _ = QFileDialog.getOpenFileName(self, "選擇圖片", "", "Images (*.png *.jpg *.jpeg)")
        if not path: return

        img = self._imread_unicode(path)
        if img is None:
            QMessageBox.warning(self, "錯誤", "無法讀取圖片檔案（可能是路徑含特殊字元、檔案不存在或損毀）。")
            return

        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(img)

        if not data:
            QMessageBox.warning(self, "錯誤", "無法辨識 QR Code")
            return

        # --- 處理 Google 匯出格式 (otpauth-migration) ---
        if data.startswith("otpauth-migration://"):
            try:
                query = parse_qs(urlparse(data).query)
                encoded_data = query.get('data', [None])[0]
                if not encoded_data:
                    raise ValueError("找不到 data 參數")

                decoded_bytes = base64.b64decode(encoded_data)
                secret_bytes = self.extract_google_secret(decoded_bytes)
                
                if secret_bytes:
                    self.temp_secret = base64.b32encode(secret_bytes).decode('utf-8').strip('=')
                    self.status_label.setText("狀態: 成功解析 Google Migration 密鑰")
                    self.status_label.setStyleSheet("color: green;")
                    self.save_btn.setEnabled(True)
                else:
                    QMessageBox.critical(self, "失敗", "無法從 Migration 格式提取密鑰")

            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"解析 Google 格式失敗: {str(e)}")

        # --- 處理標準格式 (otpauth://) ---
        elif "secret=" in data:
            self.temp_secret = data.split("secret=")[1].split("&")[0].upper()
            self.status_label.setText("狀態: 成功取得標準密鑰")
            self.status_label.setStyleSheet("color: green;")
            self.save_btn.setEnabled(True)

    def extract_google_secret(self, raw_bytes):
        try:
            if raw_bytes[0] == 0x0a:
                payload_len = raw_bytes[1]
                payload = raw_bytes[2:2+payload_len]
                if payload[0] == 0x0a:
                    secret_len = payload[1]
                    return payload[2:2+secret_len]
        except:
            return None
        return None

    def _imread_unicode(self, path: str):
        """
        Windows 上 cv2.imread 對含 Unicode/特殊字元路徑可能失敗；
        改用 numpy fromfile + cv2.imdecode 以支援完整路徑。
        """
        try:
            if not os.path.exists(path):
                return None
            buf = np.fromfile(path, dtype=np.uint8)
            if buf.size == 0:
                return None
            img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            return img
        except Exception:
            return None

    def save_data(self):
        acc = self.acc_input.text()
        pwd = self.pwd_input.text()
        if not acc or not pwd or not self.temp_secret: 
            return
        
        data = {}
        if os.path.exists(main.CONFIG_PATH):
            with open(main.CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        if 'accounts' not in data: data['accounts'] = {}
        
        data['accounts'][acc] = {
            "username": acc,
            "password": pwd,
            "otp_secret": self.temp_secret
        }
        
        with open(main.CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        self.controller.update_list()
        self.controller.stack.setCurrentIndex(0)
