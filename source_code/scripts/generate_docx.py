import os
import shutil
import sys
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

SRC = os.path.expanduser("~/Documents/BAI DU AN_UNG DUNG AI.docx")
DST = os.path.expanduser("~/koshi/nhom4.docx")

if not os.path.exists(SRC):
    print(f"[!] Error: Template file missing at {SRC}", file=sys.stderr)
    sys.exit(1)

# 1. Clone template binary directly to preserve embedded ICTU logo and geometry
shutil.copyfile(SRC, DST)
print(f"[*] Cloned binary template: {SRC} -> {DST}")

doc = Document(DST)

def set_font(run, size=13, bold=False, italic=False, color=(0x1E, 0x29, 0x3B)):
    run.font.name = 'Times New Roman'
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(*color)

def add_clean_p(target_p, text="", bold_prefix="", bullet=False, space_before=2, space_after=4):
    p = target_p.insert_paragraph_before()
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    if bullet:
        p.paragraph_format.left_indent = Inches(0.25)
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        set_font(r_pre, size=13, bold=True)
    if text:
        r_txt = p.add_run(text)
        set_font(r_txt, size=13)
    return p

def add_heading2(target_p, title):
    p = target_p.insert_paragraph_before()
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(title)
    set_font(r, size=13.5, bold=True, color=(0x0F, 0x17, 0x2A))
    return p

def replace_in_runs(container, search_str, replace_str):
    if hasattr(container, "paragraphs"):
        for p in container.paragraphs:
            replace_in_runs(p, search_str, replace_str)
    elif hasattr(container, "text"):
        if search_str in container.text:
            for r in getattr(container, "runs", []):
                if search_str in r.text:
                    r.text = r.text.replace(search_str, replace_str)
                    return
            container.text = container.text.replace(search_str, replace_str)

def delete_paragraph(p):
    """Physically removes the paragraph XML node from the document tree."""
    p_elem = p._element
    if p_elem.getparent() is not None:
        p_elem.getparent().remove(p_elem)

# -----------------------------------------------------------------------------
# 2. UPDATE COVER METADATA & TABLES
# -----------------------------------------------------------------------------
METADATA = [
    ("HỆ THỐNG QUẢN LÝ BÁN HÀNG CÓ TÍCH HỢP AI", "HỆ THỐNG QUẢN LÝ DỰ ÁN VÀ TIẾN ĐỘ CÔNG VIỆC KOSHI CÓ TÍCH HỢP AI"),
    ("Hệ thống quản lý bán hàng có tích hợp AI", "Hệ thống quản lý dự án và tiến độ công việc Koshi có tích hợp AI"),
    ("NHÓM 01", "NHÓM 04"),
    ("Nhóm 01", "Nhóm 04"),
    ("Lương Văn Trà (#)", "Phạm Minh Tú (#)"),
    ("Lương Văn Trà", "Phạm Minh Tú"),
    ("Tráng A Thư", "Phạm Văn Huynh"),
    ("Nguyễn Mạnh Dương", "Đàm Đức Đôn"),
]

for p in doc.paragraphs:
    for old_s, new_s in METADATA:
        replace_in_runs(p, old_s, new_s)

for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for old_s, new_s in METADATA:
                replace_in_runs(cell, old_s, new_s)

