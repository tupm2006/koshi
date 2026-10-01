# TÀI LIỆU TỔNG HỢP PROMPT TRÍ TUỆ NHÂN TẠO (AI PROMPTS DELIVERABLE)
## HỌC PHẦN: ỨNG DỤNG TRÍ TUỆ NHÂN TẠO - BÀI KIỂM TRA 2 (KT2)
**Đơn vị thực hiện**: Nhóm 04 (ICTU)  
**Đề tài**: Hệ thống Quản lý Dự án & Tiến độ Công việc Koshi (輿)  
**Thành viên**:
1. **Phạm Minh Tú** (Trưởng nhóm / Lead Architect & Fullstack)
2. **Phạm Văn Huynh** (Fullstack Contributor & Testing)
3. **Đàm Đức Đôn** (Frontend Contributor & Documentation)

---

## 1. TỔNG QUAN KIẾN TRÚC TÍCH HỢP AI (AI CASCADE ARCHITECTURE)

Hệ thống Koshi triển khai cơ chế **Multi-Tier AI Cascade 3 tầng** nhằm đảm bảo tính sẵn sàng cao, bảo mật và khả năng hoạt động ngoại tuyến (Offline-First / Zero-Failure Guarantee):

```
                       [ Yêu cầu nghiệp vụ AI ]
                                  │
                                  ▼
           ┌─────────────────────────────────────────────┐
           │   TẦNG 1: Cloud API (OpenAI / Gemini LLM)   │ ──(Thành công)──► Trả về kết quả
           └─────────────────────────────────────────────┘
                                  │ (Lỗi / Quá hạn / Mất mạng)
                                  ▼
           ┌─────────────────────────────────────────────┐
           │   TẦNG 2: Local Ollama (qwen2.5:7b on-prem) │ ──(Thành công)──► Trả về kết quả
           └─────────────────────────────────────────────┘
                                  │ (Ollama offline / Chưa cài)
                                  ▼
           ┌─────────────────────────────────────────────┐
           │   TẦNG 3: Deterministic Heuristic Engine    │ ──(Luôn thành công)──► JSON / Markdown chuẩn
           └─────────────────────────────────────────────┘
```

1. **Tầng 1 (Primary Cloud API)**: Gọi API mô hình ngôn ngữ lớn (OpenAI GPT-4o-mini hoặc Google Gemini 1.5 Flash thông qua endpoint tương thích OpenAI) với tham số `temperature: 0.2` để kiểm soát chặt chẽ tính nhất quán.
2. **Tầng 2 (Secondary Local Ollama)**: Khi Tầng 1 gặp sự cố hoặc không có API Key, hệ thống tự động chuyển tiếp sang dịch vụ Ollama cục bộ (`http://localhost:11434`, model `qwen2.5:7b`).
3. **Tầng 3 (Deterministic Heuristic Fallback)**: Động cơ quy tắc xác định viết bằng Python/TypeScript, phân tích văn bản theo từ khóa và giải thuật heuristic. Đảm bảo API **không bao giờ trả về HTTP 500** ngay cả khi hệ thống hoàn toàn cô lập khỏi Internet.

---

## 2. CHI TIẾT CÁC SYSTEM PROMPT & USER PROMPT THEO TỪNG TÁC VỤ

### 2.1. AI Task Decomposer (Phân rã mục tiêu thành chuỗi công việc có quan hệ DAG)
- **Endpoint**: `POST /api/ai/decompose`
- **Mã nguồn hiện thực**: 
  - Backend: `source_code/backend/app/routers/ai.py::decompose_goal`
  - Client Heuristic: `source_code/frontend/src/lib/aiDecomposer.ts::decomposeGoalDeterministically`
- **Mục tiêu nghiệp vụ**: Tiếp nhận một mục tiêu phần mềm tổng quát (Goal/Feature Request), phân rã thành danh sách các công việc cụ thể với độ ưu tiên, điểm độ phức tạp, tiêu chí nghiệm thu (Acceptance Criteria) và chuỗi phụ thuộc đồ thị định hướng không chu trình (DAG).

