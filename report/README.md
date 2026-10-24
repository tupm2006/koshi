# Koshi — project report

| File | Language | Source |
|:--|:--|:--|
| `Koshi-Report-EN.pdf` | English (the one to submit) | `en/` |
| `Koshi-BaoCao-VI.pdf` | Tiếng Việt (reading copy) | `vi/` |

Built from the ICTU LaTeX template (`documentation/template_khoa_luan_ictu.zip`), with the
statement of originality removed (group project) and a task-allocation table added.

**Before submitting, fill in:** the supervisor's name on both covers (`*/bia/bia_*.tex`), and check
the task-allocation table (`*/chuong/mo_dau.tex`) and the faculty name match your class.

## Build

```bash
cd report/en   # or report/vi
latexmk -pdf main.tex          # pdflatex + biber, as the template expects
```

No local TeX? Use the official image:

```bash
docker run --rm --user $(id -u):$(id -g) -v "$PWD/..":/w -w /w/en texlive/texlive:latest latexmk -pdf main.tex
```

The template as shipped does not compile on current LaTeX kernels (`\MakeUppercase` inside
`\cfttoctitlefont` → "Missing \endcsname" at `\tableofcontents`); both `main.tex` files work around it.

## Figures

`figures/` (English UI, English data) and `figures-vi/` (Vietnamese UI, Vietnamese data) are
captured from the running app by `scripts/report-screenshots.py`, which also fails loudly if any
screen shows text in the other language. Re-run it after a UI change.