# Populate Table 1 (All 8 rows) and Table 2
for table in doc.tables:
    t_text = " ".join(c.text for row in table.rows for c in row.cells)
    if "Tên nhiệm vụ" in t_text and "Người thực hiện" in t_text:
        tasks = [
            ("1", "Khảo sát hiện trạng, phân tích yêu cầu nghiệp vụ và bài toán AI", "Phạm Minh Tú"),
            ("2", "Xây dựng tài liệu URD, SRS chuẩn ISO/IEC/IEEE 29148", "Phạm Minh Tú"),
            ("3", "Thiết kế mô hình Actor, phân hệ Use Case và đặc tả chức năng (FR)", "Phạm Minh Tú"),
            ("4", "Phân tích đặc tả yêu cầu phi chức năng (NFR) và ràng buộc hệ thống", "Phạm Văn Huynh"),
            ("5", "Thiết kế sơ bộ thực thể dữ liệu và phân quyền theo dự án", "Phạm Văn Huynh"),
            ("6", "Khảo sát mô hình ngôn ngữ lớn (LLM) và thiết kế phạm vi tích hợp AI", "Đàm Đức Đôn"),
            ("7", "Xây dựng kịch bản thử nghiệm và ma trận đánh giá ban đầu", "Đàm Đức Đôn"),
            ("8", "Tổng hợp báo cáo kỹ thuật Chương 1 (KT1) và rà soát tài liệu", "Cả nhóm")
        ]
        for idx, (stt, tname, assignee) in enumerate(tasks, start=1):
            if idx < len(table.rows):
                row = table.rows[idx]
                if len(row.cells) >= 3:
                    row.cells[0].paragraphs[0].text = stt
                    row.cells[1].paragraphs[0].text = tname
                    row.cells[2].paragraphs[0].text = assignee

    elif "Thành Viên" in t_text and "Chữ ký" in t_text:
        members = [
            ("1", "Phạm Minh Tú (#)", "Trưởng nhóm: Phân tích yêu cầu hệ thống, mô hình Use Case, URD/SRS ISO standard và điều phối kỹ thuật.", ""),
            ("2", "Phạm Văn Huynh", "Phụ trách khảo sát hiện trạng, phân tích yêu cầu phi chức năng và thiết kế sơ bộ thực thể CSDL.", ""),
            ("3", "Đàm Đức Đôn", "Phụ trách xác định phạm vi tích hợp AI, khảo sát mô hình LLM và tổng hợp báo cáo kỹ thuật.", "")
        ]
        for idx, (stt, name, desc, sig) in enumerate(members, start=1):
            if idx < len(table.rows):
                row = table.rows[idx]
                if len(row.cells) >= 4:
                    row.cells[0].paragraphs[0].text = stt
                    row.cells[1].paragraphs[0].text = name
                    row.cells[2].paragraphs[0].text = desc
                    row.cells[3].paragraphs[0].text = sig

# -----------------------------------------------------------------------------
# 3. LOCATE BOUNDARIES AND CLEANLY STRIP CD NOTES & OLD PLACEHOLDERS
# -----------------------------------------------------------------------------
all_paragraphs = list(doc.paragraphs)
intro_end_p = None
ch1_p = None
ch2_p = None

for idx, p in enumerate(all_paragraphs):
    if "Em xin chân thành cảm ơn!" in p.text:
        intro_end_p = p
    elif "CHƯƠNG 1" in p.text.upper() and idx > 20:
        ch1_p = p
    elif "CHƯƠNG 2" in p.text.upper() and idx > 20 and ch1_p is not None:
        ch2_p = p
        break

if not intro_end_p or not ch1_p or not ch2_p:
    print("[!] Critical Error: Unable to locate body boundary headings.", file=sys.stderr)
    sys.exit(1)

# Delete all CD disc / label paragraphs between Mở đầu and Chapter 1
collecting_cd = False
to_delete_cd = []
for p in all_paragraphs:
    if p == intro_end_p:
        collecting_cd = True
        continue
    if p == ch1_p:
        break
    if collecting_cd:
        to_delete_cd.append(p)

for p in to_delete_cd:
    delete_paragraph(p)

# Delete all original placeholder paragraphs strictly between Chapter 1 and Chapter 2
collecting_ch1 = False
to_delete_ch1 = []
for p in all_paragraphs:
    if p == ch1_p:
        collecting_ch1 = True
        continue
    if p == ch2_p:
        break
    if collecting_ch1:
        to_delete_ch1.append(p)

for p in to_delete_ch1:
    delete_paragraph(p)