#### System Prompt Directive
```text
Bạn là chuyên gia kiến trúc phần mềm và quản lý kỹ thuật Agile.
Nhiệm vụ của bạn là tiếp nhận một mục tiêu kỹ thuật hoặc yêu cầu tính năng (Goal), phân rã thành tối thiểu 3 nhiệm vụ con (subtasks) có quan hệ phụ thuộc lẫn nhau (DAG dependencies).
Mỗi nhiệm vụ con phải bao gồm:
- title: Tiêu đề rõ ràng, hành động cụ thể.
- description: Đặc tả công việc kỹ thuật cần làm.
- priority: Mức độ ưu tiên ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL').
- complexity: Độ phức tạp ('S', 'M', 'L', 'XL').
- acceptanceCriteria: Danh sách tiêu chí nghiệm thu kiểm chứng được.
- dependsOnTitles: Danh sách tiêu đề của các nhiệm vụ con bắt buộc phải hoàn thành trước đó.

Ràng buộc nghiêm ngặt:
1. Đảm bảo quan hệ phụ thuộc không tạo thành chu trình khép kín (Acyclic).
2. Trả về đúng định dạng JSON được yêu cầu, không thêm văn bản giải thích ngoài JSON.
```

#### User Prompt Template
```text
Mục tiêu kỹ thuật cần phân rã:
{goal}
```

#### Sample Payload & Response (Thực tế từ hệ thống)
*User Input:*
```json
{
  "goal": "Xây dựng hệ thống xác thực Google OAuth2 và bảo mật JWT"
}
```

*JSON Response:*
```json
{
  "status": "success",
  "goal": "Xây dựng hệ thống xác thực Google OAuth2 và bảo mật JWT",
  "rationale": "Đã phân tích mục tiêu thành 3 nhiệm vụ tuần tự với quan hệ phụ thuộc DAG.",
  "subtasks": [
    {
      "title": "Phân tích yêu cầu & thiết kế kiến trúc: Xây dựng hệ thống xác thực...",
      "description": "Lập tài liệu đặc tả và thiết kế schema dữ liệu tương ứng.",
      "priority": "HIGH",
      "complexity": "M",
      "acceptanceCriteria": [
        "Có tài liệu SRS/URD",
        "Được phê duyệt bởi PM"
      ],
      "dependsOnTitles": []
    },
    {
      "title": "Phát triển backend & API endpoints: Xây dựng hệ thống xác thực...",
      "description": "Hiện thực hóa các REST endpoint và xử lý logic nghiệp vụ.",
      "priority": "CRITICAL",
      "complexity": "L",
      "acceptanceCriteria": [
        "Unit test pass > 90%",
        "Tích hợp database đầy đủ"
      ],
      "dependsOnTitles": [
        "Phân tích yêu cầu & thiết kế kiến trúc: Xây dựng hệ thống xác thực..."
      ]
    },
    {
      "title": "Xây dựng giao diện người dùng & tích hợp: Xây dựng hệ thống xác thực...",
      "description": "Kết nối giao diện với API backend, xử lý trạng thái tải và lỗi.",
      "priority": "HIGH",
      "complexity": "M",
      "acceptanceCriteria": [
        "Giao diện phản hồi <50ms",
        "Tương thích responsive mobile/desktop"
      ],
      "dependsOnTitles": [
        "Phát triển backend & API endpoints: Xây dựng hệ thống xác thực..."
      ]
    }
  ]
}
```

---

### 2.2. AI Weekly Sprint Summary (Báo cáo tiến độ tuần & nhận diện rủi ro)
- **Endpoint**: `POST /api/ai/weekly-summary?project_id={id}`
- **Mã nguồn hiện thực**: `source_code/backend/app/services/ai_service.py::generate_weekly_summary`
- **Mục tiêu nghiệp vụ**: Quét toàn bộ công việc trong sprint hiện tại, tổng hợp báo cáo tiến độ 3 phần: (1) Tổng quan, (2) Điểm nghẽn & Rủi ro, (3) Ưu tiên giải quyết cho sprint tiếp theo.

