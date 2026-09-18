#!/usr/bin/env python3
"""
Script to compile nhom4.docx for Skill Test 2 (KT2).
Clones /home/felixsu/Documents/BAI DU AN_UNG DUNG AI.docx, updates metadata/tables,
and bounds content strictly to Chapter 2.
"""

import os
import shutil
import sys
import docx
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
SRC = os.path.expanduser("~/Documents/BAI DU AN_UNG DUNG AI.docx")
DST = os.path.join(REPO_ROOT, "nhom4.docx")

if not os.path.exists(SRC):
    print(f"[!] Error: Template document not found at {SRC}", file=sys.stderr)
    sys.exit(1)

# 1. Clone template binary directly to preserve original styles, margins, and geometry
shutil.copyfile(SRC, DST)
print(f"[*] Cloned template: {SRC} -> {DST}")

doc = Document(DST)
body = doc.element.body

def set_font(run, size=13, bold=False, italic=False, color=(0x1E, 0x29, 0x3B)):
    run.font.name = 'Times New Roman'
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(*color)

def delete_paragraph(p):
    p_elem = p._element
    if p_elem.getparent() is not None:
        p_elem.getparent().remove(p_elem)

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

def add_body_p(text="", bold_prefix="", bullet=False, space_before=2, space_after=4):
    p = doc.add_paragraph()
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

def add_body_h2(title):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(title)
    set_font(r, size=13.5, bold=True, color=(0x0F, 0x17, 0x2A))
    return p

# -----------------------------------------------------------------------------
# 2. UPDATE COVER PAGE METADATA (Table 0 & Cover paragraphs)
# -----------------------------------------------------------------------------
COVER_REPLACEMENTS = [
    ("HỆ THỐNG QUẢN LÝ BÁN HÀNG CÓ TÍCH HỢP AI", "HỆ THỐNG QUẢN LÝ DỰ ÁN VÀ TIẾN ĐỘ KOSHI CÓ TÍCH HỢP AI"),
    ("Hệ thống quản lý bán hàng có tích hợp AI", "Hệ thống quản lý dự án và tiến độ Koshi có tích hợp AI"),
    ("NHÓM 01", "NHÓM 04"),
    ("Nhóm 01", "Nhóm 04"),
    ("Lương Văn Trà (#)", "Phạm Minh Tú (#)"),
    ("Lương Văn Trà", "Phạm Minh Tú"),
    ("Tráng A Thư", "Phạm Văn Huynh"),
    ("Nguyễn Mạnh Dương", "Đàm Đức Đôn")
]

for p in doc.paragraphs:
    for s, r in COVER_REPLACEMENTS:
        if s in p.text:
            p.text = p.text.replace(s, r)

t0 = doc.tables[0]
for row in t0.rows:
    for cell in row.cells:
        for s, r in COVER_REPLACEMENTS:
            if s in cell.text:
                for p in cell.paragraphs:
                    if s in p.text:
                        p.text = p.text.replace(s, r)

for row in t0.rows:
    for cell in row.cells:
        for p in cell.paragraphs:
            for run in p.runs:
                run.font.name = 'Times New Roman'

# -----------------------------------------------------------------------------
# 3. POPULATE MEMBER ALLOCATION TABLES (Table 1 & Table 2)
# -----------------------------------------------------------------------------
# Table 1: Progress (Strictly 3 rows for KT2)
t1 = doc.tables[1]
tasks_kt2 = [
    ("1", "Hiện thực hóa kiến trúc API Core FastAPI, phân quyền RBAC đa cấp độ, giải thuật Kahn DAG và tính toán đường găng Critical Path (CPM)", "Phạm Minh Tú"),
    ("2", "Hiện thực hóa cơ sở dữ liệu SQLite WAL, toàn bộ hệ thống API CRUD, avatar streaming và bộ kiểm thử tự động Pytest (68 tests)", "Phạm Văn Huynh"),
    ("3", "Hiện thực hóa kiến trúc AI Cascade 3 tầng, thiết kế và tối ưu ma trận Prompts, giao diện Vue 3 SPA và bộ kiểm thử Vitest (16 tests)", "Đàm Đức Đôn")
]

