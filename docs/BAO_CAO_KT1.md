# BÁO CÁO BÀI KIỂM TRA 1 (KT1): KHẢO SÁT, ĐẶC TẢ YÊU CẦU & THIẾT KẾ HỆ THỐNG
## DỰ ÁN: HỆ THỐNG QUẢN LÝ DỰ ÁN TINH GỌN VÀ TRỢ LÝ AI KOSHI (輿)

---

### THÔNG TIN CHUNG
- **Tên dự án**: Koshi (輿) Project Management Engine
- **Mã nhóm**: Nhóm 1
- **Đường dẫn triển khai trực tuyến (Live Production)**: [https://koshi.felixsu.qzz.io](https://koshi.felixsu.qzz.io)
- **Mã nguồn (Forgejo)**: [https://git.felixsu.qzz.io/felixsu/koshi](https://git.felixsu.qzz.io/felixsu/koshi)
- **Mã nguồn (GitHub Mirror)**: [https://github.com/tupm2006/koshi](https://github.com/tupm2006/koshi)

### DANH SÁCH THÀNH VIÊN & PHÂN CÔNG NHIỆM VỤ
| STT | Họ và Tên | Vai trò | Đóng góp & Trách nhiệm chính | Mức độ hoàn thành |
|:---|:---|:---|:---|:---:|
| 1 | **Phạm Minh Tú** (felixsu) | Lead Architect & Fullstack Dev | Thiết kế kiến trúc tổng thể, xây dựng FastAPI Core, Vue 3 SPA, thuật toán đồ thị Kahn DAG/CPM, Cascade AI 3 tầng, triển khai Docker & máy chủ Production | 100% |
| 2 | **Phạm Văn Huynh** | Fullstack Contributor & Testing | Xây dựng CSDL SQLite/SQLAlchemy, viết Unit Test pytest/vitest, kiểm thử tích hợp API và phân quyền RBAC | 100% |
| 3 | **Đàm Đức Đôn** | Frontend Contributor & Docs | Xây dựng giao diện Kanban/Table, tối ưu hóa phím tắt, biên soạn tài liệu đặc tả ISO 29148 và User Stories | 100% |

---

## 1. BỐI CẢNH & BÀI TOÁN QUẢN LÝ

### 1.1. Thực trạng và Vấn đề của các công cụ hiện nay
Trong kỷ nguyên phát triển phần mềm hiện đại, các nhóm kỹ thuật thường xuyên phải đối mặt với các rào cản lớn từ các hệ thống quản lý tác vụ truyền thống như Jira, Trello hay Asana:
1. **Độ trễ giao diện cao (UI Bloat & Latency)**: Thời gian tải trang trung bình vượt quá 2.5 giây, mỗi thao tác chuyển trạng thái phát sinh nhiều bước xác nhận và hoạt ảnh nặng nề làm gián đoạn dòng suy nghĩ (*cognitive flow*) của kỹ sư.
2. **Thiếu hỗ trợ phân tích đồ thị phụ thuộc (DAG & Critical Path)**: Hầu hết công cụ chỉ dừng lại ở danh sách phẳng hoặc bảng kéo thả mà không tính toán được đường găng (Critical Path), dẫn đến tình trạng dự án bị trễ tiến độ do nghẽn cổ chai tại các công việc tiền đề mà không được cảnh báo sớm.
3. **Quá tải biên bản họp và báo cáo định kỳ**: Quản lý dự án (PM) mất từ 3–5 giờ mỗi tuần chỉ để đọc ghi chú họp, trích xuất công việc thủ công và tổng hợp báo cáo tiến độ tuần cho ban lãnh đạo.

### 1.2. Mục tiêu của Hệ thống Koshi
Koshi được thiết kế như một **Công cụ quản lý dự án hiệu năng cao, điều khiển hoàn toàn bằng bàn phím (Keyboard-First), cục bộ ưu tiên (Local-First) và tích hợp Trợ lý Trí tuệ Nhân tạo đa tầng (Multi-Tier AI Cascade)**. Hệ thống loại bỏ 100% hoạt ảnh thừa để đạt tốc độ phản hồi 0ms trên giao diện và tự động hóa các tác vụ quản trị thông minh.

### 1.3. Đối tượng sử dụng (User Personas)
- **Lead Architect / Technical Lead**: Cần kiểm soát đồ thị phụ thuộc, phát hiện đường găng và vòng lặp phụ thuộc (circular dependency).
- **Project Manager (PM) / Scrum Master**: Cần phân bổ khối lượng công việc cân bằng theo kỹ năng, tạo báo cáo tổng kết tuần tự động và trích xuất biên bản họp.
- **Software Engineer / Member**: Cần giao diện bảng/Kanban siêu tốc, thao tác thuần phím tắt không rời tay khỏi bàn phím, tự động đồng bộ ngoại tuyến.

---

## 2. YÊU CẦU CHỨC NĂNG (FUNCTIONAL REQUIREMENTS - FR)

### 2.1. Phân hệ Quản lý Công việc & Không gian làm việc (Task Management)
- **FR-01 (Table View)**: Hiển thị bảng công việc mật độ cao, hỗ trợ điều hướng lên/xuống bằng phím `j`/`k`, gán nhãn độ ưu tiên (`1`-`4`), đổi trạng thái tuần hoàn bằng phím `Space`.
- **FR-02 (2D Spatial Kanban View)**: Hiển thị 4 cột quy trình (`TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`) với cơ chế cuộn vòng tròn 360 độ `(col ± 1 + 4) % 4` khi di chuyển ngang hoặc dịch chuyển thẻ.
- **FR-03 (Interactive Task Detail Inspector)**: Cho phép xem và chỉnh sửa trực tiếp tất cả thuộc tính của công việc (Tiêu đề, Trạng thái, Độ ưu tiên, Điểm độ phức tạp, Người thực hiện, Hạn chót, Lý do nghẽn, Mô tả chi tiết) với phím `Enter` và `Escape`.
- **FR-04 (Quick Creation & Inline Rename)**: Phím `n` mở nhanh hộp thoại tạo công việc; phím `i` kích hoạt chế độ đổi tên trực tiếp trên dòng mà không cần tải lại trang.

### 2.2. Phân hệ Đồ thị Phụ thuộc & Đường găng (DAG & CPM Analysis)
- **FR-05 (Dependency Linking)**: Thiết lập mối quan hệ công việc tiền đề - hậu đề giữa các tác vụ.
- **FR-06 (Cycle Detection & Rejection)**: Ứng dụng thuật toán Kahn để phát hiện và từ chối các liên kết tạo thành chu trình khép kín ($A \to B \to A$).
- **FR-07 (Critical Path Computation)**: Tự động tính toán đường găng dựa trên phương pháp CPM (Critical Path Method) và gắn cờ `🔥 CRITICAL PATH` cho các công việc có độ trễ toàn phần bằng 0.

### 2.3. Phân hệ Trợ lý AI Quản lý Dự án (AI PM Workflows)
- **FR-08 (Goal Decomposition)**: Tự động phân rã một mục tiêu lớn hoặc User Story thành danh sách các công việc con kèm ước lượng điểm độ phức tạp (S/M/L/XL).
- **FR-09 (Executive Weekly Summary)**: Tổng hợp toàn bộ dữ liệu công việc trong tuần thành báo cáo điều hành ngắn gọn gồm: Điểm nổi bật, Công việc đang thực hiện và Các rủi ro/điểm nghẽn.
- **FR-10 (Meeting Minutes Extraction)**: Trích xuất các đầu việc có cấu trúc (Tiêu đề, Người nhận, Độ phức tạp) từ văn bản ghi chú cuộc họp phi cấu trúc.
- **FR-11 (Smart Workload Balancing)**: Gợi ý phân công công việc tối ưu dựa trên ma trận kỹ năng của thành viên và tổng điểm WIP (Work-in-Progress) hiện tại.

---

## 3. YÊU CẦU PHI CHỨC NĂNG (NON-FUNCTIONAL REQUIREMENTS - NFR)

1. **NFR-01 (Hiệu năng & Độ trễ - Zero Latency)**: Tất cả thao tác chuyển đổi trên giao diện phải phản hồi trong thời gian < 16ms (tương đương 60 FPS), loại bỏ toàn bộ hoạt ảnh CSS (`animation-duration: 0s !important`).
2. **NFR-02 (Bảo mật & Phân quyền - RBAC)**: Xác thực bằng JSON Web Token (JWT) và Google OAuth2 (ID Token verification); phân quyền nghiêm ngặt giữa Quản lý dự án (`PM`) và Thành viên (`MEMBER`).
3. **NFR-03 (Độ tin cậy & Cục bộ ưu tiên - Local-First)**: Lưu trữ đồng thời trên IndexedDB (`idb-keyval`) tại trình duyệt để đảm bảo hệ thống vẫn hoạt động mượt mà khi mất kết nối mạng và tự động đồng bộ về máy chủ khi có mạng trở lại.
4. **NFR-04 (Công thái học & Tương phản - Ergonomics)**: Tuân thủ chuẩn WCAG AA với bảng màu Slate độ tương phản cao, hỗ trợ chuyển đổi Dark/Light mode tức thì không gây chớp nháy (Flash of Unstyled Content).

---

## 4. MÔ HÌNH ACTOR & USE CASE

### 4.1. Sơ đồ phân cấp Actor
- **Guest**: Người dùng chưa đăng nhập, có thể xem dữ liệu cục bộ hoặc đăng nhập qua Google OAuth / Email.
- **Member**: Thành viên dự án, có quyền tạo công việc, cập nhật tiến độ cá nhân, tham gia vào đồ thị phụ thuộc và sử dụng công cụ AI.
- **Project Manager (PM)**: Kế thừa toàn bộ quyền của Member, có thêm quyền quản lý thành viên, thăng cấp quyền hạn, điều chỉnh ma trận kỹ năng và xuất báo cáo điều hành.

### 4.2. Bảng đặc tả Use Case chi tiết

| Mã UC | Tên Use Case | Actor chính | Mô tả luồng xử lý | Điều kiện tiên quyết | Kết quả mong đợi |
|:---|:---|:---|:---|:---|:---|
| **UC-01** | Đăng nhập Google / Email | Guest | Gửi thông tin xác thực lên `/api/v1/auth/login` hoặc `/api/v1/auth/google` | Tài khoản hợp lệ | Nhận JWT Token và lưu vào LocalStorage |
| **UC-02** | Điều hướng bảng phím tắt | Member, PM | Nhấn `j`/`k` hoặc mũi tên để thay đổi con trỏ | Đang mở chế độ Bảng/Kanban | Hàng/thẻ được chọn sáng vòng focus tức thì |
| **UC-03** | Chuyển đổi trạng thái tuần hoàn | Member, PM | Nhấn `Space` tại thẻ đang chọn | Đã chọn một công việc | Trạng thái chuyển: TODO $\to$ IN_PROGRESS $\to$ BLOCKED $\to$ DONE |
| **UC-04** | Kiểm tra chi tiết công việc | Member, PM | Nhấn `Enter` để mở TaskDetailModal | Đã chọn một công việc | Mở Inspector, cho phép chỉnh sửa toàn bộ trường dữ liệu |
| **UC-05** | Tính toán Đường găng (CPM) | PM, Member | Hệ thống tự động kích hoạt khi có thay đổi liên kết | Có ít nhất 2 công việc liên kết | Gắn nhãn `CRITICAL PATH` lên các công việc then chốt |
| **UC-06** | Phân rã mục tiêu bằng AI | PM, Member | Nhập mục tiêu $\to$ gọi Cascade AI $\to$ xem danh sách công việc con | Đã đăng nhập | Backlog nhận danh sách công việc con được phân rã |
| **UC-07** | Tạo Báo cáo Tuần bằng AI | PM | Nhấn "Weekly Summary" $\to$ Backend tổng hợp tiến độ | Có công việc trong sprint | Tạo báo cáo 3 phần (Highlights, In-Flight, Blockers) |
| **UC-08** | Trích xuất Biên bản họp | PM, Member | Dán văn bản ghi chú cuộc họp $\to$ AI phân tích cú pháp | Văn bản có nội dung họp | Trả về danh sách Task DTO sẵn sàng thêm vào sprint |
| **UC-09** | Gợi ý Phân công Thông minh | PM | Nhấn "Recommend" tại công việc $\to$ AI so khớp skill | Có dữ liệu thành viên | Gợi ý thành viên phù hợp nhất kèm giải thích lý do |
| **UC-10** | Quản lý Vai trò & Kỹ năng | PM | Vào danh sách User $\to$ cập nhật Role (`PM`/`MEMBER`) và Skill tags | Quyền PM | Quyền hạn và thông tin kỹ năng được cập nhật trong CSDL |
| **UC-11** | Chuyển đổi Giao diện Kanban/Table | Member, PM | Nhấn phím `v` hoặc nút chuyển đổi chế độ | Đang ở màn hình chính | Giao diện chuyển đổi tức thì không giật lag |

---

## 5. THIẾT KẾ CƠ SỞ DỮ LIỆU (DATABASE DESIGN)

### 5.1. Sơ đồ Thực thể Mối quan hệ (ERD)

```
+------------------+         1:N         +------------------+
|      USERS       |-------------------->|     PROJECTS     |
|------------------|                     |------------------|
| id (PK)          |                     | id (PK)          |
| email (UQ)       |                     | name             |
| hashed_password  |                     | description      |
| google_id (UQ)   |                     | owner_id (FK)    |
| full_name        |                     | created_at       |
| role (PM/MEMBER) |                     +------------------+
| skills           |                              |
+------------------+                              | 1:N
        |                                         v
        | 1:N                            +------------------+
        |                                |     SPRINTS      |
        |                                |------------------|
        |                                | id (PK)          |
        |                                | project_id (FK)  |
        |                                | name             |
        |                                | goal             |
        |                                | is_active        |
        |                                +------------------+
        |                                         |
        | 1:N                                     | 1:N
        v                                         v
+-----------------------------------------------------------+
|                           TASKS                           |
|-----------------------------------------------------------|
| id (PK, VARCHAR(32)) - e.g. 'TSK-1'                       |
| project_id (FK -> projects.id)                            |
| sprint_id (FK -> sprints.id)                              |
| assignee_id (FK -> users.id)                              |
| title (VARCHAR(255))                                      |
| description (TEXT)                                        |
| status (ENUM: TODO, IN_PROGRESS, BLOCKED, DONE)           |
| priority (ENUM: LOW, MEDIUM, HIGH, CRITICAL)              |
| complexity_points (INTEGER: 1, 2, 3, 5)                   |
| due_date (DATETIME)                                       |
| blocking_reason (VARCHAR(500))                            |
| created_at / updated_at (DATETIME)                        |
+-----------------------------------------------------------+
        |                                   |
        | 1:N (Self-Ref M:N)                | 1:N
        v                                   v
+-------------------------+       +-------------------------+
|    TASK_DEPENDENCIES    |       |        COMMENTS         |
|-------------------------|       |-------------------------|
| id (PK)                 |       | id (PK)                 |
| task_id (FK)            |       | task_id (FK)            |
| depends_on_task_id (FK) |       | author_id (FK)          |
| UNIQUE(task, depends_on)|       | content (TEXT)          |
+-------------------------+       +-------------------------+
```

### 5.2. Bảng mô tả chi tiết các trường dữ liệu

#### Bảng `users` (Người dùng & Phân quyền)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Ý nghĩa |
|:---|:---|:---|:---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Mã định danh người dùng |
| `email` | VARCHAR(255) | NOT NULL, UNIQUE | Địa chỉ email đăng nhập |
| `hashed_password`| VARCHAR(255) | NULLABLE | Mật khẩu băm Bcrypt (Null nếu dùng OAuth) |
| `full_name` | VARCHAR(255) | NOT NULL | Họ và tên hiển thị |
| `google_id` | VARCHAR(255) | UNIQUE, NULLABLE | Mã định danh Google OAuth `sub` |
| `avatar_url` | VARCHAR(500) | NULLABLE | Đường dẫn ảnh đại diện |
| `role` | VARCHAR(20) | CHECK IN ('PM', 'MEMBER') | Vai trò hệ thống |
| `skills` | VARCHAR(500) | DEFAULT 'general' | Danh sách kỹ năng (phục vụ AI phân công) |

#### Bảng `tasks` (Công việc dự án)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Ý nghĩa |
|:---|:---|:---|:---|
| `id` | VARCHAR(32) | PRIMARY KEY | Mã công việc định dạng chuẩn (ví dụ: `TSK-1`) |
| `project_id` | INTEGER | FOREIGN KEY -> `projects.id` | Dự án sở hữu |
| `sprint_id` | INTEGER | FOREIGN KEY -> `sprints.id` | Sprint thực thi |
| `assignee_id` | INTEGER | FOREIGN KEY -> `users.id` | Thành viên phụ trách |
| `title` | VARCHAR(255) | NOT NULL | Tiêu đề công việc |
| `description` | TEXT | NULLABLE | Mô tả chi tiết kỹ thuật |
| `status` | VARCHAR(20) | CHECK IN ('TODO', 'IN_PROGRESS', 'BLOCKED', 'DONE') | Trạng thái vòng đời |
| `priority` | VARCHAR(20) | CHECK IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') | Mức độ ưu tiên |
| `complexity_points`| INTEGER| DEFAULT 2 (1=S, 2=M, 3=L, 5=XL) | Điểm độ phức tạp |
| `blocking_reason`| VARCHAR(500)| NULLABLE | Nguyên nhân công việc bị nghẽn |

---

## 6. THIẾT KẾ KIẾN TRÚC HỆ THỐNG (SYSTEM ARCHITECTURE)

Hệ thống được thiết kế theo mô hình **3 lớp phân tách rõ ràng (Decoupled 3-Tier Architecture)**:

```
[ Client Browser ] <---> [ Nginx / Caddy Edge ] <---> [ FastAPI 0.110+ Core ] <---> [ SQLite Database ]
  (Vue 3.5 SPA)            (SSL / Reverse Proxy)        (Python 3.11 Runtime)         (/app/data/koshi.db)
```

1. **Presentation Tier (Client SPA)**:
   - Xây dựng bằng **Vue 3.5 Composition API** (`<script setup lang="ts">`) và **TypeScript 5.7**.
   - Quản lý trạng thái bằng **Pinia 2.3** kết hợp lưu trữ cục bộ IndexedDB qua `idb-keyval`.
   - Bộ giải toán đồ thị Kahn DAG và CPM chạy trực tiếp tại trình duyệt để cung cấp phản hồi tức thời cho người dùng.
2. **Application Tier (Backend API)**:
   - Xây dựng bằng **FastAPI 0.110+** trên nền **Python 3.11** bất đồng bộ (async ASGI).
   - Xác thực phân quyền RBAC bằng JWT Bearer Token.
   - Quản lý giao tiếp CSDL qua **SQLAlchemy 2.0 ORM**.
3. **Data Tier (Embedded Persistence)**:
   - Sử dụng **SQLite 3** với chế độ WAL (Write-Ahead Logging) lưu trữ trên volume mount bền vững `/app/data/koshi.db`.

---

## 7. VỊ TRÍ ỨNG DỤNG AI TRONG HỆ THỐNG

Koshi tích hợp Trí tuệ Nhân tạo tại **3 điểm mấu chốt** trong quy trình quản lý dự án:
1. **Phân rã Mục tiêu (Goal Decomposition)**: Chuyển đổi yêu cầu kinh doanh trừu tượng thành các đầu việc kỹ thuật cụ thể.
2. **Tổng hợp Báo cáo Sprint (Weekly Executive Summary)**: Tự động hóa khâu làm báo cáo định kỳ cho PM.
3. **Trích xuất Biên bản Cuộc họp (Meeting Minutes Extraction)**: Biến các cuộc thảo luận tự do thành hành động backlog có cấu trúc.

---

## 8. THIẾT KẾ PROMPT & LUỒNG GỌI AI

### 8.1. Bảng Thiết kế System Prompt & User Prompt Mẫu

| Chức năng AI | System Prompt | User Prompt Mẫu | Định dạng JSON Đầu ra (Schema) |
|:---|:---|:---|:---|
| **Weekly Summary** | "You are an expert Project Lead. Analyze sprint tasks and provide a concise, high-impact weekly summary in 3 sections: Highlights, In-Flight, Blockers." | "Tasks: [{id: 'TSK-1', title: 'Setup DB', status: 'DONE'}, {id: 'TSK-3', title: 'AI API', status: 'BLOCKED', reason: 'Missing key'}]" | `{"status": "success", "summary": "### 🚀 Highlights\n- Setup DB\n\n### ⚠️ Blockers\n- AI API: Missing key"}` |
| **Meeting Minutes** | "You are a Scrum Master. Extract actionable tasks from unstructured notes. Return valid JSON matching TaskSchema." | "Daily standup: John finished auth. Huynh is blocked on SQLite locks. Don will build Kanban UI today." | `{"tasks": [{"title": "Resolve SQLite lock", "assignee": "Huynh", "priority": "HIGH", "complexity": "M"}]}` |
| **Workload Recommend**| "You are an AI Resource Planner. Match tasks to team members based on skills and current WIP points to avoid burnout." | "Task: 'Vue 3 Virtual Scroll', Skills required: 'vue,frontend'. Team: [{name: 'Huynh', wip: 5, skills: 'python'}, {name: 'Don', wip: 2, skills: 'vue'}]" | `{"recommended_assignee": "Don", "confidence": 0.95, "reason": "Lowest WIP (2pts) and exact skill match with Vue."}` |

### 8.2. Cơ chế Fallback 3 Tầng (Multi-Tier Cascade)
Để đảm bảo hệ thống không bao giờ bị tê liệt khi mất mạng hoặc hết hạn mức API:
- **Tầng 1 (Client Rule Heuristics)**: Xử lý tức thì các mẫu câu quen thuộc bằng biểu thức chính quy tại trình duyệt (< 5ms).
- **Tầng 2 (Backend Heuristics)**: So khớp ma trận kỹ năng cục bộ tại FastAPI (< 50ms).
- **Tầng 3 (Cloud LLM - Gemini 1.5 Flash)**: Gọi mô hình ngôn ngữ lớn qua API khi cần suy luận ngữ nghĩa phức tạp (< 1500ms).

---

## 9. MINH CHỨNG ỨNG DỤNG AI TRONG SDLC (KT1)

Trong giai đoạn thực hiện Bài kiểm tra 1 (KT1), nhóm đã ứng dụng AI để tối ưu hóa quy trình kỹ nghệ phần mềm:
1. **Phân tích Yêu cầu & Tạo URD/SRS**: Sử dụng AI để chuẩn hóa các yêu cầu người dùng theo tiêu chuẩn quốc tế ISO/IEC/IEEE 29148:2018.
2. **Kiểm tra Tính đúng đắn của Thuật toán Đồ thị**: Dùng AI để thẩm định mô hình toán học của thuật toán Kahn và phương pháp đường găng CPM, đảm bảo không xảy ra hiện tượng tràn bộ nhớ hoặc lặp vô hạn.
3. **Sinh CSDL & Mã khởi tạo tự động**: Tạo tự động file DDL chuẩn `schema.sql` và script khởi tạo `init_db.py`.

---

## 10. KẾ HOẠCH TRIỂN KHAI CHO CÁC GIAI ĐOẠN TIẾP THEO

```
[ Giai đoạn 1: KT1 ] ---> [ Giai đoạn 2: KT2 ] ---> [ Giai đoạn 3: KT3 ] ---> [ Báo cáo Cuối kỳ ]
Khảo sát & Thiết kế      Hoàn thiện CRUD & Auth    Tích hợp AI & Testing     Đóng gói & Nghiệm thu
```

- **KT2 (Giai đoạn 2)**:
  - Hoàn thiện 100% các API CRUD cho Projects, Sprints, Tasks, Dependencies.
  - Tích hợp hoàn chỉnh Google OAuth2 và phân quyền RBAC đa người dùng.
  - Đảm bảo toàn bộ bảng dữ liệu trên giao diện đồng bộ 2 chiều với backend.
- **KT3 (Giai đoạn 3)**:
  - Hoàn thiện bộ 4 công cụ AI PM (Decomposer, Summary, Minutes, Workload).
  - Viết bộ kiểm thử tự động (Unit Test & Integration Test) đạt độ bao phủ > 85%.
- **Báo cáo Cuối kỳ (Final Submission)**:
  - Xuất bản tài liệu kiến trúc, tài liệu hướng dẫn cài đặt và video demo trực quan.