# Update Introduction Body
for idx, p in enumerate(doc.paragraphs):
    if p.text.strip() == "MỞ ĐẦU" and idx > 10:
        for next_idx in range(idx + 1, min(idx + 5, len(doc.paragraphs))):
            np = doc.paragraphs[next_idx]
            if "Ngày nay" in np.text:
                np.text = (
                    "Ngày nay, công nghệ thông tin phát triển đồng nghĩa với việc tối ưu hóa năng suất lao động "
                    "và tự động hóa quy trình quản trị dự án. Trong phát triển phần mềm hiện đại, việc kiểm soát "
                    "tiến độ sprint và chuỗi phụ thuộc kỹ thuật đóng vai trò then chốt đối với sự thành bại của hệ thống."
                )
            elif "…" in np.text:
                np.text = (
                    "Hệ thống quản lý dự án Koshi (輿) được thiết kế theo triết lý 'Local-First' và điều hướng bàn phím "
                    "tối ưu (Vim ergonomics), mang lại phản hồi < 16ms cùng trợ lý AI tự động hóa tóm tắt tiến độ, trích xuất "
                    "biên bản họp và cân bằng tải nhân sự."
                )
            elif "Em xin chân thành cảm ơn!" in np.text:
                np.text = "Nhóm 04 chúng em xin chân thành cảm ơn giảng viên ThS. Nguyễn Thị Tuyển đã tận tình hướng dẫn để nhóm hoàn thành tốt Bài kiểm tra 1 (KT1) này!"
                break
        break

# -----------------------------------------------------------------------------
# 4. INSERT STRUCTURED CHAPTER 1 CONTENT BEFORE CHAPTER 2
# -----------------------------------------------------------------------------
ch1_p.text = "CHƯƠNG 1. PHÂN TÍCH YÊU CẦU HỆ THỐNG"

# 1.1
add_heading2(ch2_p, "1.1. Bối cảnh bài toán và lý do phát triển")
add_clean_p(ch2_p, "Koshi được định vị là hệ thống quản lý công việc và tiến độ sprint nội bộ dành cho các đội ngũ kỹ sư phần mềm chuyên sâu. Bối cảnh nghiệp vụ tập trung giải quyết nhu cầu của 3 nhóm đối tượng chính (User Personas):")
add_clean_p(ch2_p, "Đòi hỏi thao tác 100% bằng bàn phím không dùng chuột (h/j/k/l, Space, i, n, Esc), chuyển đổi tức thì giữa dạng Bảng (Table) và Kanban 2D, phát hiện sớm các điểm nghẽn tiến độ (Critical Path) trên đồ thị phụ thuộc.", bold_prefix="• Lead Architect / Senior Engineer: ", bullet=True)
add_clean_p(ch2_p, "Cần tự động hóa khâu lập báo cáo tiến độ tuần, tự động trích xuất đầu việc từ biên bản họp văn bản thô và nhận gợi ý phân công công việc dựa trên số điểm độ phức tạp (WIP story points) của từng kỹ sư.", bold_prefix="• Project Manager (PM) / Tech Lead: ", bullet=True)
add_clean_p(ch2_p, "Cần khả năng làm việc ngoại tuyến (Offline-first) khi mất kết nối mạng và đồng bộ tự động dữ liệu vào IndexedDB cục bộ với độ trễ phản hồi giao diện dưới 16ms.", bold_prefix="• Field / Mobile Developer: ", bullet=True)

# 1.2
add_heading2(ch2_p, "1.2. Khảo sát hiện trạng và các giải pháp tương tự")
add_clean_p(ch2_p, "Khảo sát đối chuẩn giữa Koshi và các hệ thống quản lý dự án hàng đầu hiện nay:")
add_clean_p(ch2_p, "Hệ thống hoàn chỉnh nhưng cồng kềnh, thời gian phản hồi giao diện chậm, phụ thuộc 100% vào kết nối mạng, thao tác bàn phím hạn chế.", bold_prefix="• Jira Software: ", bullet=True)
add_clean_p(ch2_p, "Trực quan, đơn giản nhưng thiếu khả năng phân tích đồ thị phụ thuộc DAG, không tối ưu cho luồng làm việc kỹ thuật cao.", bold_prefix="• Trello: ", bullet=True)
add_clean_p(ch2_p, "Giao diện hiện đại, hỗ trợ phím tắt tốt nhưng chưa hỗ trợ phân rã mục tiêu chuyên sâu bằng AI và không có cơ chế phân tích đường găng CPM tự động.", bold_prefix="• Linear: ", bullet=True)
add_clean_p(ch2_p, "Kết hợp triết lý Local-First, điều hướng bàn phím 2D (Vim ergonomics), phân tích chuỗi phụ thuộc bằng giải thuật Kahn kết hợp 3 luồng trợ lý AI quản trị dự án có cơ chế dự phòng 3 tầng.", bold_prefix="• Koshi (Hệ thống đề xuất): ", bullet=True)

