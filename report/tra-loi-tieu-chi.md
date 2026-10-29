# Trả lời theo tiêu chí chấm

Tài liệu ôn vấn đáp: với mỗi tiêu chí trong `report/image.webp` có các câu cô có thể hỏi, câu trả lời
ngắn, và **chỗ để chỉ ra** (mục trong báo cáo, file trong repo, hoặc thao tác demo).

- Số mục báo cáo theo bản PDF `Koshi-BaoCao-VI.pdf` (bản tiếng Anh `Koshi-Report-EN.pdf` cùng số mục).
- Đường dẫn file tính từ thư mục gốc của repo.
- Bản chạy thật: https://koshi.huynhca.com

---

## Tiêu chí 1 — Quyển báo cáo: phân tích bài toán và thiết kế giải pháp (3,0 điểm)

### 1.1 Phân tích đúng nghiệp vụ

**Hỏi: Bài toán nghiệp vụ là gì? Hiện tại người ta làm thế nào, vướng ở đâu?**
Nhóm sinh viên đang phối hợp qua chat và bảng tính, nên gặp 4 vấn đề:
- không có một nguồn sự thật duy nhất;
- người bị kẹt việc không ai thấy;
- các việc phụ thuộc nhau mà không có thứ tự;
- báo cáo và giao việc làm thủ công.

→ Báo cáo **mục 2.3.1**. So sánh với Trello, Jira và bảng tính ở **mục 2.1, Bảng 2.1**.

**Hỏi: Quy trình nghiệp vụ mới mà hệ thống hỗ trợ là gì?**
Chu trình kiểu Scrum gồm 8 bước, mỗi bước ghi rõ vai trò thực hiện:

tạo dự án/mời → lập backlog → lập kế hoạch sprint (có AI gợi ý giao việc) → bắt đầu sprint (chốt cam
kết) → làm việc hằng ngày → theo dõi burndown → kết thúc sprint (chuyển việc dở) → retrospective.

→ **Mục 2.3.2, Hình 2.2**. Vòng đời task TODO → IN_PROGRESS → BLOCKED → DONE ở **mục 2.3.3**. Vòng
đời sprint ở **mục 2.4.1**.

**Hỏi: Có những tác nhân nào? Phân quyền ra sao?**
Có 5 tác nhân: Khách, Người dùng, PM, Thành viên và dịch vụ AI.

Điểm then chốt là **vai trò gắn theo từng dự án**, không phải theo tài khoản: cùng một người có thể
là PM ở dự án A và Thành viên ở dự án B, và lúc đăng ký không chọn vai trò.

→ **Mục 2.2**: Bảng tác nhân và Hình use case.

**Hỏi: Quy tắc nghiệp vụ quan trọng nhất?**
Có 11 quy tắc, BR-01 đến BR-11. Nên nêu ví dụ:
- lời mời chưa chấp nhận thì không có quyền gì (BR-02);
- người ngoài dự án nhận 404, coi như dự án không tồn tại (BR-03);
- mỗi dự án chỉ có một sprint chạy (BR-05);
- dự án nhóm chỉ được xem khi mất mạng (BR-10).

→ **Mục 2.3.4, Bảng 2.3**. Mỗi quy tắc đều có test, ví dụ BR-02 và BR-03 ở
`source/backend/tests/test_invitations.py` và `test_projects_and_roles.py`.

### 1.2 Yêu cầu chức năng đầy đủ

**Hỏi: Hệ thống có bao nhiêu yêu cầu? Lấy gì chứng minh đã làm đủ?**
Có 89 yêu cầu chức năng chia 12 nhóm và 12 yêu cầu phi chức năng.

Chứng minh bằng **ma trận truy vết (RTM)**: mỗi yêu cầu được nối tới file code và test kiểm chứng nó.

→ Báo cáo **mục 2.4, Bảng 2.4** và **mục 2.5**. Danh sách đầy đủ ở `documentation/D1-requirements.md`.
Truy vết ở `documentation/D8-rtm.md`.

**Hỏi: Ví dụ một yêu cầu đi từ đặc tả tới test?**
Lấy FR-SCRUM, quy tắc "chỉ một sprint đang chạy":
- đặc tả trong D1;
- tiêu chí nghiệm thu trong `documentation/D5-tests-and-acceptance.md`;
- code ở `source/backend/app/routers/sprints.py` (trả 409 khi đã có sprint chạy);
- test trong `source/backend/tests/test_scrum.py`.

### 1.3 Kiến trúc, CSDL hợp lý

