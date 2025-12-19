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