while len(t1.rows) > len(tasks_kt2) + 1:
    tr = t1.rows[-1]._tr
    tr.getparent().remove(tr)

for idx, (stt, tname, assignee) in enumerate(tasks_kt2, start=1):
    row = t1.rows[idx]
    row.cells[0].paragraphs[0].text = stt
    row.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(row.cells[0].paragraphs[0].runs[0], size=13)
    row.cells[1].paragraphs[0].text = tname
    row.cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
    set_font(row.cells[1].paragraphs[0].runs[0], size=13)
    row.cells[2].paragraphs[0].text = assignee
    row.cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
    set_font(row.cells[2].paragraphs[0].runs[0], size=13)

# Table 2: Responsibilities
t2 = doc.tables[2]
members_kt2 = [
    ("1", "Phạm Minh Tú (#)", "Trưởng nhóm: Chịu trách nhiệm kiến trúc tổng thể FastAPI Core, mô hình toán học Kahn DAG & đường găng CPM, phân quyền RBAC đa cấp độ, điều phối kỹ thuật.", ""),
    ("2", "Phạm Văn Huynh", "Phụ trách phát triển API CRUD, module avatar streaming/profile, kiểm thử tự động backend Pytest (68 tests) và bảo đảm toàn vẹn CSDL SQLite WAL.", ""),
    ("3", "Đàm Đức Đôn", "Phụ trách giao diện Vue 3 SPA, điều hướng bàn phím Vim ergonomics, bẫy phím Escape capture-phase, xây dựng cơ chế AI Cascade 3 tầng và kiểm thử Vitest (16 tests).", "")
]

while len(t2.rows) > len(members_kt2) + 1:
    tr = t2.rows[-1]._tr
    tr.getparent().remove(tr)

for idx, (stt, name, desc, sig) in enumerate(members_kt2, start=1):
    row = t2.rows[idx]
    row.cells[0].paragraphs[0].text = stt
    row.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(row.cells[0].paragraphs[0].runs[0], size=13)
    row.cells[1].paragraphs[0].text = name
    row.cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
    set_font(row.cells[1].paragraphs[0].runs[0], size=13, bold=True)
    row.cells[2].paragraphs[0].text = desc
    row.cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
    set_font(row.cells[2].paragraphs[0].runs[0], size=13)
    row.cells[3].paragraphs[0].text = sig

# -----------------------------------------------------------------------------
# 4. UPDATE INTRODUCTION (Mở đầu)
# -----------------------------------------------------------------------------
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
                set_font(np.runs[0], size=13)
            elif "…" in np.text:
                np.text = (
                    "Hệ thống quản lý dự án Koshi (輿) được thiết kế theo triết lý 'Local-First' và điều hướng bàn phím "
                    "tối ưu (Vim ergonomics), mang lại phản hồi < 16ms cùng trợ lý AI tự động hóa tóm tắt tiến độ, trích xuất "
                    "biên bản họp và cân bằng tải nhân sự."
                )
                set_font(np.runs[0], size=13)
            elif "Em xin chân thành cảm ơn!" in np.text:
                np.text = "Nhóm 04 chúng em xin chân thành cảm ơn giảng viên ThS. Nguyễn Thị Tuyển đã tận tình hướng dẫn để nhóm hoàn thành tốt Báo cáo Bài kiểm tra 2 (KT2) này!"
                set_font(np.runs[0], size=13)
                break
        break

# -----------------------------------------------------------------------------
# 5. STRICT CUTOFF: DELETE ALL BODY ELEMENTS FROM CHAPTER 3 ONWARD
# -----------------------------------------------------------------------------
table_count = 0
seen_ch2 = False
cutoff = False
to_remove = []

