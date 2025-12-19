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