# 1.3
add_heading2(ch2_p, "1.3. Mô hình Actor và Phân hệ Use Case tổng quát")
add_clean_p(ch2_p, "Hệ thống phân cấp 3 nhóm tác nhân (Actors) với các phân hệ Use Case chính:")
add_clean_p(ch2_p, "Đăng ký tài khoản mới, Đăng nhập hệ thống qua Email/Mật khẩu hoặc Google OAuth2, Xem dữ liệu mẫu thử nghiệm.", bold_prefix="1. Guest (Khách vãng lai): ", bullet=True)
add_clean_p(ch2_p, "Duyệt bảng công việc (Table/Kanban), Chuyển trạng thái vòng tròn (Space), Chỉnh sửa chi tiết công việc (i/Esc), Tạo công việc mới (n), Phân rã mục tiêu bằng AI, Bóc tách Git Diff để tự động đóng ticket.", bold_prefix="2. Team Member (Lập trình viên): ", bullet=True)
add_clean_p(ch2_p, "Quản trị thành viên dự án qua project_members, Sinh Báo cáo tổng kết tuần (AI Weekly Summary), Bóc tách biên bản họp (AI Meeting Minutes), Cân bằng tải nhân sự (AI Smart Assignment) và trực quan hóa chuỗi phụ thuộc đồ thị (DAG Visualizer).", bold_prefix="3. Project Manager (Quản lý dự án): ", bullet=True)

# 1.4
add_heading2(ch2_p, "1.4. Đặc tả yêu cầu chức năng cốt lõi (Functional Requirements)")
add_clean_p(ch2_p, "Chuyển đổi giao diện tức thì giữa Table View mật độ cao và Kanban Board 2D qua phím tắt 'b' với thời gian < 16ms.", bold_prefix="• FR-01 [Dual-Mode Views]: ", bullet=True)
add_clean_p(ch2_p, "Hỗ trợ điều hướng bàn phím đầy đủ: j/k duyệt dòng trong Table, h/j/k/l duyệt lưới Kanban, Space đổi trạng thái tuần hoàn (TODO -> IN_PROGRESS -> BLOCKED -> DONE -> TODO).", bold_prefix="• FR-02 [Vim Spatial Navigation]: ", bullet=True)
add_clean_p(ch2_p, "Phím Enter mở modal chi tiết, phím 'i' chuyển sang Edit Mode cho phép chỉnh sửa toàn bộ thuộc tính, phím Escape lưu thay đổi và thoát Edit Mode.", bold_prefix="• FR-03 [Task Detail Inspector]: ", bullet=True)
add_clean_p(ch2_p, "Bắt sự kiện Escape ở mức window capture phase để đảm bảo đóng modal hoặc hủy chế độ sửa ngay lập tức mà không bị nuốt bởi ô nhập văn bản.", bold_prefix="• FR-04 [Capture-Phase Escape Trap]: ", bullet=True)
add_clean_p(ch2_p, "Tách biệt quyền hạn theo từng dự án cụ thể thông qua bảng project_members. Cho phép tìm kiếm người dùng trong hệ thống để thêm vào dự án với vai trò OWNER, PM hoặc MEMBER.", bold_prefix="• FR-05 [Project-Scoped RBAC]: ", bullet=True)
add_clean_p(ch2_p, "Sử dụng giải thuật Kahn để phân tích chuỗi phụ thuộc, phát hiện vòng lặp chu trình (Cycle Detection) và tính toán đường găng (Critical Path) cảnh báo điểm nghẽn.", bold_prefix="• FR-06 [Topological DAG & CPM]: ", bullet=True)
add_clean_p(ch2_p, "Tích hợp 3 chức năng AI chuyên sâu: Tóm tắt tiến độ tuần (3 phần Overview, Blockers, Priorities), Bóc tách biên bản họp ra Action Items, và Gợi ý phân bổ công việc theo kỹ năng và tải trọng WIP.", bold_prefix="• FR-07 [Autonomous AI PM Workflows]: ", bullet=True)
add_clean_p(ch2_p, "Cho phép tạo công việc mới trực tiếp ở trạng thái DONE để hỗ trợ ghi nhận các tác vụ đột xuất hoặc hotfix mà không cần qua trạng thái trung gian.", bold_prefix="• FR-08 [Retrospective Work Logging]: ", bullet=True)