for child in list(body):
    if child.tag.endswith("sectPr"):
        continue
    if isinstance(child, CT_Tbl):
        table_count += 1
    elif isinstance(child, CT_P):
        p = docx.text.paragraph.Paragraph(child, doc)
        txt = p.text.strip().upper()
        if table_count >= 3 and "CHƯƠNG 2" in txt:
            seen_ch2 = True
        if seen_ch2 and ("CHƯƠNG 3" in txt or "CHƯƠNG III" in txt):
            cutoff = True
    if cutoff:
        to_remove.append(child)

for elem in to_remove:
    body.remove(elem)

# -----------------------------------------------------------------------------
# 6. UPDATE TABLE OF CONTENTS (TOC)
# -----------------------------------------------------------------------------
toc_to_remove = []
for p in doc.paragraphs[:20]:
    txt = p.text.strip().upper()
    if any(k in txt for k in ["CHƯƠNG 3", "CHƯƠNG III", "3.1.", "KẾT LUẬN", "TÀI LIỆU THAM KHẢO"]):
        toc_to_remove.append(p)
    elif "CHƯƠNG 2. MẠNG NƠ-RON VGGNET" in txt:
        p.text = "CHƯƠNG 2. THIẾT KẾ HỆ THỐNG VÀ CƠ SỞ DỮ LIỆU\t4"
    elif "2.1. NỘI DUNG" in txt:
        p.text = "  2.1. Kiến trúc tổng thể hệ thống\t4"

for p in toc_to_remove:
    delete_paragraph(p)

# -----------------------------------------------------------------------------
# 7. CHAPTER 1: INSERT COMPREHENSIVE REQUIREMENTS ANALYSIS
# -----------------------------------------------------------------------------
ch1_p = None
ch2_p = None
for idx, p in enumerate(doc.paragraphs):
    txt = p.text.strip().upper()
    if idx > 20 and "CHƯƠNG 1" in txt and ch1_p is None:
        ch1_p = p
    elif idx > 20 and "CHƯƠNG 2" in txt and ch2_p is None:
        ch2_p = p

# Remove placeholder paragraphs between Chapter 1 and Chapter 2
to_delete_ch1 = []
collecting = False
for p in doc.paragraphs:
    if p == ch1_p:
        collecting = True
        continue
    if p == ch2_p:
        break
    if collecting:
        to_delete_ch1.append(p)

for p in to_delete_ch1:
    delete_paragraph(p)

# Remove placeholder paragraphs after Chapter 2 heading
to_delete_ch2 = []
collecting = False
for p in doc.paragraphs:
    if p == ch2_p:
        collecting = True
        continue
    if collecting:
        to_delete_ch2.append(p)

for p in to_delete_ch2:
    delete_paragraph(p)

# Chapter 1 Heading
ch1_p.text = "CHƯƠNG 1. PHÂN TÍCH YÊU CẦU HỆ THỐNG"
set_font(ch1_p.runs[0], size=14, bold=True, color=(0x0F, 0x17, 0x2A))

# Chapter 1 Sections
add_heading2(ch2_p, "1.1. Bối cảnh bài toán và lý do phát triển")
add_clean_p(ch2_p, "Koshi được định vị là hệ thống quản lý công việc và tiến độ sprint nội bộ dành cho các đội ngũ kỹ sư phần mềm chuyên sâu. Bối cảnh nghiệp vụ tập trung giải quyết nhu cầu của 3 nhóm đối tượng chính (User Personas):")
add_clean_p(ch2_p, "Đòi hỏi thao tác 100% bằng bàn phím không dùng chuột (h/j/k/l, Space, i, n, Esc), chuyển đổi tức thì giữa dạng Bảng (Table) và Kanban 2D, phát hiện sớm các điểm nghẽn tiến độ (Critical Path) trên đồ thị phụ thuộc.", bold_prefix="• Lead Architect / Senior Engineer: ", bullet=True)
add_clean_p(ch2_p, "Cần tự động hóa khâu lập báo cáo tiến độ tuần, tự động trích xuất đầu việc từ biên bản họp văn bản thô và nhận gợi ý phân công công việc dựa trên số điểm độ phức tạp (WIP story points) của từng kỹ sư.", bold_prefix="• Project Manager (PM) / Tech Lead: ", bullet=True)
add_clean_p(ch2_p, "Cần khả năng làm việc ngoại tuyến (Offline-first) khi mất kết nối mạng và đồng bộ tự động dữ liệu vào IndexedDB cục bộ với độ trễ phản hồi giao diện dưới 16ms.", bold_prefix="• Field / Mobile Developer: ", bullet=True)

