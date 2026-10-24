# ALP Psycho Test study guide

This repository contains a plain-English study guide for the **Watch Table Test (Clock Test)**,
part of Section 2 (Following Direction Test) of the ALP psycho test. It is based on the lecture at
https://youtu.be/lN-N6OE-tRA and on the transcript supplied with it.

## Files

| File | What it is |
| --- | --- |
| `ALP-Watch-Table-Clock-Test-Guide.pdf` | The main deliverable. A 25-page, English-only PDF that explains every concept from the lecture in detail. |
| `assets/alp-watch-table-reference.png` | The reference clock image used throughout the PDF (also available as `.svg`). |
| `alp-watch-table-guide.html` | A short web version of the guide, with a link to download the PDF. |
| `tools/build_watch_table_pdf.py` | The script that generates the PDF. |

## Rebuilding the PDF

The generator needs `reportlab` and `pillow`:

```bash
python3 -m venv .venv
.venv/bin/pip install reportlab pillow
.venv/bin/python tools/build_watch_table_pdf.py
```

## Note

The guide is a study summary, not an official document. Exam rules can change; always follow the
latest official RRB and RDSO instructions on exam day. Statements about any commercial test
platform are reported as the lecturer's own claims.
