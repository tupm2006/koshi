# KOSHI PROJECT MANAGEMENT ENGINE
# DEFECT & DISCREPANCY TRACKING REPORT (BUG REPORT)

**Document ID:** KOSHI-QA-BUGREPORT-2026-V1.0  
**Target System:** KOSHI Local-First Project Management System  
**QA Team & Authorship:** Nhóm 04 (ICTU) — Phạm Minh Tú, Phạm Văn Huynh, Đàm Đức Đôn  
**Date:** September 30, 2026  
**Policy:** KHÔNG sửa mã nguồn sản phẩm để test pass. Mọi khiếm khuyết được đánh dấu `xfail`/`test.fail` và phân loại rõ ràng.

---

## 1. PHÂN LOẠI KHIẾM KHUYẾT (DEFECT CLASSIFICATION TAXONOMY)

- **Code bug:** Lỗi logic, ngoại lệ không bắt được, thiếu hoàn tác dữ liệu (rollback), hoặc vi phạm hành vi đã được thống nhất trong thiết kế mã nguồn.
- **Spec conflict:** Xung đột hoặc mâu thuẫn giữa các tài liệu đặc tả (URD, SRS, README, user_story.md) hoặc giữa tài liệu đặc tả và mã nguồn thực tế.
- **Doc inconsistency:** Sự thiếu đồng bộ, typo hoặc mô tả sai lệch trong tài liệu hướng dẫn so với hiện trạng hệ thống.

---

## 2. BẢNG THEO DÕI KHIẾM KHUYẾT & SAI LỆCH (DEFECT TRACKING MATRIX)

| Bug ID | Tiêu đề | Loại | Mức độ | File liên quan | Mô tả tóm tắt | Trạng thái |
| :--- | :--- | :---: | :---: | :--- | :--- | :---: |
| **BUG-01** | Phím tắt tạo task: `c` (Spec) vs `n` (Code) | **Spec conflict** | High | `source_code/frontend/src/lib/keyboard.ts` | README, URD-FR-02 và Prompt quy định phím `c` tạo task. Code hiện tại bind phím `n` (`case 'n': // overhauls 'c'`), phím `c` không hoạt động. | Open (xfail in test) |
| **BUG-02** | Xung đột hành vi phím `Enter` | **Spec conflict** | High | `source_code/frontend/src/lib/keyboard.ts`, `README.md` | README & URD-FR-02 quy định `Enter` sửa tiêu đề inline. Nhưng user_story US-03 và code `keyboard.ts` lại dùng `Enter` mở Task Detail Modal (và dùng `i` sửa inline). | Open (xfail for URD inline test) |
| **BUG-03** | Sai lệch trọng số & công thức Critical Path | **Spec conflict** | Medium | `source_code/frontend/src/lib/dagSorter.ts`, `SRS.md` | SRS-FR-09 quy định trọng số complexity: S=1, M=2, L=3, XL=5. Code `dagSorter.ts` đang gán `{XL:8, L:5, M:3, S:1}` và nhân thêm `priorityWeight`. | Open (xfail for SRS pure weight test) |
| **BUG-04** | Thiếu cơ chế Rollback trong `taskStore.updateTask` | **Code bug** | High | `source_code/frontend/src/stores/taskStore.ts` | Khi API backend trả về lỗi (500/timeout), `taskStore.updateTask` bắt lỗi qua `.catch(() => {})` mà không hoàn tác (revert) dữ liệu cũ trong `this.tasks`. | Open (xfail in test) |
| **BUG-05** | Typo vòng lặp trạng thái trong CLAUDE.md | **Doc inconsistency** | Low | `CLAUDE.md` | Dòng 19 ghi `TODO -> IN_PROGRESS -> DONE -> BLOCKED -> TODO`, trong khi tất cả URD, SRS, README, code client/server đều là `TODO -> IN_PROGRESS -> BLOCKED -> DONE -> TODO`. | Open |

---

## 3. CHI TIẾT CÁC KHIẾM KHUYẾT

### BUG-01: Phím tắt tạo task `c` bị đổi thành `n` trong code
- **Loại:** Spec conflict
- **Mức độ nghiêm trọng:** High (Ảnh hưởng trải nghiệm người dùng theo tài liệu hướng dẫn)
- **File liên quan:** `source_code/frontend/src/lib/keyboard.ts` (dòng 155-158)
- **Các bước tái hiện:**
  1. Mở màn hình chính Table hoặc Kanban.
  2. Không focus vào bất kỳ ô nhập liệu nào.
  3. Nhấn phím `c`.