add_heading2(ch2_p, "1.2. Khảo sát hiện trạng và các giải pháp tương tự")
add_clean_p(ch2_p, "Khảo sát đối chuẩn giữa Koshi và các hệ thống quản lý dự án hàng đầu hiện nay:")
add_clean_p(ch2_p, "Hệ thống hoàn chỉnh nhưng cồng kềnh, thời gian phản hồi giao diện chậm, phụ thuộc 100% vào kết nối mạng, thao tác bàn phím hạn chế.", bold_prefix="• Jira Software: ", bullet=True)
add_clean_p(ch2_p, "Trực quan, đơn giản nhưng thiếu khả năng phân tích đồ thị phụ thuộc DAG, không tối ưu cho luồng làm việc kỹ thuật cao.", bold_prefix="• Trello: ", bullet=True)
add_clean_p(ch2_p, "Giao diện hiện đại, hỗ trợ phím tắt tốt nhưng chưa hỗ trợ phân rã mục tiêu chuyên sâu bằng AI và không có cơ chế phân tích đường găng CPM tự động.", bold_prefix="• Linear: ", bullet=True)
add_clean_p(ch2_p, "Kết hợp triết lý Local-First, điều hướng bàn phím 2D (Vim ergonomics), phân tích chuỗi phụ thuộc bằng giải thuật Kahn kết hợp 3 luồng trợ lý AI quản trị dự án có cơ chế dự phòng 3 tầng.", bold_prefix="• Koshi (Hệ thống đề xuất): ", bullet=True)

add_heading2(ch2_p, "1.3. Mô hình Actor và Phân hệ Use Case tổng quát")
add_clean_p(ch2_p, "Hệ thống phân cấp 3 nhóm tác nhân (Actors) với các phân hệ Use Case chính:")
add_clean_p(ch2_p, "Đăng ký tài khoản mới, Đăng nhập hệ thống qua Email/Mật khẩu hoặc Google OAuth2, Xem dữ liệu mẫu thử nghiệm.", bold_prefix="1. Guest (Khách vãng lai): ", bullet=True)
add_clean_p(ch2_p, "Duyệt bảng công việc (Table/Kanban), Chuyển trạng thái vòng tròn (Space), Chỉnh sửa chi tiết công việc (i/Esc), Tạo công việc mới (n), Phân rã mục tiêu bằng AI, Bóc tách Git Diff để tự động đóng ticket.", bold_prefix="2. Team Member (Lập trình viên): ", bullet=True)
add_clean_p(ch2_p, "Quản trị thành viên dự án qua project_members, Sinh Báo cáo tổng kết tuần (AI Weekly Summary), Bóc tách biên bản họp (AI Meeting Minutes), Cân bằng tải nhân sự (AI Smart Assignment) và trực quan hóa chuỗi phụ thuộc đồ thị (DAG Visualizer).", bold_prefix="3. Project Manager (Quản lý dự án): ", bullet=True)

