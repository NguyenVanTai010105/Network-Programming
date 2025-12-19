# 📡 Simple SNMP Agent System

## 📖 Mô tả dự án
Dự án **Simple SNMP Agent System** là một hệ thống mô phỏng **SNMP Agent** đơn giản, cho phép thu thập và cung cấp các thông tin cơ bản của hệ thống máy tính như CPU, RAM, dung lượng đĩa và thời gian hệ thống.

Hệ thống hoạt động theo mô hình **Agent – Manager**, trong đó:
- **Agent** chịu trách nhiệm thu thập thông tin hệ thống và lắng nghe yêu cầu từ Manager thông qua giao thức **UDP**.
- **Manager** gửi các yêu cầu truy vấn và hiển thị kết quả nhận được từ Agent.

Dự án nhằm giúp sinh viên hiểu rõ hơn về:
- Nguyên lý hoạt động của SNMP
- Mô hình Agent – Manager
- Lập trình mạng với UDP
- Thu thập thông tin hệ thống

---

## 👥 Danh sách thành viên
- Nguyễn Văn Tài – 3120223173
- Hồ Công Duy - 3120223038
- Nguyễn Lộc Khải-3120223087
- Đặng Bảo Ngọc- 3120223129
- Đặng Duy Khánh-3120223091


---

## 🛠️ Công nghệ sử dụng
- **Ngôn ngữ lập trình:** Python 3
- **Giao thức mạng:** UDP
- **Thư viện:**
  - `socket` – Giao tiếp mạng
  - `psutil` – Thu thập thông tin hệ thống
  - `json` – Định dạng dữ liệu trao đổi
  - `platform` – Lấy thông tin hệ điều hành
  - `subprocess` – Thực thi lệnh hệ thống
  - `PyQt5` – Giao diện người dùng (GUI)

---

## ⚙️ Hướng dẫn cài đặt

### 1️⃣ Yêu cầu hệ thống
- Python **3.8 trở lên**
- Hệ điều hành: Windows / Linux / macOS

### 2️⃣ Cài đặt các thư viện cần thiết
Mở Terminal hoặc Command Prompt và chạy:
```bash
pip install psutil pyqt5
Bước 1: Khởi động SNMP Agent
python agent.py
Bước 2: Chạy SNMP Manager
python manager.py
| Lệnh | Chức năng              |
| ---- | ---------------------- |
| CPU  | Lấy thông tin CPU      |
| RAM  | Lấy dung lượng bộ nhớ  |
| DISK | Lấy dung lượng ổ đĩa   |
| TIME | Lấy thời gian hệ thống |
Demo

Chạy Agent → chạy Manager

Nhập lệnh truy vấn

Nhận kết quả phản hồi từ Agent theo thời gian thực

📄 Ghi chú

Đây là hệ thống SNMP mô phỏng, không thay thế SNMP thực tế.

Dự án phục vụ mục đích học tập và nghiên cứu.