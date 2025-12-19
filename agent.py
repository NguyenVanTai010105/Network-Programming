import sys
import socket
import json
import psutil
from datetime import datetime
from PyQt5 import QtCore, QtGui, QtWidgets

# ==========================================
# PHẦN 1: CORE LOGIC
# ==========================================
class AgentCore:
    HOST = '0.0.0.0'       
    DEFAULT_PORT = 161    
    BUF_SIZE = 4096

    @staticmethod
    def get_system_stats(command):
        cmd = command.strip().upper()
        if cmd == 'GET ALL':
            return {
                'cpu': psutil.cpu_percent(interval=None), 
                'mem': psutil.virtual_memory().percent
            }
        elif cmd == 'GET CPU':
            return {'cpu': psutil.cpu_percent(interval=None)}
        elif cmd == 'GET MEM':
            return {'mem': psutil.virtual_memory().percent}
        else:
            return {'error': 'Unknown command'}

    @staticmethod
    def get_local_ip_address():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

class ServerThread(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)
    error_signal = QtCore.pyqtSignal(str)

    def __init__(self, port):
        super().__init__()
        self.port = port
        self.is_running = True
        self.sock = None

    def run(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((AgentCore.HOST, self.port))
            self.log_signal.emit(f"✅ Server STARTED listening on port {self.port}")
            self.sock.settimeout(1.0)

            while self.is_running:
                try:
                    data, addr = self.sock.recvfrom(AgentCore.BUF_SIZE)
                    text = data.decode('utf-8', errors='ignore').strip()
                    
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    
                    # --- ĐÃ XÓA EMOJI Ở DÒNG DƯỚI ĐÂY ---
                    self.log_signal.emit(f"[{timestamp}] From {addr[0]}: {text}")
                    
                    response_data = AgentCore.get_system_stats(text)
                    response_json = json.dumps(response_data)
                    self.sock.sendto(response_json.encode('utf-8'), addr)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    self.error_signal.emit(f"Socket Error: {e}")

        except Exception as e:
            self.error_signal.emit(f"Start Error: {e}")
        finally:
            if self.sock: self.sock.close()
            self.log_signal.emit("🛑 Server STOPPED.")

    def stop(self):
        self.is_running = False
        self.wait()


THEME = {
    "bg_main": "#f4f6f9", "bg_card": "#ffffff", "border_card": "#e1e4e8",
    "text_main": "#2c3e50", "text_dim": "#7f8c8d",
    "btn_bg": "#ffffff", "btn_border": "#d1d5db", "btn_text": "#374151", "btn_hover": "#f3f4f6",
    "success": "#27ae60", "danger": "#c0392b", "highlight": "#2980b9"
}

STYLESHEET = f"""
QMainWindow {{ background-color: {THEME['bg_main']}; }}
QWidget {{ font-family: 'Segoe UI', sans-serif; color: {THEME['text_main']}; }}
QFrame.Card {{ background-color: {THEME['bg_card']}; border-radius: 12px; border: 1px solid {THEME['border_card']}; }}
QLineEdit {{ background-color: #ffffff; border: 1px solid {THEME['btn_border']}; border-radius: 6px; padding: 6px; }}
QPushButton {{ background-color: {THEME['btn_bg']}; border: 1px solid {THEME['btn_border']}; border-radius: 6px; color: {THEME['btn_text']}; padding: 8px 15px; font-weight: 600; }}
QPushButton:hover {{ background-color: {THEME['btn_hover']}; }}
QPlainTextEdit {{ background-color: transparent; border: none; font-family: 'Consolas', monospace; font-size: 13px; color: {THEME['text_main']}; }}
"""

class AgentWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SNMP Agent")
        self.resize(500, 500)
        self.setStyleSheet(STYLESHEET)
        self.server_thread = None
        self.init_ui()

    def init_ui(self):
        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central); layout.setSpacing(15); layout.setContentsMargins(20,20,20,20)

        # --- HEADER ---
        head_frame = QtWidgets.QFrame(); head_frame.setProperty("class", "Card")
        head_layout = QtWidgets.QVBoxLayout(head_frame); head_layout.setContentsMargins(20,20,20,20)
        
        head_layout.addSpacing(15)

        ctrl_layout = QtWidgets.QHBoxLayout()
        ctrl_layout.addWidget(QtWidgets.QLabel("Port:"))
        self.txt_port = QtWidgets.QLineEdit(str(AgentCore.DEFAULT_PORT)); self.txt_port.setFixedWidth(60); self.txt_port.setAlignment(QtCore.Qt.AlignCenter)
        ctrl_layout.addWidget(self.txt_port)
        
        self.btn_toggle = QtWidgets.QPushButton("START SERVER")
        self.btn_toggle.setStyleSheet(f"background-color: {THEME['success']}; color: white; border: none;")
        self.btn_toggle.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_toggle.clicked.connect(self.toggle_server)
        ctrl_layout.addWidget(self.btn_toggle)
        
        head_layout.addLayout(ctrl_layout)
        layout.addWidget(head_frame)

        # --- LOG ---
        log_frame = QtWidgets.QFrame(); log_frame.setProperty("class", "Card")
        l_layout = QtWidgets.QVBoxLayout(log_frame); l_layout.setContentsMargins(15,15,15,15)
        
        top_log = QtWidgets.QHBoxLayout()
        lbl_log = QtWidgets.QLabel("Request Logs")
        lbl_log.setStyleSheet(f"font-weight: bold; color: {THEME['text_dim']};")
        top_log.addWidget(lbl_log)
        
        btn_clear = QtWidgets.QPushButton("Clear")
        btn_clear.setFixedSize(60, 25); btn_clear.setStyleSheet("font-size: 11px; padding: 2px;")
        btn_clear.clicked.connect(lambda: self.txt_log.clear())
        top_log.addWidget(btn_clear)
        
        l_layout.addLayout(top_log)
        self.txt_log = QtWidgets.QPlainTextEdit(); self.txt_log.setReadOnly(True)
        self.txt_log.setPlaceholderText("Waiting for connection from Manager...")
        l_layout.addWidget(self.txt_log)
        layout.addWidget(log_frame, stretch=1)

    def toggle_server(self):
        if self.server_thread is not None:
            self.server_thread.stop()
            self.server_thread = None
            self.btn_toggle.setText("START SERVER"); self.btn_toggle.setStyleSheet(f"background-color: {THEME['success']}; color: white;")
            self.txt_port.setEnabled(True)
        else:
            try:
                p = int(self.txt_port.text())
                self.server_thread = ServerThread(p)
                self.server_thread.log_signal.connect(self.log)
                self.server_thread.error_signal.connect(self.log_err)
                self.server_thread.start()
                self.btn_toggle.setText("STOP SERVER"); self.btn_toggle.setStyleSheet(f"background-color: {THEME['danger']}; color: white;")
                self.txt_port.setEnabled(False)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Invalid Port: {str(e)}")

    def log(self, msg):
        self.txt_log.appendPlainText(msg)
        self.txt_log.verticalScrollBar().setValue(self.txt_log.verticalScrollBar().maximum())

    def log_err(self, msg):
        self.txt_log.appendHtml(f"<font color='#c0392b'><b>[ERROR]</b> {msg}</font>")

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    font = QtGui.QFont("Segoe UI", 10); app.setFont(font)
    win = AgentWindow(); win.show()
    sys.exit(app.exec_())