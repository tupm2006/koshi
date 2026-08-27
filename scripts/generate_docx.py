#!/usr/bin/env python3
import os
import subprocess
import html

def markdown_to_html(md_text: str) -> str:
    html_lines = []
    html_lines.append("""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Báo cáo Bài kiểm tra 1 (KT1) - Nhóm 1</title>
<style>
    body { font-family: 'Times New Roman', serif; font-size: 13pt; line-height: 1.5; margin: 30px; color: #111; }
    h1 { font-size: 20pt; text-align: center; color: #0f172a; margin-bottom: 20px; font-weight: bold; }
    h2 { font-size: 16pt; color: #1e293b; border-bottom: 1.5px solid #64748b; padding-bottom: 4px; margin-top: 24px; font-weight: bold; }
    h3 { font-size: 14pt; color: #334155; margin-top: 18px; font-weight: bold; }
    h4 { font-size: 13pt; color: #475569; margin-top: 14px; font-weight: bold; }
    table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 11pt; }
    th, td { border: 1px solid #94a3b8; padding: 6px 10px; text-align: left; }
    th { background-color: #f1f5f9; font-weight: bold; }
    pre { background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 10px; font-family: 'Courier New', monospace; font-size: 10pt; overflow-x: auto; }
    code { font-family: 'Courier New', monospace; background-color: #f1f5f9; padding: 2px 4px; border-radius: 3px; font-size: 11pt; }
    blockquote { border-left: 3px solid #6366f1; padding-left: 12px; margin: 10px 0; color: #475569; font-style: italic; }
    ul, ol { margin-left: 20px; }
    li { margin-bottom: 4px; }
</style>
</head>
<body>
""")
    
    in_table = False
    in_code = False
    code_block = []
    
    lines = md_text.split('\n')
    for line in lines:
        if line.startswith('```'):
            if in_code:
                in_code = False
                html_lines.append(f"<pre><code>{html.escape(chr(10).join(code_block))}</code></pre>")
                code_block = []
            else:
                in_code = True
                code_block = []
            continue
            
        if in_code:
            code_block.append(line)
            continue
            
        # Table handling
        if '|' in line and not line.strip().startswith('#'):
            parts = [p.strip() for p in line.split('|')[1:-1]]
            if all(set(p) <= {'-', ':', ' '} for p in parts if p):
                continue # Skip divider row
            
            if not in_table:
                in_table = True
                html_lines.append("<table>")
                html_lines.append("<thead><tr>" + "".join(f"<th>{html.escape(p)}</th>" for p in parts) + "</tr></thead><tbody>")
            else:
                html_lines.append("<tr>" + "".join(f"<td>{html.escape(p)}</td>" for p in parts) + "</tr>")
            continue
        elif in_table:
            in_table = False
            html_lines.append("</tbody></table>")
            
        stripped = line.strip()
        if not stripped:
            continue
            
        if line.startswith('# '):
            html_lines.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith('## '):
            html_lines.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith('### '):
            html_lines.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
        elif line.startswith('#### '):
            html_lines.append(f"<h4>{html.escape(line[5:].strip())}</h4>")
        elif stripped.startswith('- '):
            html_lines.append(f"<ul><li>{html.escape(stripped[2:])}</li></ul>")
        elif stripped.startswith('1. ') or stripped.startswith('2. ') or stripped.startswith('3. '):
            html_lines.append(f"<ol><li>{html.escape(stripped[3:])}</li></ol>")
        elif stripped.startswith('---'):
            html_lines.append("<hr style='border: 0.5px solid #cbd5e1; margin: 15px 0;'/>")
        else:
            html_lines.append(f"<p>{html.escape(stripped)}</p>")
            
    if in_table:
        html_lines.append("</tbody></table>")
    html_lines.append("</body></html>")
    return "\n".join(html_lines)

def build_docx():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md_path = os.path.join(base_dir, "docs", "BAO_CAO_KT1.md")
    html_temp = os.path.join(base_dir, "docs", "temp_report.html")
    docx_output = os.path.join(base_dir, "nhom1.docx")
    
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
        
    html_content = markdown_to_html(md_content)
    with open(html_temp, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    cmd = ["libreoffice", "--headless", "--convert-to", "docx:Office Open XML Text", html_temp, "--outdir", base_dir]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    generated_docx = os.path.join(base_dir, "temp_report.docx")
    if os.path.exists(generated_docx):
        if os.path.exists(docx_output):
            os.remove(docx_output)
        os.rename(generated_docx, docx_output)
        if os.path.exists(html_temp):
            os.remove(html_temp)
        print(f"Successfully compiled report to: {docx_output}")
    else:
        print(f"LibreOffice conversion output: {res.stdout.decode()} {res.stderr.decode()}")

if __name__ == "__main__":
    build_docx()