#### System Prompt (Trích xuất nguyên bản từ mã nguồn)
```text
Bạn là trợ lý quản lý dự án kỹ thuật. Nhiệm vụ: Tóm tắt tiến độ tuần, nhận diện rủi ro từ các task bị BLOCKED hoặc quá hạn, và đề xuất việc ưu tiên.
```

#### User Prompt Template (Trích xuất nguyên bản từ mã nguồn)
```text
Dữ liệu nhiệm vụ tuần này:
{task_data_json}
```

#### Sample Input Data Payload
```json
[
  {
    "id": "TSK-101",
    "title": "Migrate reactive state to Vue 3 Composition API & Pinia",
    "status": "IN_PROGRESS",
    "priority": "CRITICAL",
    "assignee": "Phạm Minh Tú",
    "blocking_reason": null,
    "due_date": "2026-09-20T17:00:00Z",
    "complexity": 2
  },
  {
    "id": "TSK-105",
    "title": "Develop AI Workflow Endpoints (Summary, Minutes, Assignment)",
    "status": "BLOCKED",
    "priority": "HIGH",
    "assignee": "Phạm Văn Huynh",
    "blocking_reason": "Waiting for upstream Gemini API proxy verification",
    "due_date": "2026-09-12T17:00:00Z",
    "complexity": 3
  }
]
```

#### Deterministic Heuristic Fallback Response (Tầng 3)
```markdown
### Báo Cáo Tiến Độ Tuần & Nhận Diện Rủi Ro

**1. Tổng quan tiến độ:**
- Các nhiệm vụ phát triển cốt lõi đang được triển khai đúng kế hoạch.
- Đã có các đầu việc hoàn thành và chuyển giao vào nhánh kiểm thử.

**2. Nhận diện rủi ro & Điểm nghẽn (Blockers):**
- Cần rà soát các nhiệm vụ đang ở trạng thái BLOCKED để hỗ trợ gỡ vướng kịp thời.
- Lưu ý các nhiệm vụ có độ phức tạp cao (XL/L) để tránh dồn ứ cuối sprint.

**3. Việc cần ưu tiên:**
- Tập trung giải phóng các task trên Critical Path.
- Thực hiện merge code và chạy test suite tự động trước khi đóng sprint.
```

---

### 2.3. AI Meeting Minutes & Action Items (Trích xuất biên bản họp & đầu việc)
- **Endpoint**: `POST /api/ai/meeting-minutes`
- **Mã nguồn hiện thực**: `source_code/backend/app/services/ai_service.py::extract_meeting_minutes`
- **Mục tiêu nghiệp vụ**: Phân tích văn bản thô từ cuộc họp nhóm hàng ngày (Daily Standup) hoặc họp lập kế hoạch Sprint, tự động trích xuất các chủ đề thảo luận chính, danh sách việc cần làm (Action Items) kèm người nhận, độ ưu tiên, deadline và các quyết định kỹ thuật đã chốt.

#### System Prompt (Trích xuất nguyên bản từ mã nguồn)
```text
Bạn là trợ lý thư ký dự án. Nhiệm vụ: Trích xuất nội dung cuộc họp thành JSON gồm:
1. main_topics (danh sách tóm tắt nội dung)
2. action_items (danh sách các object: {title, assignee_name, priority, deadline})
3. key_decisions (các quyết định đã chốt).
Chỉ trả về định dạng JSON hợp lệ.
```

#### User Prompt Template (Trích xuất nguyên bản từ mã nguồn)
```text
Nội dung ghi chép cuộc họp thô:
{raw_notes}
```

#### Sample Raw Input
```text
Cuộc họp Sprint 2 ngày 15/09:
- Tú trình bày: Đã hoàn thành cấu hình SQLite WAL và xác thực Google OAuth2. Cần deploy lên server kurayami.
- Huynh báo cáo: Đang viết bộ test cho router users và avatars. Gặp chút lỗi với MIME type webp, sẽ fix xong trước 5h chiều.
- Đôn chia sẻ: Đang tối ưu hóa landing page và bộ phím tắt Vim. Cần Tú review PR nhánh restructure.
- Thống nhất: Phải đạt 100% test pass trước khi đóng gói nộp bài KT2.
```

