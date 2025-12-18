import sys
import json
import socket
import numpy as np
from scipy.interpolate import make_interp_spline
from collections import deque
from datetime import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ==========================================
# PHẦN 1: CORE LOGIC
# ==========================================
class ManagerCore:
    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_PORT = 161
    TIMEOUT = 2.0
    ALERT_CPU = 40.0
    ALERT_MEM = 85.0

    @staticmethod
    def send_request(cmd, host, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(ManagerCore.TIMEOUT)
            s.sendto(cmd.encode('utf-8'), (host, port))
            data, _ = s.recvfrom(4096)
            try: return True, json.loads(data.decode('utf-8'))
            except: return True, {'raw': data.decode('utf-8')}
        except socket.timeout:
            return False, {'error': 'Timeout (Agent not responding)'}
        except Exception as e:
            return False, {'error': str(e)}
        finally:
            s.close()

    @staticmethod
    def check_alert(cpu_val, mem_val):
        if cpu_val is not None and mem_val is not None:
            if cpu_val > ManagerCore.ALERT_CPU and mem_val > ManagerCore.ALERT_MEM:
                return True
        return False

class NetWorker(QtCore.QRunnable):
    def __init__(self, cmd, host, port, signal_emitter):
        super().__init__()
        self.cmd, self.host, self.port, self.emitter = cmd, host, port, signal_emitter

    def run(self):
        ok, data = ManagerCore.send_request(self.cmd, self.host, self.port)
        self.emitter.emit((self.cmd, ok, data))

# ==========================================
# PHẦN 2: GUI
# ==========================================
THEME = {
    "bg_main": "#f4f6f9", "bg_card": "#ffffff", "border_card": "#e1e4e8",
    "cpu_color": "#2980b9", "mem_color": "#e74c3c", 
    "text_main": "#2c3e50", "text_dim": "#7f8c8d", "grid_color": "#ecf0f1",
    "btn_bg": "#ffffff", "btn_border": "#d1d5db", "btn_text": "#374151", "btn_hover": "#f3f4f6"
}

STYLESHEET = f"""
QMainWindow {{ background-color: {THEME['bg_main']}; }}
QWidget {{ font-family: 'Segoe UI', sans-serif; color: {THEME['text_main']}; }}
QFrame.Card {{ background-color: {THEME['bg_card']}; border-radius: 12px; border: 1px solid {THEME['border_card']}; }}
QLineEdit, QSpinBox {{ background-color: #ffffff; border: 1px solid {THEME['btn_border']}; border-radius: 6px; padding: 6px; }}
QPushButton {{ background-color: {THEME['btn_bg']}; border: 1px solid {THEME['btn_border']}; border-radius: 6px; color: {THEME['btn_text']}; padding: 6px 15px; font-weight: 600; }}
QPushButton:hover {{ background-color: {THEME['btn_hover']}; border-color: #9ca3af; }}
QPushButton:checked {{ background-color: {THEME['cpu_color']}; color: white; border: none; }}
QPlainTextEdit {{ background: transparent; border: none; font-family: 'Consolas'; font-size: 12px; color: {THEME['text_dim']}; }}
QMessageBox {{ background-color: #ffffff; }}
QMessageBox QLabel {{ color: {THEME['text_main']}; }}
"""

class StatCard(QtWidgets.QFrame):
    def __init__(self, title, color, icon, parent=None):
        super().__init__(parent)
        self.setProperty("class", "Card")
        l = QtWidgets.QVBoxLayout(self); l.setContentsMargins(20, 20, 20, 20)
        top = QtWidgets.QHBoxLayout()
        t = QtWidgets.QLabel(f"{icon}  {title}")
        t.setStyleSheet(f"color: {THEME['text_dim']}; font-weight: bold; font-size: 13px; text-transform: uppercase;")
        top.addWidget(t); top.addStretch(); l.addLayout(top); l.addSpacing(10)
        self.val = QtWidgets.QLabel("0.0%"); self.val.setStyleSheet(f"font-size: 38px; font-weight: 800; color: {color};"); l.addWidget(self.val)
        self.bar = QtWidgets.QProgressBar(); self.bar.setFixedHeight(6); self.bar.setTextVisible(False)
        self.bar.setStyleSheet(f"QProgressBar {{ background: #ecf0f1; border-radius: 3px; }} QProgressBar::chunk {{ background: {color}; border-radius: 3px; }}")
        self.bar.setRange(0, 100); self.bar.setValue(0); l.addSpacing(10); l.addWidget(self.bar)
    def update_value(self, value): self.val.setText(f"{value}%"); self.bar.setValue(int(value))

class CleanChartCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure(figsize=(6, 4), dpi=100, tight_layout=True)
        fig.patch.set_facecolor(THEME['bg_card']) 
        self.ax = fig.add_subplot(111); self.ax.set_facecolor(THEME['bg_card'])   
        self.ax.tick_params(axis='x', colors=THEME['text_dim'], labelsize=9)
        self.ax.tick_params(axis='y', colors=THEME['text_dim'], labelsize=9)
        self.ax.spines['top'].set_visible(False); self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_color(THEME['border_card']); self.ax.spines['left'].set_color(THEME['border_card'])
        fig.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.1)
        super().__init__(fig); self.setParent(parent)

    def plot(self, cpu_data, mem_data):
        self.ax.clear(); self.ax.grid(True, linestyle=':', color=THEME['grid_color'], linewidth=1)
        self.ax.set_ylim(0, 100); self.ax.set_xlim(0, 49)
        def get_smooth(data):
            if len(data) < 4: return range(len(data)), data
            x = np.arange(len(data)); x_new = np.linspace(x.min(), x.max(), 300)
            try: spl = make_interp_spline(x, data, k=3); return x_new, np.clip(spl(x_new), 0, 100)
            except: return x, data
        xc, yc = get_smooth(cpu_data); self.ax.plot(xc, yc, color=THEME['cpu_color'], linewidth=2, label="CPU"); self.ax.fill_between(xc, yc, 0, color=THEME['cpu_color'], alpha=0.1)
        xm, ym = get_smooth(mem_data); self.ax.plot(xm, ym, color=THEME['mem_color'], linewidth=2, label="RAM")
        leg = self.ax.legend(loc='upper left', frameon=False, fontsize=9); 
        for text in leg.get_texts(): text.set_color(THEME['text_main'])
        self.draw()

