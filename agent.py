import sys
import socket
import json
import psutil
import platform
import subprocess
from datetime import datetime
from PyQt5 import QtCore, QtWidgets

# --- CORE LOGIC ---
class AgentCore:
    HOST = '0.0.0.0'
    DEFAULT_PORT = 161 
    BUF_SIZE = 4096

    @staticmethod
    def get_cpu_name():
        try:
            if platform.system() == "Windows":
                command = "wmic cpu get name"
                output = subprocess.check_output(command, shell=True).decode().strip()
                lines = output.split('\n')
                if len(lines) > 1: return lines[1].strip()
            elif platform.system() == "Linux":
                command = "cat /proc/cpuinfo | grep 'model name' | uniq"
                output = subprocess.check_output(command, shell=True).decode().strip()
                return output.split(':')[1].strip()
        except: pass
        return platform.processor()

    @staticmethod
    def get_system_stats(command):
        cmd = command.strip().upper()
        
        # --- CƠ BẢN ---
        if cmd == 'GET ALL':
            return {
                'cpu': psutil.cpu_percent(interval=None), 
                'ram': psutil.virtual_memory().percent
            }
        elif cmd == 'GET CPU':
            return {'cpu': psutil.cpu_percent(interval=None)}
        elif cmd == 'GET RAM':
            return {'ram': psutil.virtual_memory().percent}
        
        # --- THÔNG TIN MÁY ---
        elif cmd == 'GET SYS':
            uname = platform.uname()
            os_name = f"{uname.system} {uname.release} ({uname.machine})"
            cpu_name = AgentCore.get_cpu_name()
            total_ram = round(psutil.virtual_memory().total / (1024**3), 1)
            info = f"\n   ➤ OS: {os_name}\n   ➤ Chip: {cpu_name}\n   ➤ RAM Tổng: {total_ram} GB"
            return {'sys_info': info}
            
        elif cmd == 'GET UPTIME':
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            now = datetime.now()
            uptime = str(now - boot_time).split('.')[0]
            return {'uptime': uptime}

        # --- [MỚI 1] GET PROC (SỐ TIẾN TRÌNH) ---
        elif cmd == 'GET PROC':
            # Đếm số lượng PID (Process ID) đang chạy
            count = len(psutil.pids())
            return {'proc_count': count}

        # --- [MỚI 2] GET BATTERY (PIN) ---
        elif cmd == 'GET BATTERY':
            try:
                batt = psutil.sensors_battery()
                if batt is None:
                    return {'battery': "Không có Pin (Máy bàn)"}
                
                status = "Đang sạc" if batt.power_plugged else "Dùng pin"
                percent = batt.percent
                # Tính thời gian còn lại (nếu đang dùng pin)
                mm, ss = divmod(batt.secsleft, 60)
                hh, mm = divmod(mm, 60)
                time_left = f"{hh}h {mm}m" if batt.secsleft != psutil.POWER_TIME_UNLIMITED else "---"
                
                info = f"{percent}% ({status}) - Còn lại: {time_left}"
                return {'battery': info}
            except:
                return {'error': 'Lỗi đọc Pin'}

        else:
            return {'error': 'Unknown command'}

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
            self.log_signal.emit(f"Server STARTED on port {self.port}")
            self.sock.settimeout(1.0)

            while self.is_running:
                try:
                    data, addr = self.sock.recvfrom(AgentCore.BUF_SIZE)
                    text = data.decode('utf-8', errors='ignore').strip()
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    
                    self.log_signal.emit(f"[{timestamp}] IP {addr[0]}: {text}")
                    
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
            self.log_signal.emit("Server STOPPED.")

    def stop(self):
        self.is_running = False
        self.wait()

# --- GUI ---
class AgentWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SNMP Agent")
        self.resize(450, 350)
        self.server_thread = None
        self.init_ui()

    def init_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        ctrl_layout = QtWidgets.QHBoxLayout()
        ctrl_layout.addWidget(QtWidgets.QLabel("UDP Port:"))
        self.txt_port = QtWidgets.QLineEdit(str(AgentCore.DEFAULT_PORT))
        self.txt_port.setFixedWidth(60)
        ctrl_layout.addWidget(self.txt_port)
        
        self.btn_toggle = QtWidgets.QPushButton("Start Agent")
        self.btn_toggle.clicked.connect(self.toggle_server)
        ctrl_layout.addWidget(self.btn_toggle)
        layout.addLayout(ctrl_layout)

        layout.addWidget(QtWidgets.QLabel("Agent Log:"))
        self.txt_log = QtWidgets.QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        layout.addWidget(self.txt_log)
        
        btn_clear = QtWidgets.QPushButton("Xóa Log")
        btn_clear.clicked.connect(lambda: self.txt_log.clear())
        layout.addWidget(btn_clear)

    def toggle_server(self):
        if self.server_thread is not None:
            self.server_thread.stop()
            self.server_thread = None
            self.btn_toggle.setText("Start Agent")
            self.txt_port.setEnabled(True)
        else:
            try:
                p = int(self.txt_port.text())
                self.server_thread = ServerThread(p)
                self.server_thread.log_signal.connect(self.log)
                self.server_thread.error_signal.connect(self.log)
                self.server_thread.start()
                self.btn_toggle.setText("Stop Agent")
                self.txt_port.setEnabled(False)
            except ValueError:
                QtWidgets.QMessageBox.warning(self, "Lỗi", "Port phải là số.")

    def log(self, msg):
        self.txt_log.appendPlainText(msg)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = AgentWindow()
    win.show()
    sys.exit(app.exec_())