# Medical AI - Website Chatbox AI Hỗ Trợ Đặt Lịch Khám & Tư Vấn Y Tế Thông Minh

> Đồ án tốt nghiệp / Bài tập lớn: **Hệ thống Website Tư Vấn Y Tế Thông Minh & Đặt Lịch Khám 7 Bước tích hợp Chatbox AI**.  
> **Công nghệ:** Python • Django 5.2 • MySQL 8.0 • MySQL Workbench • HTML5/CSS3/JavaScript • Bootstrap 5.

---

## 🌟 1. Tổng Quan & Điểm Nổi Bật Của Đề Tài

Hệ thống giải quyết bài toán người bệnh thường không biết mình nên đi khám chuyên khoa nào, không biết bệnh viện nào ở tỉnh mình có thế mạnh đó, và gặp khó khăn trong việc đặt lịch với bác sĩ.

### Luồng Nghiệp Vụ Cốt Lõi (Trọng Tâm Đề Tài):
```
Triệu chứng ──> AI phân tích & gợi ý Chuyên khoa ──> Chọn Tỉnh/Thành phố 
  ──> Danh sách Bệnh viện thuộc tỉnh đó ──> Chọn Bác sĩ 
  ──> Chọn Ngày & Khung giờ trống ──> Xác nhận ──> Lưu vào MySQL ──> Bác sĩ duyệt lịch
```

---

## 🚀 2. Hướng Dẫn Chạy Website (Dành Cho Người Mới Bắt Đầu)

### Bước 1: Mở Terminal tại thư mục dự án `d:\doan-test`
Mở PowerShell hoặc Command Prompt tại thư mục:
```powershell
cd d:\doan-test
```

### Bước 2: Khởi động máy chủ Django
Chạy lệnh sau:
```powershell
py manage.py runserver
```
*(Nếu máy bạn dùng lệnh `python` thì chạy `python manage.py runserver`)*