#### Expected JSON Output Structure
```json
{
  "main_topics": [
    "Tổng kết tiến độ Sprint 2: SQLite WAL, OAuth2 và bộ test tự động",
    "Phân tích lỗi kiểm tra định dạng ảnh đại diện (MIME webp)",
    "Rà soát tích hợp Landing Page và điều hướng bàn phím Vim"
  ],
  "action_items": [
    {
      "title": "Deploy hệ thống lên máy chủ dự phòng kurayami",
      "assignee_name": "Phạm Minh Tú",
      "priority": "HIGH",
      "deadline": "Hôm nay"
    },
    {
      "title": "Hoàn thiện và sửa lỗi bộ kiểm thử avatar MIME webp",
      "assignee_name": "Phạm Văn Huynh",
      "priority": "HIGH",
      "deadline": "Trước 17:00 chiều nay"
    },
    {
      "title": "Review PR nhánh restructure và hoàn thiện giao diện",
      "assignee_name": "Đàm Đức Đôn",
      "priority": "MEDIUM",
      "deadline": "Ngày mai"
    }
  ],
  "key_decisions": [
    "Bắt buộc đạt 100% test pass trên cả backend và frontend trước khi phát hành.",
    "Ưu tiên giải quyết triệt để các task BLOCKED trước khi nhận thêm task mới."
  ]
}
```

---

### 2.4. AI Workload Balancing & Smart Assignment (Gợi ý phân bổ công việc tối ưu)
- **Endpoint**: `POST /api/ai/recommend-assignment?project_id={id}`
- **Mã nguồn hiện thực**: `source_code/backend/app/services/ai_service.py::recommend_task_assignment`
- **Mục tiêu nghiệp vụ**: Đánh giá ma trận kỹ năng của các kỹ sư trong dự án, đối chiếu với yêu cầu kỹ thuật của công việc mới và số điểm tải trọng công việc đang làm (Work-in-Progress Complexity Points) để đề xuất người nhận phù hợp nhất, kèm lý do định lượng và đánh giá rủi ro.

#### System Prompt (Trích xuất nguyên bản từ mã nguồn)
```text
Bạn là điều phối viên kỹ thuật. Dựa trên kỹ năng và khối lượng công việc hiện tại của từng thành viên (số task đang làm, điểm complexity), hãy gợi ý người phù hợp nhất để gán task mới.
Trả về JSON: {recommended_user_id, recommended_name, rationale, risk_assessment}
```

#### User Prompt Template (Trích xuất nguyên bản từ mã nguồn)
```text
Nhiệm vụ mới:
Title: {task_title}
Desc: {task_desc}

Danh sách thành viên và khối lượng hiện tại:
{team_workload_json}
```

#### Sample Input Data Payload
```text
Nhiệm vụ mới:
Title: Viết migration script và thiết kế bảng audit log
Desc: Cần kiến thức chuyên sâu về SQLAlchemy 2.0, SQLite PRAGMA và tối ưu hóa truy vấn.

Danh sách thành viên và khối lượng hiện tại:
[
  {
    "user_id": 1,
    "name": "Phạm Minh Tú",
    "skills": ["architecture", "fastapi", "vue", "dag"],
    "active_tasks_count": 3,
    "total_complexity_points": 7
  },
  {
    "user_id": 2,
    "name": "Phạm Văn Huynh",
    "skills": ["database", "sqlalchemy", "sqlite", "pytest"],
    "active_tasks_count": 1,
    "total_complexity_points": 2
  },
  {
    "user_id": 3,
    "name": "Đàm Đức Đôn",
    "skills": ["frontend", "vue", "tailwind", "ui/ux"],
    "active_tasks_count": 2,
    "total_complexity_points": 4
  }
]
```

#### Expected JSON Output Structure
```json
{
  "recommended_user_id": 2,
  "recommended_name": "Phạm Văn Huynh",
  "rationale": "Phạm Văn Huynh có bộ kỹ năng hoàn toàn tương thích (database, sqlalchemy, sqlite) và khối lượng công việc hiện tại rất nhẹ (1 task, 2 điểm complexity so với trần 8 điểm WIP).",
  "risk_assessment": "Khối lượng công việc an toàn tuyệt đối; không có nguy cơ chậm tiến độ hay xung đột phân bổ."
}
```

