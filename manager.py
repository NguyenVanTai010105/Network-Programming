import sys
import json
import socket
import time
from datetime import datetime
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt

# --- PHẦN 1: CORE LOGIC & MẠNG ---
class ManagerCore:
    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_PORT = 161
    TIMEOUT = 2.0 

    @staticmethod
    def send_request(cmd, host, port, timeout=2.0):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(timeout)
            
            # [BENCHMARK] Bắt đầu bấm giờ
            start_time = time.perf_counter()
            
            s.sendto(cmd.encode('utf-8'), (host, port))
            data, _ = s.recvfrom(4096)
            
            # [BENCHMARK] Kết thúc bấm giờ
            end_time = time.perf_counter()
            s.close()
            
            # Tính độ trễ (Latency)
            latency_ms = (end_time - start_time) * 1000
            
            try: return True, json.loads(data.decode('utf-8')), latency_ms
            except: return True, {'raw': data.decode('utf-8')}, latency_ms
            
        except socket.timeout:
            return False, {'error': 'Timeout'}, 0
        except Exception as e:
            return False, {'error': str(e)}, 0

class NetWorker(QtCore.QRunnable):
    def __init__(self, cmd, host, port, signal_emitter):
        super().__init__()
        self.cmd, self.host, self.port, self.emitter = cmd, host, port, signal_emitter

    def run(self):
        ok, data, _ = ManagerCore.send_request(self.cmd, self.host, self.port)
        self.emitter.emit((self.cmd, ok, data))

# --- [ĐIỂM THƯỞNG] CLASS XỬ LÝ CONCURRENCY & BENCHMARK ---
class BenchmarkWorker(QtCore.QThread):
    progress_signal = QtCore.pyqtSignal(int)
    result_signal = QtCore.pyqtSignal(dict)
    
    def __init__(self, host, port, total_requests):
        super().__init__()
        self.host = host
        self.port = port
        self.total = total_requests

    def run(self):
        success = 0; failed = 0; total_latency = 0
        start_total = time.perf_counter()

        for i in range(self.total):
            ok, _, lat = ManagerCore.send_request("GET ALL", self.host, self.port, timeout=0.5)
            if ok:
                success += 1; total_latency += lat
            else:
                failed += 1
            self.progress_signal.emit(int((i + 1) / self.total * 100))

        duration = time.perf_counter() - start_total
        rps = success / duration if duration > 0 else 0     
        avg_lat = total_latency / success if success > 0 else 0 
        
        self.result_signal.emit({
            "total": self.total, "success": success, "failed": failed,
            "duration": duration, "rps": rps, "avg_lat": avg_lat
        })