**Hỏi: Kiến trúc tổng thể? Vì sao chọn vậy?**
SPA Vue 3 → nginx → FastAPI → MySQL, cộng với dịch vụ AI (Groq) bên ngoài, đóng gói bằng Docker và
đưa ra internet qua Cloudflare Tunnel. Lý do chọn:
- **Local-first:** thay đổi được ghi vào IndexedDB trước nên giao diện phản hồi tức thì.
- **Server là ranh giới bảo mật duy nhất:** UI ẩn một nút chỉ là tiện ích, không phải phân quyền.

→ **Mục 3.1, Hình 3.1**. Chi tiết ở `documentation/D3-architecture.md`.

**Hỏi: CSDL thiết kế thế nào?**
Có 10 bảng. Ba điểm nên nói:
- `project_members` mang vai trò, nên vai trò thuộc về từng dự án.
- `task_assignees` cho phép một task có nhiều người làm.
- `task_events` lưu lịch sử thay đổi.

Toàn bộ dùng utf8mb4 để tiếng Việt không bị cắt, có khoá ngoại thật. Lược đồ chỉ thay đổi qua
**migration Alembic** có đánh số phiên bản (hiện có 0001 đến 0009).

→ **Mục 3.2, Hình 3.2**. Migration ở `source/backend/migrations/versions/`. Hợp đồng dữ liệu ở
`documentation/D4-api-and-data-contracts.md`.

**Hỏi: API và phân quyền?**
REST, khoảng 50 endpoint. Mọi route thuộc dự án đều gọi `require_member` hoặc `require_project_pm`,
và người ngoài dự án nhận 404 thay vì 403 để không lộ dự án tồn tại.

→ **Mục 3.3, Bảng 3.1** và **mục 3.4**. Code ở `source/backend/app/security.py`.

---

## Tiêu chí 2 — Sản phẩm phần mềm do AI tạo ra

### 2a. Hoàn thiện hệ thống và chức năng AI theo yêu cầu đề tài (2,0 điểm)

**Hỏi: Hệ thống làm được gì? Demo đi.**
Mở https://koshi.huynhca.com, đăng nhập bằng tài khoản `huynh`, `tu` hoặc `don`. Thứ tự demo gợi ý:
1. bảng Kanban, thao tác bằng phím h/j/k/l và Space;
2. chi tiết một task (bình luận, @mention, minh chứng, lịch sử);
3. tab Scrum (Burndown, Velocity, Retro);
4. đồ thị phụ thuộc (DAG);
5. đổi ngôn ngữ Anh/Việt.

→ **Mục 4.2**, có ảnh chụp từng màn hình.

**Hỏi: AI làm những gì?**
Có 5 chức năng:
1. tóm tắt tuần;
2. biên bản họp từ ghi chú thô;
3. gợi ý giao việc theo kỹ năng và tải công việc;
4. chia nhỏ mục tiêu thành task;
5. retrospective sprint từ số liệu thật.

AI trả lời bằng ngôn ngữ đang chọn trên giao diện.

→ **Mục 4.2.6**. Code ở `source/backend/app/services/ai_service.py` và `app/routers/ai.py`.

**Hỏi: AI hỏng hoặc hết quota thì sao?**
Hệ thống có chuỗi dự phòng 3 tầng: Groq trên cloud → Ollama chạy local → câu trả lời tất định dựng
từ dữ liệu. Vì vậy không chức năng nào trả lỗi chỉ vì mô hình không gọi được.

Khi phải dùng dự phòng thì vẫn **nhìn thấy được**: metrics đếm số câu trả lời theo từng tầng.

→ **Mục 3.5, Hình 3.3** và **mục 5.6.3**. Test ở `source/backend/tests/test_ai_cascade.py`.

### 2b. Thiết kế Agent AI cho quy trình SDLC (4,0 điểm)

> Câu mở đầu nên dùng: "Nhóm không dùng AI như một trợ lý chat, mà tổ chức nó thành một dây chuyền:
> agent nhận đúng ngữ cảnh, đi qua các trạm có quyền riêng, bị rào chắn bằng code, và phải qua kiểm
> thử mới được coi là xong." → **Chương 5, Hình 5.1**.

**Hỏi: Context engineering là gì, nhóm làm thế nào?**
Context engineering là cung cấp cho agent đúng thông tin trước khi nó hành động, để nó không phải đoán.

- `CLAUDE.md` được nạp tự động mỗi phiên. Trong đó có lệnh kiểm chứng, các bất biến không được phá,
  và thứ tự đọc tài liệu.