class MainWindow(QtWidgets.QMainWindow):
    signal_result = QtCore.pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SNMP Manager")
        self.resize(1100, 700)
        self.setStyleSheet(STYLESHEET)
        
        self.len_data = 50
        self.data_cpu = deque([0]*self.len_data, maxlen=self.len_data)
        self.data_mem = deque([0]*self.len_data, maxlen=self.len_data)
        
        self.pool = QtCore.QThreadPool()
        self.signal_result.connect(self.handle_result)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(lambda: self.send_cmd("GET ALL"))

        self.setup_ui()

    def setup_ui(self):
        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central); layout.setSpacing(20); layout.setContentsMargins(25, 25, 25, 25)

        # Header
        header = QtWidgets.QFrame(); header.setProperty("class", "Card")
        h_layout = QtWidgets.QHBoxLayout(header); h_layout.setContentsMargins(15, 12, 15, 12); h_layout.setSpacing(15)
        h_layout.addWidget(QtWidgets.QLabel("Host:")); self.txt_host = QtWidgets.QLineEdit(ManagerCore.DEFAULT_HOST); self.txt_host.setFixedWidth(100); h_layout.addWidget(self.txt_host)
        h_layout.addWidget(QtWidgets.QLabel("Port:")); self.txt_port = QtWidgets.QLineEdit(str(ManagerCore.DEFAULT_PORT)); self.txt_port.setFixedWidth(50); h_layout.addWidget(self.txt_port)
        h_layout.addWidget(QtWidgets.QLabel("Poll(s):")); self.spin_poll = QtWidgets.QSpinBox(); self.spin_poll.setRange(1, 60); self.spin_poll.setValue(1); self.spin_poll.setFixedWidth(50); h_layout.addWidget(self.spin_poll)
        
        self.btn_auto = QtWidgets.QPushButton("▶ Start Auto"); self.btn_auto.setCheckable(True); self.btn_auto.toggled.connect(self.toggle_auto); h_layout.addWidget(self.btn_auto)
        h_layout.addStretch()
        self.btn_all = QtWidgets.QPushButton("Get All"); self.btn_all.clicked.connect(lambda: self.send_cmd("GET ALL")); h_layout.addWidget(self.btn_all)
        self.btn_cpu = QtWidgets.QPushButton("Get CPU"); self.btn_cpu.clicked.connect(lambda: self.send_cmd("GET CPU")); h_layout.addWidget(self.btn_cpu)
        self.btn_mem = QtWidgets.QPushButton("Get RAM"); self.btn_mem.clicked.connect(lambda: self.send_cmd("GET MEM")); h_layout.addWidget(self.btn_mem)
        layout.addWidget(header)

        # Cards
        stats_layout = QtWidgets.QHBoxLayout(); stats_layout.setSpacing(20)
        self.card_cpu = StatCard("CPU Load", THEME['cpu_color'], "⚡"); stats_layout.addWidget(self.card_cpu)
        self.card_mem = StatCard("Memory Usage", THEME['mem_color'], "🧠"); stats_layout.addWidget(self.card_mem)
        layout.addLayout(stats_layout)

        # Chart & Log
        body_split = QtWidgets.QSplitter(QtCore.Qt.Horizontal); body_split.setHandleWidth(10)
        chart_frame = QtWidgets.QFrame(); chart_frame.setProperty("class", "Card")
        c_layout = QtWidgets.QVBoxLayout(chart_frame); c_layout.setContentsMargins(0, 0, 0, 0)
        lbl_chart = QtWidgets.QLabel("  Real-time Analytics"); lbl_chart.setStyleSheet(f"font-weight: bold; color: {THEME['text_dim']}; margin-top: 10px; margin-left: 5px;"); c_layout.addWidget(lbl_chart)
        self.chart = CleanChartCanvas(self); c_layout.addWidget(self.chart); body_split.addWidget(chart_frame)

        log_frame = QtWidgets.QFrame(); log_frame.setProperty("class", "Card")
        l_layout = QtWidgets.QVBoxLayout(log_frame); l_layout.setContentsMargins(15, 15, 15, 15)
        l_layout.addWidget(QtWidgets.QLabel("System Logs")); self.txt_log = QtWidgets.QPlainTextEdit(); self.txt_log.setReadOnly(True); l_layout.addWidget(self.txt_log); body_split.addWidget(log_frame)
        
        body_split.setSizes([750, 300]); body_split.setCollapsible(0, False); layout.addWidget(body_split, stretch=1)
        self.chart.plot([], [])

    def log(self, text):
        t = datetime.now().strftime("%H:%M:%S")
        self.txt_log.appendPlainText(f"[{t}] {text}")
        self.txt_log.verticalScrollBar().setValue(self.txt_log.verticalScrollBar().maximum())

    def toggle_auto(self, active):
        if active:
            ms = self.spin_poll.value() * 1000; self.timer.start(ms); self.btn_auto.setText("⏹ Stop Auto")
            self.txt_host.setDisabled(True); self.txt_port.setDisabled(True); self.spin_poll.setDisabled(True)
        else:
            self.timer.stop(); self.btn_auto.setText("▶ Start Auto")
            self.txt_host.setDisabled(False); self.txt_port.setDisabled(False); self.spin_poll.setDisabled(False)

    def send_cmd(self, cmd):
        h = self.txt_host.text()
        try: p = int(self.txt_port.text())
        except: return
        worker = NetWorker(cmd, h, p, self.signal_result)
        self.pool.start(worker)

    def handle_result(self, res):
        cmd, ok, data = res
        if not ok: self.log(f"Error: {data.get('error')}"); return

        c = data.get('cpu')
        m = data.get('mem')
        
        last_c = self.data_cpu[-1] if self.data_cpu else 0
        last_m = self.data_mem[-1] if self.data_mem else 0
        val_c = float(c) if c is not None else last_c
        val_m = float(m) if m is not None else last_m
        
        self.data_cpu.append(val_c); self.data_mem.append(val_m)
        
        log_msg = f"{cmd} OK"
        if c is not None: self.card_cpu.update_value(val_c); log_msg += f" | CPU: {val_c}%"
        if m is not None: self.card_mem.update_value(val_m); log_msg += f" | MEM: {val_m}%"
            
        self.log(log_msg)
        self.chart.plot(list(self.data_cpu), list(self.data_mem))
        
        if ManagerCore.check_alert(c, m):
            self.show_alert(val_c, val_m)

    # --- HÀM SHOW_ALERT ĐÃ ĐƯỢC CẬP NHẬT ---
    def show_alert(self, c, m):
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("⚠️ CẢNH BÁO TÀI NGUYÊN")
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        
        # Tiêu đề lớn màu đỏ
        msg.setText("<h3><font color='#e74c3c'>HỆ THỐNG ĐANG QUÁ TẢI!</font></h3>")
        
        # Nội dung chi tiết với định dạng HTML
        details = (
            f"<b>Thông số hiện tại:</b><br>"
            f"CPU: <font color='#d35400'><b>{c}%</b></font> | "
            f"RAM: <font color='#d35400'><b>{m}%</b></font><br><br>"
            f"<b>⚠️ Hành động khuyến nghị:</b>"
            f"<ul>"
            f"<li>Tắt ngay các ứng dụng nặng (Game, Render).</li>"
            f"<li>Kiểm tra các tab trình duyệt web đang mở.</li>"
            f"<li>Lưu lại công việc quan trọng để tránh mất dữ liệu.</li>"
            f"<li>Kiểm tra các tiến trình lạ trong Task Manager.</li>"
            f"</ul>"
        )
        msg.setInformativeText(details)
        msg.exec_()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    font = QtGui.QFont("Segoe UI", 10); app.setFont(font)
    win = MainWindow(); win.show()
    sys.exit(app.exec_())