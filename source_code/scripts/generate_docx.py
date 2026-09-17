#!/usr/bin/env python3
import os
import sys
import shutil
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

REPO_ROOT = os.path.expanduser("~/koshi")
DOCX_PATH = os.path.join(REPO_ROOT, "nhom4.docx")
TEMPLATE_PATH = os.path.expanduser("~/Documents/BAI DU AN_UNG DUNG AI.docx")

if not os.path.exists(DOCX_PATH):
    if os.path.exists(TEMPLATE_PATH):
        print(f"[*] Cloning template: {TEMPLATE_PATH} -> {DOCX_PATH}")
        shutil.copyfile(TEMPLATE_PATH, DOCX_PATH)
    else:
        print(f"[!] Error: Neither {DOCX_PATH} nor {TEMPLATE_PATH} exists.", file=sys.stderr)
        sys.exit(1)

doc = Document(DOCX_PATH)

# 1. Update text mentions of KT1 -> KT2 across paragraphs
replacements = [
    ("Bảng 1: Phân công nhiệm vụ theo tiến độ thực hiện (KT1)", "Bảng 1: Phân công nhiệm vụ theo tiến độ thực hiện (KT2)"),
    ("Báo cáo Bài kiểm tra 1 (KT1) trình bày toàn bộ kết quả phân tích yêu cầu, thiết kế kiến trúc hệ thống, mô hình hóa cơ sở dữ liệu và kế hoạch tích hợp AI của Nhóm 04.",
     "Báo cáo Bài kiểm tra 2 (KT2) trình bày toàn bộ kết quả hiện thực hóa mã nguồn hệ thống, tích hợp cơ sở dữ liệu SQLite WAL, phân quyền RBAC đa cấp độ, xác thực bảo mật JWT / Google OAuth2 mật mã học, hiện thực hóa các chức năng AI PM đa tầng và bộ kiểm thử tự động toàn diện của Nhóm 04."),
    ("Giai đoạn Bài kiểm tra 1 (KT1) đã hoàn thành xuất sắc toàn bộ các mục tiêu đặt ra: phân tích thấu đáo bài toán quản lý dự án, thiết kế kiến trúc 3 lớp vững chắc, hoàn thiện mô hình cơ sở dữ liệu quan hệ với các ràng buộc toàn vẹn dữ liệu, và xây dựng thành công cơ chế tích hợp AI đa tầng linh hoạt.",
     "Giai đoạn Bài kiểm tra 2 (KT2) đã hoàn thành xuất sắc toàn bộ các mục tiêu đặt ra: hiện thực hóa 100% các API CRUD cho Projects, Sprints, Tasks, Dependencies, Comments; tích hợp xác thực JWT an toàn và Google OAuth2; xây dựng giao diện Vue 3 Single Page Application với điều hướng bàn phím Vim ergonomics; hoàn thiện bộ 4 chức năng AI đa tầng với cơ chế Fallback không lỗi; và vượt qua 84 bài kiểm thử tự động (68 pytest backend và 16 vitest frontend)."),
    ("• Bài kiểm tra 2 (KT2): Hoàn thiện toàn bộ các API CRUD nghiệp vụ, phân quyền JWT/OAuth2, kết nối giao diện Vue 3 SPA.",
     "• Bài kiểm tra 2 (KT2): Đã hoàn thành toàn bộ API CRUD, phân quyền JWT/OAuth2, giao diện Vue 3 SPA, bộ 4 chức năng AI và kiểm thử tự động."),
    ("3.4. Minh chứng ứng dụng AI trong quy trình SDLC (KT1)",
     "3.4. Minh chứng ứng dụng AI trong quy trình SDLC (KT2)")
]

for p in doc.paragraphs:
    for old_text, new_text in replacements:
        if old_text in p.text:
            p.text = p.text.replace(old_text, new_text)