- 8 tài liệu D1–D8, mỗi tài liệu trả lời một câu hỏi của agent. Ví dụ D6 trả lời "tôi có được tự
  làm việc này không?", D8 trả lời "file này phục vụ yêu cầu nào, test nào?".
- Tài liệu được cập nhật **cùng commit** với code, để không bị lỗi thời.

→ **Mục 5.2, Bảng 5.1**. File `CLAUDE.md` và thư mục `documentation/`.

**Hỏi: "Factory" (nhà máy) ở đây là gì?**
Có 6 agent chuyên trách, mỗi agent là một trạm:

phân tích yêu cầu → kiến trúc sư → kỹ sư kiểm thử (viết test trước, test phải đỏ) → lập trình (làm
test xanh) → review → kỹ sư phát hành.

Mỗi trạm có quyền công cụ riêng. Ví dụ trạm review **chỉ được đọc**, và trạm phân tích chỉ được sửa
tài liệu. Lệnh `/feature <mô tả>` chạy cả dây chuyền.

→ **Mục 5.3, Bảng 5.2**. File `.claude/agents/*.md` và `.claude/commands/feature.md`.

Demo: mở Claude Code trong repo, gõ `/feature ...` hoặc `/verify`.

**Hỏi: Rào chắn an toàn (guardrails) là gì?**
Đó là luật của dự án (D6) được viết thành **code chạy trước mỗi lần agent sửa file hay chạy lệnh**,
nên agent không thể bỏ qua như khi chỉ đọc lời dặn. Có ba mức:
- **CẤM:** ghi API key vào code, đọc `.env`, sửa migration đã commit, `git push --force`, lệnh
  deploy kiểu cũ.
- **HỎI người:** sửa phần xác thực, model dữ liệu hay CI, `git push`, deploy.
- **CHO PHÉP kèm nhắc nhở:** các file vùng vàng.

Ngoài ra, khi agent muốn báo "xong" mà đã sửa code nhưng chưa có test hoặc chưa cập nhật tài liệu,
nó bị chặn lại. Nếu chính script rào chắn bị lỗi thì nó từ chối, không để lọt.

→ **Mục 5.4, Hình 5.2, Bảng 5.3**. File `.claude/settings.json`, `.claude/hooks/policy.py` và
`.claude/hooks/guard.py`.

**Hỏi: Có bằng chứng rào chắn hoạt động thật không?**
Có, kể cả hai lần nó chặn **nhầm** chính agent đang làm bài:
1. Một đoạn tài liệu có nhắc tới lệnh deploy cũ bị tưởng là đang chạy lệnh đó.
2. Cờ `-f` của lệnh `pdftotext` bị đọc thành `git push -f`.

Cả hai lần nhóm đều sửa quy tắc và thêm test cho đúng trường hợp đó. Việc này cho thấy rào chắn chạy
thật trên mọi lệnh, và được cải tiến bằng test.

→ **Mục 5.4** ("Lần chặn đầu tiên là chính tác giả"). Ghi chép trong
`documentation/D7-development-book.md`, mục DEC-033.

**Hỏi: Cơ chế bảo mật?**
Có hai lớp:
- **Bảo vệ kho mã:** rào chắn ở trên. Không có bí mật trong code hay trong image Docker; bí mật được
  sinh riêng cho từng máy bằng `scripts/dev-env.sh`.
- **Bảo vệ sản phẩm:**
  - phân quyền phía server trên mọi route, người ngoài nhận 404;
  - khi chạy production, app từ chối khởi động nếu khoá yếu, CORS là `*` hoặc còn tài khoản demo;
  - upload theo danh sách định dạng cho phép, tên file do server sinh;
  - bình luận không bao giờ hiển thị dạng HTML (chống XSS).

→ **Mục 3.4** và **mục 5.4** (đoạn "Bảo mật trong chính sản phẩm"). Test ở
`source/backend/tests/test_projects_and_roles.py` và `test_startup_safety.py`.

**Hỏi: Kiểm thử đơn vị và kiểm thử tích hợp khác nhau thế nào, nhóm có bao nhiêu?**
- **Đơn vị:** kiểm một hàm hoặc module riêng lẻ, không qua mạng.
  - 442 test frontend (Vitest): thuật toán sắp xếp phụ thuộc, đường găng, phím tắt, store…
  - 57 test rào chắn.
- **Tích hợp:** đi qua router thật, CSDL thật và xác thực thật bằng HTTP test client. Có 185 test
  backend (pytest), trong đó các tầng AI được giả lập ở biên HTTP.