# --- PHẦN 2: WIDGET ĐỒNG HỒ TRÒN ---
class CircularProgress(QtWidgets.QWidget):
    def __init__(self, title, color_hex, parent=None):
        super().__init__(parent)
        self.value = 0; self.title = title; self.color = QtGui.QColor(color_hex)
        self.setMinimumSize(160, 160)

    def set_value(self, val):
        self.value = val; self.repaint()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height()
        size = min(w, h) - 30 
        rect = QtCore.QRectF((w - size)/2, (h - size)/2, size, size)
        
        pen_border = QtGui.QPen(QtGui.QColor("#95a5a6")); pen_border.setWidth(1)
        painter.setPen(pen_border); painter.drawEllipse(rect.adjusted(-8, -8, 8, 8))
        
        pen_bg = QtGui.QPen(QtGui.QColor("#bdc3c7")); pen_bg.setWidth(12); pen_bg.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_bg); painter.drawEllipse(rect)

        use_color = self.color
        if self.value > 90: use_color = QtGui.QColor("#c0392b") 
        elif self.value > 75: use_color = QtGui.QColor("#f39c12")

        pen_val = QtGui.QPen(use_color); pen_val.setWidth(12); pen_val.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_val); painter.drawArc(rect, 90 * 16, int(-self.value * 3.6 * 16))

        painter.setPen(QtGui.QColor("#2c3e50")); painter.setFont(QtGui.QFont("Segoe UI", 20, QtGui.QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, f"{int(self.value)}%")
        painter.setFont(QtGui.QFont("Segoe UI", 10))
        rect_title = QtCore.QRectF(rect.x(), rect.y() + 35, rect.width(), rect.height())
        painter.drawText(rect_title, Qt.AlignCenter, self.title)

# --- PHẦN 3: GUI MANAGER CHÍNH ---
class ManagerWindow(QtWidgets.QMainWindow):
    signal_result = QtCore.pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SNMP Manager")
        self.resize(500, 750)
        self.pool = QtCore.QThreadPool()
        self.signal_result.connect(self.handle_result)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(lambda: self.send_cmd("GET ALL"))
        self.is_alert_open = False
        self.init_ui()

    def init_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(10); layout.setContentsMargins(15, 15, 15, 15)

        # 1. KẾT NỐI
        conn_group = QtWidgets.QGroupBox("1. CẤU HÌNH AGENT")
        conn_layout = QtWidgets.QHBoxLayout()
        conn_layout.addWidget(QtWidgets.QLabel("IP:"))
        self.txt_host = QtWidgets.QLineEdit(ManagerCore.DEFAULT_HOST)
        conn_layout.addWidget(self.txt_host)
        conn_layout.addWidget(QtWidgets.QLabel("Port:"))
        self.txt_port = QtWidgets.QLineEdit(str(ManagerCore.DEFAULT_PORT))
        self.txt_port.setFixedWidth(50)
        conn_layout.addWidget(self.txt_port)
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)

        # 2. DASHBOARD
        mon_group = QtWidgets.QGroupBox("2. GIÁM SÁT TRỰC QUAN")
        mon_layout = QtWidgets.QHBoxLayout()
        self.gauge_cpu = CircularProgress("CPU", "#27ae60")
        mon_layout.addWidget(self.gauge_cpu)
        self.gauge_ram = CircularProgress("RAM", "#2980b9")
        mon_layout.addWidget(self.gauge_ram)
        mon_group.setLayout(mon_layout)
        layout.addWidget(mon_group)

        # 3. ĐIỀU KHIỂN
        ctrl_group = QtWidgets.QGroupBox("3. BẢNG ĐIỀU KHIỂN")
        ctrl_layout = QtWidgets.QVBoxLayout()
        
        # Hàng 1
        row1 = QtWidgets.QHBoxLayout()
        self.btn_get_all = QtWidgets.QPushButton("GET ALL")
        self.btn_get_all.clicked.connect(lambda: self.send_cmd("GET ALL"))
        row1.addWidget(self.btn_get_all)

        self.btn_get_cpu = QtWidgets.QPushButton("GET CPU")
        self.btn_get_cpu.clicked.connect(lambda: self.send_cmd("GET CPU"))
        row1.addWidget(self.btn_get_cpu)

        self.btn_get_ram = QtWidgets.QPushButton("GET RAM")
        self.btn_get_ram.clicked.connect(lambda: self.send_cmd("GET RAM"))
        row1.addWidget(self.btn_get_ram)
        ctrl_layout.addLayout(row1)

        # Hàng 2
        row2 = QtWidgets.QHBoxLayout()
        self.btn_sys = QtWidgets.QPushButton("SYS INFO")
        self.btn_sys.clicked.connect(lambda: self.send_cmd("GET SYS"))
        row2.addWidget(self.btn_sys)

        self.btn_uptime = QtWidgets.QPushButton("UPTIME")
        self.btn_uptime.clicked.connect(lambda: self.send_cmd("GET UPTIME"))
        row2.addWidget(self.btn_uptime)
        ctrl_layout.addLayout(row2)

        # Hàng 3
        row3 = QtWidgets.QHBoxLayout()
        self.btn_proc = QtWidgets.QPushButton("PROCESSES")
        self.btn_proc.clicked.connect(lambda: self.send_cmd("GET PROC"))
        row3.addWidget(self.btn_proc)

        self.btn_batt = QtWidgets.QPushButton("BATTERY")
        self.btn_batt.clicked.connect(lambda: self.send_cmd("GET BATTERY"))
        row3.addWidget(self.btn_batt)
        ctrl_layout.addLayout(row3)

        # Hàng 4 
        row4 = QtWidgets.QHBoxLayout()
        row4.addWidget(QtWidgets.QLabel("Chu kì (s):"))
        self.spin_interval = QtWidgets.QSpinBox()
        self.spin_interval.setRange(1, 60); self.spin_interval.setValue(1); self.spin_interval.setFixedWidth(50)
        row4.addWidget(self.spin_interval)
        self.btn_auto = QtWidgets.QPushButton("Bật Tự Động")
        self.btn_auto.setCheckable(True)
        self.btn_auto.toggled.connect(self.toggle_auto)
        row4.addWidget(self.btn_auto)
        
        ctrl_layout.addLayout(row4)

        ctrl_group.setLayout(ctrl_layout)
        layout.addWidget(ctrl_group)

        # 4. BENCHMARK
        bench_group = QtWidgets.QGroupBox("4. ĐO LƯỜNG HIỆU NĂNG (BENCHMARK)")
        bench_layout = QtWidgets.QVBoxLayout()
        b_row = QtWidgets.QHBoxLayout()
        b_row.addWidget(QtWidgets.QLabel("Gói tin:"))
        self.spin_bench = QtWidgets.QSpinBox()
        self.spin_bench.setRange(50, 50000); self.spin_bench.setValue(100); self.spin_bench.setFixedWidth(80)
        b_row.addWidget(self.spin_bench)
        self.btn_bench = QtWidgets.QPushButton("CHẠY STRESS TEST")
        self.btn_bench.clicked.connect(self.run_benchmark)
        b_row.addWidget(self.btn_bench)
        bench_layout.addLayout(b_row)
        self.progress_bench = QtWidgets.QProgressBar(); self.progress_bench.setValue(0); self.progress_bench.setTextVisible(False)
        bench_layout.addWidget(self.progress_bench)
        bench_group.setLayout(bench_layout)
        layout.addWidget(bench_group)

        # 5. LOG
        layout.addWidget(QtWidgets.QLabel("Nhật ký hệ thống:"))
        self.txt_log = QtWidgets.QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        layout.addWidget(self.txt_log)

    def toggle_auto(self, active):
        if active:
            s = self.spin_interval.value()
            self.timer.start(s * 1000)
            self.btn_auto.setText(f"Dừng ({s}s)")
            self.set_controls_enabled(False)
        else:
            self.timer.stop()
            self.btn_auto.setText("Bật Tự Động")
            self.set_controls_enabled(True)

    def set_controls_enabled(self, enable):
        self.txt_host.setEnabled(enable); self.txt_port.setEnabled(enable)
        self.spin_interval.setEnabled(enable); self.btn_get_all.setEnabled(enable)
        self.btn_get_cpu.setEnabled(enable); self.btn_get_ram.setEnabled(enable)
        self.btn_bench.setEnabled(enable)

    def send_cmd(self, cmd):
        h = self.txt_host.text()
        try: p = int(self.txt_port.text())
        except: return
        self.pool.start(NetWorker(cmd, h, p, self.signal_result))

    def handle_result(self, res):
        cmd, ok, data = res
        t = datetime.now().strftime("%H:%M:%S")
        if not ok:
            self.txt_log.appendPlainText(f"[{t}] Lỗi: {data.get('error')}")
            return

        cpu, ram = data.get('cpu'), data.get('ram')
        log = f"[{t}] {cmd} =>"
        
        # CPU/RAM
        if cpu is not None: self.gauge_cpu.set_value(cpu); log += f" CPU:{cpu}%"
        if ram is not None: self.gauge_ram.set_value(ram); log += f" RAM:{ram}%"
        
        # Info khác
        if data.get('sys_info'): log += f" Hệ thống: {data.get('sys_info')}"
        if data.get('uptime'): log += f" Uptime: {data.get('uptime')}"
        if data.get('proc_count'): log += f" Processes: {data.get('proc_count')}"
        if data.get('battery'): log += f" Pin: {data.get('battery')}"

        if cpu is not None and ram is not None and cpu > 90 and ram > 90:
            if not self.is_alert_open:
                self.is_alert_open = True
                QtWidgets.QMessageBox.critical(self, "CẢNH BÁO", f"QUÁ TẢI!\nCPU: {cpu}% - RAM: {ram}%")
                self.is_alert_open = False
        
        self.txt_log.appendPlainText(log)

    def run_benchmark(self):
        count = self.spin_bench.value()
        h = self.txt_host.text()
        try: p = int(self.txt_port.text())
        except: return
        
        self.set_controls_enabled(False); self.btn_auto.setEnabled(False)
        self.txt_log.appendPlainText(f"\n--- BẮT ĐẦU ĐO HIỆU NĂNG ({count} gói) ---")
        
        self.worker_bench = BenchmarkWorker(h, p, count)
        self.worker_bench.progress_signal.connect(self.progress_bench.setValue)
        self.worker_bench.result_signal.connect(self.show_bench_result)
        self.worker_bench.start()

    def show_bench_result(self, res):
        self.set_controls_enabled(True); self.btn_auto.setEnabled(True)
        self.progress_bench.setValue(100)
        
        msg = (f"=== KẾT QUẢ ĐO LƯỜNG ===\n"
               f"• Tổng số yêu cầu: {res['total']} gói\n"
               f"• Thành công: {res['success']} gói\n"
               f"• Thất bại: {res['failed']} gói\n"
               f"• Thời gian thực thi: {res['duration']:.4f} giây\n"
               f"----------------------------------------\n"
               f"🚀 Tốc độ xử lý (Throughput/RPS): {res['rps']:.2f} req/s\n"
               f"⏱️ Độ trễ trung bình (Latency): {res['avg_lat']:.4f} ms")
        
        self.txt_log.appendPlainText(msg + "\n----------------------------------------")
        QtWidgets.QMessageBox.information(self, "Kết quả Benchmark", msg)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = ManagerWindow()
    win.show()
    sys.exit(app.exec_())