# 2. Update Table 1: Phase 2 Task Allocation (KT2)
tasks_kt2 = [
    ("1", "Hiện thực hóa kiến trúc API Core FastAPI, kết nối CSDL SQLite WAL, tích hợp xác thực JWT & Google OAuth2 mật mã học", "Phạm Minh Tú", "100%"),
    ("2", "Hiện thực hóa thuật toán đồ thị phụ thuộc Kahn DAG, tính toán đường găng Critical Path (CPM) và động cơ tính trễ hạn SLA động", "Phạm Minh Tú", "100%"),
    ("3", "Hiện thực hóa toàn bộ các API CRUD (Projects, Sprints, Tasks, Dependencies, Comments) và phân quyền RBAC đa cấp độ", "Phạm Văn Huynh", "100%"),
    ("4", "Xây dựng luồng tải lên/tải xuống ảnh đại diện (avatar streaming, MIME allowlist, hex filenames chống path traversal)", "Phạm Văn Huynh", "100%"),
    ("5", "Viết bộ kiểm thử tự động toàn diện pytest (68 tests) và vitest (16 tests), kiểm thử ràng buộc toàn vẹn CSDL SQL", "Phạm Văn Huynh", "100%"),
    ("6", "Phát triển giao diện Vue 3 Single Page Application (Kanban Board 2D, Task Table, Profile Management View, AuthModal)", "Đàm Đức Đôn", "100%"),
    ("7", "Tích hợp hệ thống điều hướng bàn phím Vim ergonomics (h/j/k/l, Space, b, 1-4), bẫy phím Escape capture-phase và đa ngôn ngữ i18n", "Đàm Đức Đôn", "100%"),
    ("8", "Thiết kế, thử nghiệm và tối ưu hóa ma trận Prompt AI 3 tầng (Decomposer, Weekly Summary, Meeting Minutes, Smart Assignment)", "Đàm Đức Đôn", "100%"),
    ("9", "Tích hợp toàn diện frontend - backend, E2E validation, biên soạn tài liệu kỹ thuật KT2 (prompts.md, nhom4.docx) và đóng gói mã nguồn", "Cả nhóm", "100%")
]

table1 = doc.tables[1]
while len(table1.rows) - 1 < len(tasks_kt2):
    table1.add_row()
while len(table1.rows) - 1 > len(tasks_kt2):
    tr = table1.rows[-1]._tr
    tr.getparent().remove(tr)

for idx, (stt, content, assignee, result) in enumerate(tasks_kt2, start=1):
    row = table1.rows[idx]
    row.cells[0].paragraphs[0].text = stt
    row.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    row.cells[1].paragraphs[0].text = content
    row.cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
    row.cells[2].paragraphs[0].text = assignee
    row.cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
    row.cells[3].paragraphs[0].text = result
    row.cells[3].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

# 3. Update Table 2: Member allocation
members_kt2 = [
    ("1", "Phạm Minh Tú (Trưởng nhóm)", "Chịu trách nhiệm kiến trúc tổng thể, mô hình toán học DAG/CPM, FastAPI Core, xác thực JWT/OAuth2, điều phối kỹ thuật.", ""),
    ("2", "Phạm Văn Huynh", "Phụ trách phát triển API CRUD, module quản lý avatar/profile, kiểm thử tự động backend pytest và toàn vẹn CSDL SQL.", ""),
    ("3", "Đàm Đức Đôn", "Phụ trách giao diện Vue 3 SPA, điều hướng bàn phím Vim, đa ngôn ngữ i18n, xây dựng ma trận Prompt AI 3 tầng và tài liệu KT2.", "")
]

table2 = doc.tables[2]
for idx, (stt, name, desc, sig) in enumerate(members_kt2, start=1):
    if idx < len(table2.rows):
        row = table2.rows[idx]
        row.cells[0].paragraphs[0].text = stt
        row.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        row.cells[1].paragraphs[0].text = name
        row.cells[2].paragraphs[0].text = desc
        row.cells[3].paragraphs[0].text = sig

doc.save(DOCX_PATH)
print(f"[✓] Successfully updated Phase 2 Task Allocation in {DOCX_PATH}")