### Bước 3: Truy cập trên trình duyệt
- Trang chủ website: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Quy trình đặt lịch 7 bước: [http://127.0.0.1:8000/booking/](http://127.0.0.1:8000/booking/)
- Trợ lý Chatbox AI toàn màn hình: [http://127.0.0.1:8000/chatbot/](http://127.0.0.1:8000/chatbot/)
- Bệnh viện theo Tỉnh: [http://127.0.0.1:8000/hospitals/](http://127.0.0.1:8000/hospitals/)
- Bác sĩ chuyên khoa: [http://127.0.0.1:8000/doctors/](http://127.0.0.1:8000/doctors/)
- Quản trị Django Admin: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 🔑 3. Danh Sách Tài Khoản Thử Nghiệm Sẵn Có (Seed Accounts)

Hệ thống đã nạp sẵn dữ liệu mẫu đầy đủ các vai trò:

| Vai Trò | Username | Mật Khẩu | Mục Đích Thử Nghiệm |
| :--- | :--- | :--- | :--- |
| **👨💼 Quản trị viên (Admin)** | `admin` | `admin123` | Đăng nhập `/admin/` quản lý toàn bộ cơ sở dữ liệu |
| **👨⚕️ Bác sĩ (Doctor)** | `bacsi_nam` | `doctor123` | Bác sĩ Thần kinh BV Đa khoa Đà Nẵng, vào Dashboard duyệt/hủy lịch hẹn |
| **👤 Bệnh nhân (Patient)** | `benhnhan` | `patient123` | Xem danh sách lịch khám cá nhân, đặt lịch mới |

*(Bạn cũng có thể bấm nút **Đăng ký** trên thanh menu để tạo thêm tài khoản bệnh nhân mới tùy thích).*

---

## 📊 4. Hướng Dẫn Sử Dụng MySQL Workbench Để Xem & Quản Trị Database

Cơ sở dữ liệu của dự án được lưu trực tiếp trên MySQL local:
- **Tên Database:** `medical_ai_db`
- **User:** `root`
- **Password:** `123456`
- **Host / Port:** `127.0.0.1:3306`

### Cách mở và xem dữ liệu trên MySQL Workbench:
1. Mở phần mềm **MySQL Workbench**.
2. Nhấn vào kết nối `Local instance MySQL80` (hoặc tạo kết nối mới tới `127.0.0.1:3306` với user `root` và pass `123456`).
3. Trong tab **Schemas** ở góc trái, bạn sẽ thấy cơ sở dữ liệu `medical_ai_db`.
4. Nhấn đúp vào `medical_ai_db` để kích hoạt.
5. Mở rộng mục **Tables** để thấy 19 bảng:
   - `hospitals_tinhthanh`: Bảng các Tỉnh/Thành phố.
   - `hospitals_benhvien`: Bảng các Bệnh viện (có khóa ngoại `tinh_id` trỏ về Tỉnh thành).
   - `hospitals_chuyenkhoa`: Bảng các Chuyên khoa khám chữa bệnh.
   - `doctors_bacsi`: Bảng thông tin Bác sĩ (chức danh, viện công tác, khoa, giá khám).
   - `doctors_lichlamviec`: Bảng phân ca làm việc của bác sĩ.
   - `appointments_lichkham`: Bảng lưu trữ toàn bộ các lịch đặt khám của bệnh nhân.
   - `chatbot_chatmessage`: Lịch sử các câu hỏi triệu chứng và tư vấn AI.
6. Để xem dữ liệu bảng lịch khám: Nhấp chuột phải vào bảng `appointments_lichkham` ➔ chọn **Select Rows - Limit 1000**. Mọi lịch hẹn đặt trên web sẽ xuất hiện ngay tại đây!

---

## 🧠 5. Giải Thích Chi Tiết Các Luồng Hoạt Động (Dành Cho Báo Cáo)

### Luồng 1: Tư Vấn & Đặt Lịch Qua Chatbox AI (Floating Widget & Trang Chat)
1. **Tiếp nhận triệu chứng:** Người dùng nhập tin nhắn tự nhiên (VD: *"Tôi bị đau đầu và chóng mặt 2 ngày nay"*).
2. **AI phân tích NLP (`chatbot/ai_service.py`):**
   - Quét từ khóa ngữ nghĩa triệu chứng.
   - Trả về chẩn đoán định hướng tham khảo kèm **cảnh báo y tế / miễn trừ trách nhiệm**.
   - Gợi ý Chuyên khoa phù hợp (VD: **Thần kinh**).
3. **Hỏi Tỉnh / Thành phố:** AI hiển thị các nút chọn nhanh Tỉnh/Thành phố (Đà Nẵng, Hà Nội, TP.HCM,...).
4. **Lọc Bệnh viện theo Tỉnh:** Khi người dùng chọn *"Đà Nẵng"*, AI lập tức truy vấn MySQL và trả về các Card bệnh viện tại Đà Nẵng có chuyên khoa đó.
5. **Chuyển tiếp hoặc Đặt lịch:** Mỗi Card bệnh viện có nút *"Đặt lịch ngay tại viện này"*, dẫn thẳng người dùng vào lịch khám của viện.

### Luồng 2: Quy Trình Đặt Lịch 7 Bước Trực Quan (Interactive Wizard)
- **Bước 1 (Triệu chứng & Chuyên khoa):** Nhập triệu chứng, bấm nút "AI gợi ý" để AI tự động tìm chuyên khoa, hoặc click chọn trực tiếp chuyên khoa.
- **Bước 2 (Chọn Tỉnh/Thành phố):** Click chọn Tỉnh bạn muốn đi khám (VD: Đà Nẵng).
- **Bước 3 (Chọn Bệnh viện thuộc Tỉnh):** JavaScript tự động gọi API `/hospitals/api/by-province/<tinh_id>/` để CHỈ tải danh sách các bệnh viện nằm trong tỉnh đó.
- **Bước 4 (Chọn Bác sĩ):** Tải danh sách bác sĩ thuộc bệnh viện và chuyên khoa tương ứng.
- **Bước 5 (Chọn Ngày & Giờ):** Chọn ngày khám ➔ Hệ thống kiểm tra số lượt đã đặt trong database ➔ Hiển thị các khung giờ còn trống (08:00, 09:00, 10:00, 14:00, 15:00,...).
- **Bước 6 (Thông tin bệnh nhân):** Điền Họ tên, Số điện thoại, Ghi chú cho bác sĩ.
- **Bước 7 (Xác nhận):** Xem lại toàn bộ thông tin ➔ Bấm "Xác Nhận Đặt Lịch" ➔ Gọi API `/appointments/api/create/` ➔ Lưu vào bảng `appointments_lichkham` trong MySQL ➔ Chuyển đến trang Phiếu hẹn thành công.

### Luồng 3: Bác Sĩ Tiếp Nhận & Quản Lý Lịch Hẹn
1. Bác sĩ đăng nhập tài khoản `bacsi_nam`.
2. Truy cập **Dashboard Bác sĩ** (`/doctors/dashboard/`).
3. Xem danh sách các bệnh nhân đã đặt lịch hẹn với mình.
4. Bấm **Duyệt (Xác nhận)** hoặc **Hủy**.
5. Khi bệnh nhân đến khám xong, bác sĩ bấm **Hoàn thành khám**, nhập chẩn đoán / toa thuốc vào hệ thống.

---

## 📁 6. Cấu Trúc Thư Mục Dự Án

```
d:\doan-test/
│
├── manage.py                          # Lệnh điều hành chính của Django
│
├── medical_ai/                        # Cấu hình dự án trung tâm
│   ├── settings.py                    # Cấu hình MySQL, Apps, Static, Templates
│   ├── urls.py                        # Điều hướng URL toàn hệ thống
│   ├── views.py                       # View trang chủ (home_view)
│   ├── wsgi.py & asgi.py
│
├── accounts/                          # Quản lý người dùng & phân quyền
│   ├── models.py                      # User model (patient, doctor, admin)
│   ├── forms.py, views.py, urls.py
│   └── management/commands/seed_data.py # Lệnh tạo dữ liệu mẫu tự động
│
├── hospitals/                         # Quản lý Tỉnh/Thành phố & Bệnh viện
│   ├── models.py                      # TinhThanh, ChuyenKhoa, BenhVien
│   ├── views.py                       # Lọc bệnh viện theo tỉnh, API AJAX
│   └── urls.py
│
├── doctors/                           # Quản lý Bác sĩ & Lịch làm việc
│   ├── models.py                      # BacSi, LichLamViec
│   ├── views.py                       # Dashboard bác sĩ, duyệt lịch, API slot
│   └── urls.py
│
├── appointments/                      # Quy trình đặt lịch khám bệnh
│   ├── models.py                      # LichKham (Mã lịch, trạng thái, ngày giờ)
│   ├── views.py                       # Wizard 7 bước, lịch của tôi, API đặt lịch
│   └── urls.py
│
├── chatbot/                           # Trợ lý Chatbox AI y tế
│   ├── models.py                      # ChatSession, ChatMessage
│   ├── ai_service.py                  # Bộ phân tích triệu chứng & tư vấn NLP
│   ├── views.py                       # Fullscreen chat view, API chat
│   └── urls.py
│
├── templates/                         # Giao diện HTML (Django Templates)
│   ├── base.html                      # Layout dùng chung, Floating Chatbot Widget
│   ├── home.html                      # Trang chủ hiện đại
│   ├── accounts/                      # login.html, register.html, profile.html
│   ├── hospitals/                     # hospital_list.html, hospital_detail.html
│   ├── doctors/                       # doctor_list.html, doctor_detail.html, doctor_dashboard.html
│   ├── appointments/                  # booking.html (Wizard 7 bước), my_appointments.html, booking_success.html
│   └── chatbot/                       # chat_page.html (Chat AI toàn màn hình)
│
└── static/                            # Tài nguyên tĩnh
    ├── css/style.css                  # CSS y tế chuyên nghiệp, responsive
    └── js/main.js                     # Xử lý Chatbot nổi và API
```

---

## 🛠️ 7. Lệnh Hữu Ích Thường Dùng

- Khởi động server: `py manage.py runserver`
- Nạp lại dữ liệu mẫu (reset data): `py manage.py seed_data`
- Cập nhật database khi sửa models: `py manage.py makemigrations && py manage.py migrate`
- Tạo tài khoản admin mới nếu cần: `py manage.py createsuperuser`