# 1.5
add_heading2(ch2_p, "1.5. Đặc tả yêu cầu phi chức năng (Non-Functional Requirements)")
add_clean_p(ch2_p, "Mọi thao tác điều hướng bàn phím và render giao diện cục bộ phải phản hồi trong thời gian < 16ms (tương đương 60fps).", bold_prefix="• NFR-01 [Hiệu năng & Độ trễ]: ", bullet=True)
add_clean_p(ch2_p, "Hệ thống CSDL SQLite phải được cấu hình PRAGMA journal_mode = WAL và busy_timeout = 30000ms nhằm đảm bảo không bị lỗi khóa ghi khi nhiều người dùng thao tác đồng thời.", bold_prefix="• NFR-02 [Độ tin cậy & Concurrency]: ", bullet=True)
add_clean_p(ch2_p, "Mật khẩu người dùng được băm an toàn bằng Bcrypt. Xác thực API sử dụng JWT HS256. Xác thực Google OAuth2 kiểm tra chữ ký mật mã nghiêm ngặt.", bold_prefix="• NFR-03 [Bảo mật & Xác thực]: ", bullet=True)
add_clean_p(ch2_p, "Luồng gọi AI áp dụng cơ chế Cascade 3 tầng (Cloud LLM -> Local Ollama -> Heuristic Rule Engine), đảm bảo hệ thống luôn trả về dữ liệu JSON hợp lệ ngay cả khi mất kết nối Internet.", bold_prefix="• NFR-04 [Khả năng phục hồi AI]: ", bullet=True)
add_clean_p(ch2_p, "Giao diện tuân thủ bảng màu Slate đơn sắc có độ tương phản cao, chuyển đổi Light/Dark mode với độ trễ 0ms.", bold_prefix="• NFR-05 [Độ tương phản & Công thái học]: ", bullet=True)
add_clean_p(ch2_p, "Bật cơ chế PRAGMA foreign_keys = ON trên toàn bộ kết nối cơ sở dữ liệu để đảm bảo các ràng buộc khóa ngoại và xóa xếp tầng (CASCADE) hoạt động chính xác.", bold_prefix="• NFR-06 [Tính toàn vẹn dữ liệu]: ", bullet=True)

# 1.6
add_heading2(ch2_p, "1.6. Xác định bài toán ứng dụng AI và phạm vi tích hợp")
add_clean_p(ch2_p, "Trong khuôn khổ đề tài, Koshi tập trung ứng dụng các mô hình ngôn ngữ lớn (LLMs) vào 3 bài toán xử lý ngôn ngữ tự nhiên then chốt:")
add_clean_p(ch2_p, "Tổng hợp dữ liệu trạng thái công việc trong sprint thành báo cáo súc tích 3 phần (Tổng quan, Điểm nghẽn tiến độ, Ưu tiên tiếp theo).", bold_prefix="1. Bài toán Tóm tắt văn bản có cấu trúc (Structured Summarization): ", bullet=True)
add_clean_p(ch2_p, "Phân tích văn bản thô từ biên bản cuộc họp để trích xuất danh sách công việc, người chịu trách nhiệm, độ ưu tiên và thời hạn bàn giao.", bold_prefix="2. Bài toán Trích xuất thông tin thực thể (Information Extraction): ", bullet=True)
add_clean_p(ch2_p, "Đánh giá ma trận kỹ năng và số điểm độ phức tạp công việc đang thực hiện (WIP points) để đề xuất lập trình viên phù hợp nhất.", bold_prefix="3. Bài toán Tối ưu hóa phân bổ nguồn lực (Capacity Optimization): ", bullet=True)

# Keep Chapter 2 heading clean in body
ch2_p.text = "CHƯƠNG 2. THIẾT KẾ HỆ THỐNG (BÀI KIỂM TRA 2)"

doc.save(DST)
print(f"[✓] Successfully compiled in-place with discrete paragraphs and clean TOC: {DST}")

if __name__ == "__main__":
    pass