- **Đầu-cuối:** script chạy 32 bước trên web thật, gọi cả AI thật.

→ **Mục 5.5, Bảng 5.4** và **mục 4.3, Bảng 4.2**.

Chạy thử:
- `cd source/backend && .venv/bin/pytest -q`
- `pnpm test`
- `source/backend/.venv/bin/python -m pytest -q .claude/hooks`

**Hỏi: Làm sao biết test có tác dụng thật?**
Bằng **kiểm thử đột biến**: cố ý làm hỏng code, ví dụ gỡ quy tắc chặn force-push, rồi xác nhận có
test báo lỗi, sau đó khôi phục. Với rào chắn, gỡ 2 quy tắc làm 5 test thất bại.

CI trên GitHub Actions chạy 3 job (frontend, backend, rào chắn) mỗi lần push.

→ **Mục 5.5**. File `.github/workflows/test.yml`.

**Hỏi: Hệ thống agent có thể "vận hành như nhà máy" đến mức nào? Hạn chế?**
Nên trả lời trung thực, vì đây là điểm cộng:
- Cổng kết thúc chỉ kiểm tra rằng test và tài liệu **có được sửa**, chứ không kiểm tra chúng đúng.
  Việc đó là của trạm review và của con người.
- Hook chỉ ràng buộc agent. Vì vậy CI chạy lại mọi bộ test một cách độc lập.

→ **Mục 5.7**.

### 2c. Đóng gói, vận hành và theo dõi sản phẩm (1,0 điểm)

**Hỏi: Đóng gói thế nào?**
Docker Compose với 4 container: MySQL, backend, nginx kèm frontend, và cloudflared. Image không chứa
bí mật vì `.dockerignore` loại `.env`, và script deploy kiểm tra lại image sau khi build.

→ **Mục 5.6.1, mục 4.4**. File `docker-compose.prod-local.yml` và `scripts/deploy.sh`.

**Hỏi: Vận hành thế nào?**
`./scripts/local-prod.sh up` làm lần lượt:
1. chạy migration ở một bước riêng;
2. khởi động stack với kiểm tra an toàn production được bật;
3. xác minh không có tài khoản demo, CORS cố định, lược đồ ở phiên bản mới nhất.

Docker tự khởi động lại container bị dừng, log bị giới hạn dung lượng. Bản công khai đưa ra internet
qua Cloudflare Tunnel, không phải mở cổng router.

→ **Mục 5.6.2**.

**Hỏi: Theo dõi (monitoring) thế nào?**
Có ba tín hiệu:
- `/api/health` kiểm tra cả CSDL và trả 503 khi CSDL chết. Docker healthcheck dùng endpoint này.
- Mỗi request có `X-Request-ID` và một dòng log.
- `/api/metrics` theo chuẩn Prometheus, cần token: số request, độ trễ, và **số câu trả lời AI theo
  tầng**. Nếu tầng dự phòng tăng vọt nghĩa là Groq đang hỏng.

`./scripts/monitor.sh` gộp ba tín hiệu này lại và tự cảnh báo.

→ **Mục 5.6.3**. Code ở `source/backend/app/services/monitoring.py`, test ở
`source/backend/tests/test_monitoring.py`.

Demo trên máy chạy server:
```
set -a; . ./.env; set +a; ./scripts/monitor.sh
```
Kết quả có dạng: `health HTTP 200 … requests N total, 0 server errors … AI answers N, 0 from the
offline fallback`.

---

## Bảng tra nhanh

| Tiêu chí | Điểm | Báo cáo | Repo |
|:--|:--:|:--|:--|
| 1.1 Nghiệp vụ | 3,0 (cả mục 1) | 2.1, 2.2, 2.3 | `documentation/D1` |
| 1.2 Yêu cầu chức năng | | 2.4, 2.5 | `D1`, `D8-rtm.md` |
| 1.3 Kiến trúc, CSDL | | 3.1–3.6 | `D3`, `D4`, `migrations/versions/` |
| 2 · Hệ thống + AI | 2,0 | 3.5, 4.2, 4.3 | `ai_service.py`, https://koshi.huynhca.com |
| 2 · Agent AI cho SDLC | 4,0 | Chương 5 (5.1–5.5, 5.7) | `CLAUDE.md`, `.claude/`, `documentation/` |
| 2 · Đóng gói, vận hành, theo dõi | 1,0 | 4.4, 5.6 | `docker-compose.prod-local.yml`, `scripts/local-prod.sh`, `scripts/monitor.sh` |