add_heading2(ch2_p, "1.4. Đặc tả yêu cầu chức năng cốt lõi (Functional Requirements)")
add_clean_p(ch2_p, "Chuyển đổi giao diện tức thì giữa Table View mật độ cao và Kanban Board 2D qua phím tắt 'b' với thời gian < 16ms.", bold_prefix="• FR-01 [Dual-Mode Views]: ", bullet=True)
add_clean_p(ch2_p, "Hỗ trợ điều hướng bàn phím đầy đủ: j/k duyệt dòng trong Table, h/j/k/l duyệt lưới Kanban, Space đổi trạng thái tuần hoàn (TODO -> IN_PROGRESS -> BLOCKED -> DONE -> TODO).", bold_prefix="• FR-02 [Vim Spatial Navigation]: ", bullet=True)
add_clean_p(ch2_p, "Phím Enter mở modal chi tiết, phím 'i' chuyển sang Edit Mode cho phép chỉnh sửa toàn bộ thuộc tính, phím Escape lưu thay đổi và thoát Edit Mode.", bold_prefix="• FR-03 [Task Detail Inspector]: ", bullet=True)
add_clean_p(ch2_p, "Bắt sự kiện Escape ở mức window capture phase để đảm bảo đóng modal hoặc hủy chế độ sửa ngay lập tức mà không bị nuốt bởi ô nhập văn bản.", bold_prefix="• FR-04 [Capture-Phase Escape Trap]: ", bullet=True)
add_clean_p(ch2_p, "Tách biệt quyền hạn theo từng dự án cụ thể thông qua bảng project_members. Cho phép tìm kiếm người dùng trong hệ thống để thêm vào dự án với vai trò OWNER, PM hoặc MEMBER.", bold_prefix="• FR-05 [Project-Scoped RBAC]: ", bullet=True)
add_clean_p(ch2_p, "Sử dụng giải thuật Kahn để phân tích chuỗi phụ thuộc, phát hiện vòng lặp chu trình (Cycle Detection) và tính toán đường găng (Critical Path) cảnh báo điểm nghẽn.", bold_prefix="• FR-06 [Topological DAG & CPM]: ", bullet=True)
add_clean_p(ch2_p, "Tích hợp 3 chức năng AI chuyên sâu: Tóm tắt tiến độ tuần (3 phần Overview, Blockers, Priorities), Bóc tách biên bản họp ra Action Items, và Gợi ý phân bổ công việc theo kỹ năng và tải trọng WIP.", bold_prefix="• FR-07 [Autonomous AI PM Workflows]: ", bullet=True)
add_clean_p(ch2_p, "Cho phép tạo công việc mới trực tiếp ở trạng thái DONE để hỗ trợ ghi nhận các tác vụ đột xuất hoặc hotfix mà không cần qua trạng thái trung gian.", bold_prefix="• FR-08 [Retrospective Work Logging]: ", bullet=True)

add_heading2(ch2_p, "1.5. Đặc tả yêu cầu phi chức năng (Non-Functional Requirements)")
add_clean_p(ch2_p, "Mọi thao tác điều hướng bàn phím và render giao diện cục bộ phải phản hồi trong thời gian < 16ms (tương đương 60fps).", bold_prefix="• NFR-01 [Hiệu năng & Độ trễ]: ", bullet=True)
add_clean_p(ch2_p, "Hệ thống CSDL SQLite phải được cấu hình PRAGMA journal_mode = WAL và busy_timeout = 30000ms nhằm đảm bảo không bị lỗi khóa ghi khi nhiều người dùng thao tác đồng thời.", bold_prefix="• NFR-02 [Độ tin cậy & Concurrency]: ", bullet=True)
add_clean_p(ch2_p, "Mật khẩu người dùng được băm an toàn bằng Bcrypt. Xác thực API sử dụng JWT HS256. Xác thực Google OAuth2 kiểm tra chữ ký mật mã nghiêm ngặt.", bold_prefix="• NFR-03 [Bảo mật & Xác thực]: ", bullet=True)
add_clean_p(ch2_p, "Luồng gọi AI áp dụng cơ chế Cascade 3 tầng (Cloud LLM -> Local Ollama -> Heuristic Rule Engine), đảm bảo hệ thống luôn trả về dữ liệu JSON hợp lệ ngay cả khi mất kết nối Internet.", bold_prefix="• NFR-04 [Khả năng phục hồi AI]: ", bullet=True)
add_clean_p(ch2_p, "Giao diện tuân thủ bảng màu Slate đơn sắc có độ tương phản cao, chuyển đổi Light/Dark mode với độ trễ 0ms.", bold_prefix="• NFR-05 [Độ tương phản & Công thái học]: ", bullet=True)
add_clean_p(ch2_p, "Bật cơ chế PRAGMA foreign_keys = ON trên toàn bộ kết nối cơ sở dữ liệu để đảm bảo các ràng buộc khóa ngoại và xóa xếp tầng (CASCADE) hoạt động chính xác.", bold_prefix="• NFR-06 [Tính toàn vẹn dữ liệu]: ", bullet=True)