- **Kết quả thực tế:** Không có phản hồi nào, Create Task Modal không mở.
- **Kết quả mong đợi (theo README & URD-FR-02):** Modal tạo task phải mở ngay lập tức.
- **Ghi chú QA:** Trong code đang có chú thích `case 'n': // 'n': Create task (overhauls 'c')`. Test case `TC-KB-09` sẽ test phím `c` và đánh dấu `xfail`.

---

### BUG-02: Xung đột hành vi phím `Enter` (Inline edit vs Detail Modal)
- **Loại:** Spec conflict
- **Mức độ nghiêm trọng:** High
- **File liên quan:** `source_code/frontend/src/lib/keyboard.ts` (dòng 128-140), `README.md`, `user_story.md`
- **Mô tả:**
  - `README.md` (mục 4.1) và `URD.md` (URD-FR-02): `Enter` kích hoạt "Inline title edit mode".
  - `user_story.md` (US-03): "When I press Enter, the Task Detail Inspector opens".
  - `keyboard.ts`: `Enter` mở Task Detail Modal (`taskStore.openDetail()`), trong khi phím `i` kích hoạt inline edit (`taskStore.startEditing()`).
- **Ghi chú QA:** Tách thành 2 test case: `TC-KB-07a` (mở modal theo US-03 $\to$ Pass) và `TC-KB-07b` (sửa inline theo URD $\to$ xfail).

---

### BUG-03: Trọng số tính toán Critical Path sai lệch so với SRS-FR-09
- **Loại:** Spec conflict
- **Mức độ nghiêm trọng:** Medium
- **File liên quan:** `source_code/frontend/src/lib/dagSorter.ts` (dòng 84-98), `SRS.md` (§3.3)
- **Mô tả:**
  - `SRS.md` và User prompt quy định trọng số độ phức tạp duy nhất: $S=1, M=2, L=3, XL=5$.
  - `dagSorter.ts` cài đặt: `complexityWeight = { XL: 8, L: 5, M: 3, S: 1 }` và nhân thêm `priorityWeight = { CRITICAL: 10, HIGH: 5, MEDIUM: 2, LOW: 1 }`.
- **Kết quả thực tế vs Mong đợi:** Đồ thị có các task cùng complexity nhưng khác priority sẽ cho ra đường găng khác với công thức thuần túy của SRS.
- **Ghi chú QA:** Test `TC-DAG-07` kiểm tra công thức spec chuẩn đánh dấu `xfail`.

---

### BUG-04: Thiếu cơ chế hoàn tác (Rollback) khi API cập nhật task thất bại
- **Loại:** Code bug
- **Mức độ nghiêm trọng:** High (Rủi ro mất tính toàn vẹn dữ liệu client-server)
- **File liên quan:** `source_code/frontend/src/stores/taskStore.ts` (dòng 563-576)
- **Các bước tái hiện:**
  1. Client kết nối tới backend.
  2. Sửa tiêu đề hoặc priority của một task. Store cập nhật local optimistic ngay lập tức.
  3. API backend trả về lỗi HTTP 500 hoặc rớt mạng.
- **Kết quả thực tế:** Hàm `api.updateTask` bị lỗi rơi vào `.catch(() => {})`, store không revert lại giá trị cũ của task.
- **Kết quả mong đợi:** Store phải khôi phục trạng thái snapshot trước khi mutate và hiển thị cảnh báo lỗi/offline.
- **Ghi chú QA:** Test case `TC-STORE-05` đánh dấu `xfail`.

---

### BUG-05: Typo vòng lặp trạng thái trong CLAUDE.md
- **Loại:** Doc inconsistency
- **Mức độ nghiêm trọng:** Low
- **File liên quan:** `CLAUDE.md` (dòng 19)
- **Mô tả:** `CLAUDE.md` viết nhầm `TODO -> IN_PROGRESS -> DONE -> BLOCKED -> TODO`. Tất cả tài liệu còn lại và mã nguồn thực tế đều là `TODO -> IN_PROGRESS -> BLOCKED -> DONE -> TODO`.