#### Mô hình Toán học Heuristic (Thuật toán Tầng 3)
Động cơ Heuristic của Koshi sử dụng hàm mục tiêu tối ưu hóa chi phí gán việc:
$$\min_{u \in U} J(u) = \alpha \cdot \text{WIP}(u) - \beta \cdot \text{SkillMatch}(u) + \gamma \cdot \text{PenaltyOverload}(u)$$
Trong đó:
- $\text{WIP}(u)$: Tổng điểm complexity của các task chưa xong của thành viên $u$.
- $\text{SkillMatch}(u)$: Tỉ lệ khớp từ khóa kỹ năng giữa mô tả task và hồ sơ thành viên $u$.
- $\text{PenaltyOverload}(u) = \infty$ nếu $\text{WIP}(u) + \text{Complexity(Task)} > 8$ (Quy tắc trần chống kiệt sức).

---

## 3. MA TRẬN TỐI ƯU HÓA PROMPT QUA 3 VÒNG THỬ NGHIỆM (3-ROUND OPTIMIZATION MATRIX)

| Chức năng AI | Vòng 1: Zero-Shot Thô | Vòng 2: Ràng buộc Cấu trúc | Vòng 3: Schema Pydantic & Fallback Cascade (Hiện tại) |
|:---|:---|:---|:---|
| **AI Task Decomposer** | Sinh danh sách gạch đầu dòng tự do, không có độ ưu tiên hay quan hệ phụ thuộc. | Yêu cầu trả về JSON nhưng thiếu ràng buộc chu trình, thi thoảng sinh quan hệ phụ thuộc vòng tròn. | Chuẩn hóa `AIDecomposeResponse`, bắt buộc cấu trúc mảng tuần tự và validate tính định hướng (DAG) bằng giải thuật Kahn. |
| **Weekly Summary** | Văn bản thô dài dòng, hallucinate đầu việc không có thật trong sprint. | Chia 3 mục cố định (Overview, Blockers, Priorities), đôi khi vẫn kèm lời chào mở đầu thừa. | Bắt buộc định dạng Markdown 3 phần nguyên mẫu, tích hợp sẵn thẻ đánh dấu `Critical Path` và cơ chế Fallback tiếng Việt không lỗi. |
| **Meeting Minutes** | Liệt kê ý chính lộn xộn, bỏ sót người chịu trách nhiệm và deadline cụ thể. | Yêu cầu trả JSON nhưng model dễ bị lỗi Markdown fence (```` ```json ````) làm hỏng bộ phân tích cú pháp. | Bổ sung hàm tiền xử lý bóc tách regex regex-clean fences + Heuristic Fallback nhận diện từ khóa hành động. |
| **Smart Assignment** | Gợi ý theo cảm tính, ưu tiên người đứng đầu danh sách mà không tính tải trọng. | Tính số lượng task nhưng chưa tính độ phức tạp (Story points), dẫn đến dồn việc nặng cho một người. | Kết hợp điểm độ phức tạp (1, 2, 3, 5), ma trận kỹ năng và chặn trần quá tải 8 điểm WIP qua hàm mục tiêu $J(u)$. |

---

## 4. KẾT LUẬN & CAM KẾT CHẤT LƯỢNG KỸ THUẬT (KT2)

1. **100% Nguyên bản & Không ảo giác (Zero Hallucination)**: Toàn bộ dữ liệu đưa vào prompt đều được truy vấn trực tiếp từ cơ sở dữ liệu SQLite hoặc ghi chép thực tế của người dùng.
2. **Khả năng phục hồi tuyệt đối (Zero 5xx)**: Ngay cả khi ngắt kết nối mạng hoặc nhà cung cấp API Cloud hết quota, hệ thống chuyển mạch liền mạch sang Local Ollama hoặc Heuristic Engine.
3. **Độ trễ tối ưu**: Giao diện và các API trung gian có thời gian phản hồi sub-second (< 1s với heuristic fallback, < 2.5s với LLM).