add_heading2(ch2_p, "1.6. Xác định bài toán ứng dụng AI và phạm vi tích hợp")
add_clean_p(ch2_p, "Trong khuôn khổ đề tài, Koshi tập trung ứng dụng các mô hình ngôn ngữ lớn (LLMs) vào 3 bài toán xử lý ngôn ngữ tự nhiên then chốt:")
add_clean_p(ch2_p, "Tổng hợp dữ liệu trạng thái công việc trong sprint thành báo cáo súc tích 3 phần (Tổng quan, Điểm nghẽn tiến độ, Ưu tiên tiếp theo).", bold_prefix="1. Bài toán Tóm tắt văn bản có cấu trúc (Structured Summarization): ", bullet=True)
add_clean_p(ch2_p, "Phân tích văn bản thô từ biên bản cuộc họp để trích xuất danh sách công việc, người chịu trách nhiệm, độ ưu tiên và thời hạn bàn giao.", bold_prefix="2. Bài toán Trích xuất thông tin thực thể (Information Extraction): ", bullet=True)
add_clean_p(ch2_p, "Đánh giá ma trận kỹ năng và số điểm độ phức tạp công việc đang thực hiện (WIP points) để đề xuất lập trình viên phù hợp nhất.", bold_prefix="3. Bài toán Tối ưu hóa phân bổ nguồn lực (Capacity Optimization): ", bullet=True)

# -----------------------------------------------------------------------------
# 8. CHAPTER 2: INSERT ARCHITECTURE & DATABASE DESIGN (Bounded Cutoff)
# -----------------------------------------------------------------------------
# Format Chapter 2 Heading
ch2_p.text = "CHƯƠNG 2. THIẾT KẾ HỆ THỐNG VÀ CƠ SỞ DỮ LIỆU"
set_font(ch2_p.runs[0], size=14, bold=True, color=(0x0F, 0x17, 0x2A))

# Chapter 2 Sections
add_body_h2("2.1. Kiến trúc tổng thể hệ thống")
add_body_p("Koshi được thiết kế theo mô hình kiến trúc phân lớp hiện đại (3-Tier Decoupled Architecture), tối ưu cho tính sẵn sàng cao, hiệu năng phản hồi < 16ms và bảo mật nghiêm ngặt:")
add_body_p("Xây dựng trên nền tảng Vue 3.5 (Composition API, `<script setup lang='ts'>`), quản lý trạng thái tập trung với Pinia 2.3, Vite 6 và hệ thống thiết kế giao diện tối giản Slate bằng Tailwind CSS v4.", bold_prefix="• Frontend Client (SPA): ", bullet=True)
add_body_p("Caddy Reverse Proxy tự động cấp phát chứng chỉ SSL/TLS, định tuyến lưu lượng vào Nginx Alpine đóng gói ứng dụng Single Page Application.", bold_prefix="• Edge Proxy & Web Server: ", bullet=True)
add_body_p("Sử dụng FastAPI (Python 3.11), SQLAlchemy 2.0 ORM, xác thực phân quyền qua OAuth2 Password Bearer & JSON Web Token (JWT HS256) và Google OAuth2 mật mã học.", bold_prefix="• Backend API Core: ", bullet=True)
add_body_p("Cơ sở dữ liệu quan hệ SQLite với chế độ PRAGMA journal_mode = WAL và busy_timeout = 30000ms, đảm bảo tính gọn nhẹ, di động và hiệu năng truy vấn tức thì.", bold_prefix="• Database Engine: ", bullet=True)

add_body_h2("2.2. Thiết kế Cơ sở dữ liệu quan hệ (ERD & Data Dictionary)")
add_body_p("Hệ thống CSDL bao gồm 7 bảng thực thể có quan hệ ràng buộc khóa ngoại chặt chẽ (bật PRAGMA foreign_keys = ON trên mọi kết nối):")

# Table 3: Data Dictionary
tbl3 = doc.add_table(rows=8, cols=4)
tbl3.style = 'Table Grid'
headers3 = ['Tên bảng', 'Khóa chính (PK)', 'Khóa ngoại (FK)', 'Mô tả nghiệp vụ']
for idx, h in enumerate(headers3):
    cell = tbl3.rows[0].cells[idx]
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(h)
    set_font(r, size=12, bold=True)
    shd = parse_xml(r'<w:shd {} w:fill="F1F5F9"/>'.format(nsdecls('w')))
    cell._tc.get_or_add_tcPr().append(shd)

data_dict = [
    ("users", "id (INTEGER)", "Không", "Lưu thông tin tài khoản, mật khẩu băm Bcrypt, vai trò hệ thống, kỹ năng (skills) và avatar."),
    ("projects", "id (INTEGER)", "owner_id -> users(id)", "Lưu thông tin dự án phần mềm và chủ sở hữu dự án."),
    ("project_members", "id (INTEGER)", "project_id, user_id", "Phân quyền theo phạm vi từng dự án cụ thể với vai trò OWNER, PM, hoặc MEMBER."),
    ("sprints", "id (INTEGER)", "project_id -> projects(id)", "Quản lý chu kỳ sprint phát triển, mục tiêu sprint và trạng thái kích hoạt."),
    ("tasks", "id (VARCHAR)", "project_id, sprint_id, assignee_id", "Lưu chi tiết công việc, trạng thái (TODO/IN_PROGRESS/BLOCKED/DONE), độ ưu tiên, điểm Story Points."),
    ("task_dependencies", "id (INTEGER)", "task_id, depends_on_task_id", "Lưu đồ thị quan hệ phụ thuộc giữa các công việc phục vụ thuật toán Topological DAG."),
    ("comments", "id (INTEGER)", "task_id, author_id", "Lưu lịch sử trao đổi, bình luận kỹ thuật và ghi chú tiến độ giữa các thành viên.")
]

for r_idx, (tbl_name, pk, fk, desc) in enumerate(data_dict, start=1):
    row = tbl3.rows[r_idx]
    row.cells[0].paragraphs[0].text = tbl_name
    row.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(row.cells[0].paragraphs[0].runs[0], size=11, bold=True)
    row.cells[1].paragraphs[0].text = pk
    row.cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(row.cells[1].paragraphs[0].runs[0], size=11)
    row.cells[2].paragraphs[0].text = fk
    row.cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
    set_font(row.cells[2].paragraphs[0].runs[0], size=11)
    row.cells[3].paragraphs[0].text = desc
    row.cells[3].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
    set_font(row.cells[3].paragraphs[0].runs[0], size=11)

add_body_h2("2.3. Thiết kế giải thuật đồ thị phụ thuộc DAG và đường găng CPM")
add_body_p("Hệ thống xây dựng mô hình đồ thị có hướng không chu trình (Directed Acyclic Graph - DAG) để quản trị phụ thuộc giữa các tác vụ:")
add_body_p("Áp dụng giải thuật Kahn với độ phức tạp O(V + E) để tính toán thứ tự thực thi hợp lệ. Trong quá trình duyệt bậc vào in-degree, nếu đồ thị còn đỉnh chưa được duyệt khi hàng đợi rỗng, hệ thống lập tức phát hiện chu trình (Cycle Detection) và từ chối thiết lập liên kết.", bold_prefix="• Giải thuật sắp xếp tô-pô (Topological Sort): ", bullet=True)
add_body_p("Tính toán thời điểm bắt đầu sớm nhất (Early Start - ES) và muộn nhất (Late Finish - LF) của từng tác vụ. Những tác vụ có độ trượt (Float/Slack) bằng 0 được định danh vào Đường găng (Critical Path) và hiển thị nổi bật trên giao diện DAG Visualizer.", bold_prefix="• Phương pháp đường găng (Critical Path Method - CPM): ", bullet=True)
add_body_p("Hệ thống tự động đánh giá chỉ số trễ hạn SLA động. Một công việc bị coi là trễ hạn nếu vượt quá deadline hoặc phụ thuộc vào một tác vụ tiên quyết (predecessor) đang bị trễ hạn.", bold_prefix="• Động cơ tính trễ hạn SLA động: ", bullet=True)

add_body_h2("2.4. Thiết kế công thái học giao diện và điều hướng bàn phím Vim")
add_body_p("Giao diện Koshi loại bỏ hoàn toàn sự phụ thuộc vào chuột máy tính, áp dụng hệ thống phím tắt không gian 2D theo chuẩn Vim ergonomics:")
add_body_p("Phím 'j' và 'k' duyệt danh sách dòng trong Table View; các phím 'h', 'j', 'k', 'l' duyệt lưới 2 chiều trên Kanban Board.", bold_prefix="• Điều hướng không gian 2D: ", bullet=True)
add_body_p("Phím Space chuyển đổi trạng thái công việc theo vòng tuần hoàn (TODO -> IN_PROGRESS -> BLOCKED -> DONE -> TODO). Phím 'b' chuyển đổi tức thì giữa Table View và Kanban Board.", bold_prefix="• Thao tác trạng thái nhanh: ", bullet=True)
add_body_p("Phím Escape được bắt ở window capture phase (`window.addEventListener('keydown', handler, true)`), đảm bảo đóng các modal và hủy chế độ chỉnh sửa với độ trễ 0ms mà không bị các phần tử input chặn lại.", bold_prefix="• Bẫy phím Escape Capture-Phase: ", bullet=True)

add_body_h2("2.5. Thiết kế kiến trúc AI Cascade 3 tầng và ma trận Prompt")
add_body_p("Để đảm bảo tính liên tục trong vận hành ngay cả khi môi trường mạng bị gián đoạn, Koshi áp dụng kiến trúc Cascade 3 tầng:")
add_body_p("Sử dụng Gemini 2.5 Flash / OpenAI qua giao thức HTTPS API RESTful, mang lại chất lượng xử lý ngôn ngữ tự nhiên tối ưu nhất.", bold_prefix="• Tầng 1 (Cloud LLM): ", bullet=True)
add_body_p("Tự động chuyển tiếp yêu cầu sang mô hình ngôn ngữ chạy cục bộ qua Ollama (Qwen 2.5 7B) khi phát hiện lỗi kết nối mạng hoặc timeout 10 giây.", bold_prefix="• Tầng 2 (Local LLM): ", bullet=True)
add_body_p("Nếu cả 2 tầng LLM đều không phản hồi, hệ thống kích hoạt bộ quy tắc Heuristic thuần túy (Rule Engine), đảm bảo trả về định dạng JSON hợp lệ đạt tỷ lệ sẵn sàng 100%.", bold_prefix="• Tầng 3 (Heuristic Engine): ", bullet=True)
add_body_p("Hệ thống cung cấp 4 năng lực AI chủ chốt: AI Task Decomposer (phân rã mục tiêu), AI Weekly Sprint Summary (tổng kết tuần 3 phần), AI Meeting Minutes (trích xuất biên bản họp ra Action Items) và AI Smart Assignment (hàm mục tiêu cân bằng tải nhân sự theo ma trận kỹ năng và WIP points).", bold_prefix="• Bốn năng lực AI tích hợp: ", bullet=True)

# -----------------------------------------------------------------------------
# 9. SAVE FINAL nhom4.docx
# -----------------------------------------------------------------------------
doc.save(DST)
print(f"[✓] Successfully compiled nhom4.docx strictly bounded to Chapter 2: {DST}")

if __name__ == "__main__":
    pass
