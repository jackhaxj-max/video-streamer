#!/usr/bin/env python3
"""
Build a detailed, plain-English PDF study guide for the ALP Psycho Test
"Watch Table Test" / "Clock Test", based on the lecture at
https://youtu.be/lN-N6OE-tRA

The guide reuses one reference clock image (assets/alp-watch-table-reference.png)
to explain every concept in the lecture.

Run with a Python that has reportlab + pillow installed, e.g.
    python3 -m venv /tmp/pdfvenv
    /tmp/pdfvenv/bin/pip install reportlab pillow
    /tmp/pdfvenv/bin/python tools/build_watch_table_pdf.py
"""

from __future__ import annotations

import math
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

# ----------------------------------------------------------------------------
# Paths and page geometry
# ----------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_PNG = os.path.join(ROOT, "assets", "alp-watch-table-reference.png")
OUT_PDF = os.path.join(ROOT, "ALP-Watch-Table-Clock-Test-Guide.pdf")
SOURCE_URL = "https://youtu.be/lN-N6OE-tRA"

PAGE_W, PAGE_H = A4
MARGIN_L = 52
MARGIN_R = 52
MARGIN_T = 58
MARGIN_B = 52
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R   # ≈ 491 pt

# ----------------------------------------------------------------------------
# Palette
# ----------------------------------------------------------------------------

NAVY = colors.HexColor("#172033")
BLUE = colors.HexColor("#1B4FA0")
BLUE_SOFT = colors.HexColor("#E8F1FF")
BLUE_LINE = colors.HexColor("#C9D9F5")
AMBER = colors.HexColor("#E0A11B")
AMBER_SOFT = colors.HexColor("#FFF4D6")
GREEN = colors.HexColor("#167A55")
GREEN_SOFT = colors.HexColor("#E6F6EF")
RED = colors.HexColor("#B23B3B")
RED_SOFT = colors.HexColor("#FDECEC")
BORDER = colors.HexColor("#D9E2F2")
MUTED = colors.HexColor("#536079")
PALE = colors.HexColor("#F8FBFF")
WHITE = colors.white

# ----------------------------------------------------------------------------
# Styles
# ----------------------------------------------------------------------------

S = {}

S["cover_kicker"] = ParagraphStyle(
    "cover_kicker", fontName="Helvetica-Bold", fontSize=9.5, leading=13,
    textColor=colors.HexColor("#BBD2FF"), alignment=TA_LEFT, spaceAfter=12,
)
S["cover_title"] = ParagraphStyle(
    "cover_title", fontName="Helvetica-Bold", fontSize=30, leading=34,
    textColor=NAVY, spaceAfter=6,
)
S["cover_sub"] = ParagraphStyle(
    "cover_sub", fontName="Helvetica-Bold", fontSize=13, leading=18,
    textColor=BLUE, spaceAfter=14,
)
S["cover_body"] = ParagraphStyle(
    "cover_body", fontName="Helvetica", fontSize=10, leading=15,
    textColor=MUTED, spaceAfter=10,
)
S["title"] = ParagraphStyle(
    "title", fontName="Helvetica-Bold", fontSize=25, leading=29,
    textColor=NAVY, spaceAfter=8,
)
S["h1"] = ParagraphStyle(
    "h1", fontName="Helvetica-Bold", fontSize=17, leading=21,
    textColor=NAVY, spaceBefore=4, spaceAfter=10,
)
S["h2"] = ParagraphStyle(
    "h2", fontName="Helvetica-Bold", fontSize=12.5, leading=16,
    textColor=BLUE, spaceBefore=13, spaceAfter=6,
)
S["h3"] = ParagraphStyle(
    "h3", fontName="Helvetica-Bold", fontSize=10.5, leading=14,
    textColor=NAVY, spaceBefore=9, spaceAfter=4,
)
S["body"] = ParagraphStyle(
    "body", fontName="Helvetica", fontSize=9.5, leading=14.2,
    textColor=NAVY, spaceAfter=8, alignment=TA_LEFT,
)
S["body_tight"] = ParagraphStyle(
    "body_tight", parent=S["body"], spaceAfter=4,
)
S["bullet"] = ParagraphStyle(
    "bullet", parent=S["body"], leftIndent=15, bulletIndent=3, spaceAfter=4,
)
S["bullet2"] = ParagraphStyle(
    "bullet2", parent=S["body"], leftIndent=30, bulletIndent=18,
    fontSize=9.2, leading=13.5, spaceAfter=3,
)
S["small"] = ParagraphStyle(
    "small", fontName="Helvetica", fontSize=8.4, leading=12,
    textColor=MUTED, spaceAfter=6,
)
S["caption"] = ParagraphStyle(
    "caption", fontName="Helvetica-Oblique", fontSize=8.5, leading=12,
    textColor=MUTED, alignment=TA_CENTER, spaceBefore=5, spaceAfter=10,
)
S["quote"] = ParagraphStyle(
    "quote", fontName="Helvetica-Oblique", fontSize=10, leading=16,
    textColor=NAVY, leftIndent=6, rightIndent=6, spaceAfter=4,
)
S["box_h"] = ParagraphStyle(
    "box_h", fontName="Helvetica-Bold", fontSize=9.3, leading=13,
    textColor=NAVY, spaceAfter=4,
)
S["box_b"] = ParagraphStyle(
    "box_b", fontName="Helvetica", fontSize=9.2, leading=13.5,
    textColor=NAVY, spaceAfter=5,
)
S["box_bullet"] = ParagraphStyle(
    "box_bullet", parent=S["box_b"], leftIndent=14, bulletIndent=3,
    spaceAfter=3,
)
S["th"] = ParagraphStyle(
    "th", fontName="Helvetica-Bold", fontSize=8.3, leading=11,
    textColor=WHITE,
)
S["td"] = ParagraphStyle(
    "td", fontName="Helvetica", fontSize=8.7, leading=12,
    textColor=NAVY,
)
S["td_b"] = ParagraphStyle(
    "td_b", fontName="Helvetica-Bold", fontSize=8.7, leading=12,
    textColor=NAVY,
)
S["td_sm"] = ParagraphStyle(
    "td_sm", fontName="Helvetica", fontSize=8.1, leading=11.5,
    textColor=NAVY,
)
S["toc1"] = ParagraphStyle(
    "toc1", fontName="Helvetica-Bold", fontSize=10, leading=19,
    textColor=NAVY,
)
S["toc2"] = ParagraphStyle(
    "toc2", fontName="Helvetica", fontSize=9.1, leading=16,
    textColor=MUTED, leftIndent=18,
)
S["step"] = ParagraphStyle(
    "step", fontName="Helvetica", fontSize=9.1, leading=13.4,
    textColor=NAVY, leftIndent=17, bulletIndent=2, spaceAfter=3,
)


def P(text, style="body"):
    return Paragraph(text, S[style])


def B(items, style="bullet"):
    return [Paragraph(t, S[style], bulletText="\u2022") for t in items]


# ----------------------------------------------------------------------------
# Custom flowables
# ----------------------------------------------------------------------------

class Callout(Flowable):
    """A rounded, coloured box containing wrapped flowables with a left bar."""

    def __init__(self, parts, width=CONTENT_W, bg=BLUE_SOFT, border=BLUE_LINE,
                 bar=BLUE, padding=11, bar_width=5):
        super().__init__()
        self.parts = parts
        self.width = width
        self.bg = bg
        self.border = border
        self.bar = bar
        self.padding = padding
        self.bar_width = bar_width
        self._h = 0
        self._heights = []

    def wrap(self, availWidth, availHeight):
        self.width = min(self.width, availWidth)
        inner = self.width - 2 * self.padding - self.bar_width
        self._heights = []
        for f in self.parts:
            self._heights.append(f.wrap(inner, availHeight)[1])
        self._h = sum(self._heights) + 2 * self.padding
        return self.width, self._h

    def draw(self):
        c = self.canv
        c.setFillColor(self.bg)
        c.setStrokeColor(self.border)
        c.setLineWidth(0.7)
        c.roundRect(0, 0, self.width, self._h, 8, fill=1, stroke=1)
        c.setFillColor(self.bar)
        c.roundRect(0, 0, self.bar_width, self._h, 2.5, fill=1, stroke=0)
        y = self._h - self.padding
        for f, h in zip(self.parts, self._heights):
            y -= h
            f.drawOn(c, self.padding + self.bar_width, y)


def rule_box(title, text, extra=None):
    parts = [P(title, "box_h"), P(text, "box_b")]
    if extra:
        parts.extend(extra)
    return Callout(parts, bg=GREEN_SOFT, border=colors.HexColor("#BFE4D2"), bar=GREEN)


def note_box(title, text, extra=None):
    parts = [P(title, "box_h"), P(text, "box_b")]
    if extra:
        parts.extend(extra)
    return Callout(parts, bg=AMBER_SOFT, border=colors.HexColor("#F1DCA5"), bar=AMBER)


def warn_box(title, text, extra=None):
    parts = [P(title, "box_h"), P(text, "box_b")]
    if extra:
        parts.extend(extra)
    return Callout(parts, bg=RED_SOFT, border=colors.HexColor("#F3CACA"), bar=RED)


def info_box(title, text, extra=None):
    parts = [P(title, "box_h"), P(text, "box_b")]
    if extra:
        parts.extend(extra)
    return Callout(parts, bg=BLUE_SOFT, border=BLUE_LINE, bar=BLUE)


class HRule(Flowable):
    def __init__(self, width=CONTENT_W, color=BORDER, thickness=0.7, space=9):
        super().__init__()
        self.width, self.color, self.thickness, self.space = width, color, thickness, space

    def wrap(self, av, ah):
        return self.width, self.space

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.space / 2, self.width, self.space / 2)


class PartBanner(Flowable):
    """Navy band that opens a major part of the guide."""

    def __init__(self, number, title, subtitle="", width=CONTENT_W):
        super().__init__()
        self.number, self.title, self.subtitle, self.width = number, title, subtitle, width
        self.height = 54 if subtitle else 43

    def wrap(self, av, ah):
        self.width = min(self.width, av)
        return self.width, self.height + 10

    def draw(self):
        c = self.canv
        h = self.height
        c.setFillColor(NAVY)
        c.roundRect(0, 10, self.width, h, 9, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#4B7AD1"))
        c.roundRect(14, 10 + h / 2 - 13, 26, 26, 13, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(27, 10 + h / 2 - 4, str(self.number))
        c.setFont("Helvetica-Bold", 15)
        c.drawString(50, 10 + h - 22 if self.subtitle else 10 + h / 2 - 5, self.title)
        if self.subtitle:
            c.setFillColor(colors.HexColor("#BBD2FF"))
            c.setFont("Helvetica", 8.6)
            c.drawString(50, 10 + h - 36, self.subtitle)


# The eight positions of the reference image, in CLOCKWISE order.
POS = [
    ("N", "North", "a", "3"),
    ("NE", "North-East", "g", "4"),
    ("E", "East", "c", "2"),
    ("SE", "South-East", "f", "3"),
    ("S", "South", "k", "5"),
    ("SW", "South-West", "e", "5"),
    ("W", "West", "d", "1"),
    ("NW", "North-West", "m", "4"),
]
SHORT = [p[0] for p in POS]
COMP = [p[2] + p[3] for p in POS]
VAL = [p[3] for p in POS]


class MiniClock(Flowable):
    """
    Small vector clock drawn from the SAME eight positions as the reference
    image. Can highlight positions, draw a shape (polygon), a travelled path,
    and a right-angle marker. Used to explain concepts without leaving the
    reference picture.
    """

    def __init__(self, width, height, labels="component", highlight=(),
                 polygon=None, path=None, right_angle_at=None, arc=False,
                 title="", note=""):
        super().__init__()
        self.width, self.height = width, height
        self.labels = labels
        self.highlight = list(highlight)
        self.polygon = polygon
        self.path = path
        self.right_angle_at = right_angle_at
        self.arc = arc
        self.title = title
        self.note = note

    def wrap(self, av, ah):
        self.width = min(self.width, av)
        return self.width, self.height

    def _pt(self, i, cx, cy, r):
        a = math.radians(i * 45.0)
        return cx + r * math.sin(a), cy + r * math.cos(a)

    def draw(self):
        c = self.canv
        W, H = self.width, self.height
        top = 12 if self.title else 2
        bottom = 24 if self.note else 8
        cy = (H - top - bottom) / 2 + bottom - 2
        cx = W / 2
        r = min((H - top - bottom) / 2 - 20, (W / 2) - 58)
        if r < 20:
            r = 20

        if self.title:
            c.setFillColor(BLUE)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(cx, H - 11, self.title)

        # Ring and spokes
        c.setStrokeColor(colors.HexColor("#D5E1F3"))
        c.setLineWidth(1.1)
        c.circle(cx, cy, r, fill=0, stroke=1)
        for i in range(8):
            x, y = self._pt(i, cx, cy, r)
            c.setStrokeColor(colors.HexColor("#E7EEF9"))
            c.setLineWidth(0.8)
            c.line(cx, cy, x, y)

        # Clockwise direction arc
        if self.arc:
            c.setStrokeColor(AMBER)
            c.setLineWidth(2.0)
            a0 = math.radians(-90 + 20)
            a1 = math.radians(-90 + 300)
            # reportlab arc is counter-clockwise; draw a dashed ring instead
            c.setDash(4, 3)
            c.circle(cx, cy, r + 9, fill=0, stroke=1)
            c.setDash()

        # Shape polygon
        if self.polygon:
            c.setStrokeColor(BLUE)
            c.setFillColor(colors.HexColor("#EDF4FF"))
            c.setLineWidth(2.2)
            p = c.beginPath()
            pts = [self._pt(i, cx, cy, r) for i in self.polygon]
            p.moveTo(*pts[0])
            for x, y in pts[1:]:
                p.lineTo(x, y)
            p.close()
            c.drawPath(p, fill=1, stroke=1)

        # Travelled path (chords between consecutive points)
        if self.path:
            c.setStrokeColor(GREEN)
            c.setLineWidth(3.0)
            pts = [self._pt(i, cx, cy, r) for i in self.path]
            for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
                c.line(x1, y1, x2, y2)

        # Right-angle marker
        if self.right_angle_at is not None and self.polygon:
            v = self.right_angle_at
            others = [i for i in self.polygon if i != v]
            if len(others) >= 2:
                vx, vy = self._pt(v, cx, cy, r)
                ax, ay = self._pt(others[0], cx, cy, r)
                bx, by = self._pt(others[1], cx, cy, r)
                u = (ax - vx, ay - vy)
                w = (bx - vx, by - vy)
                lu = math.hypot(*u) or 1
                lw = math.hypot(*w) or 1
                u = (u[0] / lu, u[1] / lu)
                w = (w[0] / lw, w[1] / lw)
                s = 11
                p1 = (vx + s * u[0], vy + s * u[1])
                p2 = (p1[0] + s * w[0], p1[1] + s * w[1])
                p3 = (vx + s * w[0], vy + s * w[1])
                c.setStrokeColor(RED)
                c.setLineWidth(1.6)
                marker = c.beginPath()
                marker.moveTo(*p1)
                marker.lineTo(*p2)
                marker.lineTo(*p3)
                c.drawPath(marker, fill=0, stroke=1)

        # Centre
        c.setFillColor(NAVY)
        c.circle(cx, cy, 3.6, fill=1, stroke=0)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(cx, cy - 12, "centre")

        # Position dots and labels
        for i in range(8):
            x, y = self._pt(i, cx, cy, r)
            hot = i in self.highlight
            c.setFillColor(AMBER if hot else WHITE)
            c.setStrokeColor(AMBER if hot else colors.HexColor("#93A9CC"))
            c.setLineWidth(1.6 if hot else 1.0)
            c.circle(x, y, 7.2 if hot else 5.6, fill=1, stroke=1)

            dx = x - cx
            dy = y - cy
            norm = math.hypot(dx, dy) or 1
            lx = x + (dx / norm) * 17
            ly = y + (dy / norm) * 17

            if self.labels == "component":
                text = COMP[i]
            elif self.labels == "direction":
                text = SHORT[i]
            else:
                text = SHORT[i] + " = " + COMP[i]
            c.setFillColor(NAVY if hot else MUTED)
            c.setFont("Helvetica-Bold" if hot else "Helvetica", 8)
            if abs(dx) < 0.3 * norm:
                c.drawCentredString(lx, ly - 3, text)
            elif dx > 0:
                c.drawString(lx, ly - 3, text)
            else:
                c.drawRightString(lx, ly - 3, text)

        if self.note:
            c.setFillColor(MUTED)
            c.setFont("Helvetica-Oblique", 7.6)
            c.drawCentredString(cx, 9, self.note)


def ref_image(width):
    return Image(REF_PNG, width=width, height=width * 0.9)


def table(data, widths, header=True, small=False, align_first_left=True):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, BORDER),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER),
    ]
    if header:
        cmds.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
        cmds.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]))
    else:
        cmds.append(("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, PALE]))
    t.setStyle(TableStyle(cmds))
    return t


def th(text):
    return P(text, "th")


def td(text, bold=False, small=False):
    return P(text, "td_sm" if small else ("td_b" if bold else "td"))


# ----------------------------------------------------------------------------
# Document template (header, footer, table of contents)
# ----------------------------------------------------------------------------

class GuideDocTemplate(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, PartBanner):
            self.notify("TOCEntry", (0, "Part %d. %s" % (flowable.number, flowable.title), self.page))
        elif getattr(flowable, "_toc", None):
            level, text = flowable._toc
            self.notify("TOCEntry", (level, text, self.page))


def heading(text, level=1, toc=True):
    style = "h1" if level == 1 else "h2"
    p = P(text, style)
    # Only major headings go into the contents list; smaller sub-headings are
    # listed in the "In this part" strip on the relevant page instead.
    if toc and level == 1:
        p._toc = (0, text)
    return p


def _header_footer(canvas, doc, first=False):
    canvas.saveState()
    if not first:
        canvas.setFont("Helvetica-Bold", 7.4)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN_L, PAGE_H - 33, "ALP PSYCHO TEST  /  WATCH TABLE TEST (CLOCK TEST)")
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.6)
        canvas.line(MARGIN_L, PAGE_H - 39, PAGE_W - MARGIN_R, PAGE_H - 39)
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.6)
    canvas.line(MARGIN_L, 41, PAGE_W - MARGIN_R, 41)
    canvas.setFont("Helvetica", 7.4)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN_L, 30, "Simple English guide based on the source lecture")
    canvas.drawRightString(PAGE_W - MARGIN_R, 30, "Page %d" % doc.page)
    canvas.restoreState()


def cover_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_H - 12, PAGE_W, 12, fill=1, stroke=0)
    _header_footer(canvas, doc, first=True)
    canvas.restoreState()


def later(canvas, doc):
    _header_footer(canvas, doc, first=False)


# ----------------------------------------------------------------------------
# Story
# ----------------------------------------------------------------------------

def build_story():
    st = []

    # ---------------------------------------------------------------- COVER
    st.append(Spacer(1, 44))
    st.append(P("ALP PSYCHO TEST  /  SECTION 2  /  FOLLOWING DIRECTION TEST", "cover_kicker"))
    st.append(P("Watch Table Test", "cover_title"))
    st.append(P("(Clock Test)", "cover_title"))
    st.append(P("Every concept from the lecture, explained in plain simple English", "cover_sub"))
    st.append(P(
        "This guide takes the whole lecture you shared and rewrites it in easy English. "
        "One reference picture is created for the test, and that same picture is used again "
        "and again to explain every idea - directions, components, rotation, exchanges, "
        "word traps, shapes and maths.", "cover_body"))
    st.append(Spacer(1, 12))

    chips = [[
        P("10 minutes", "th"), P("20 questions", "th"),
        P("Answer = number", "th"), P("English only", "th"),
    ]]
    ct = Table(chips, colWidths=[CONTENT_W / 4.0] * 4, rowHeights=[27], hAlign="LEFT")
    ct.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    st.append(ct)
    st.append(Spacer(1, 20))
    img = ref_image(330)
    img.hAlign = "CENTER"
    st.append(img)
    st.append(P("The one reference image used throughout this guide.", "caption"))
    st.append(info_box(
        "Source and scope",
        'Based on the lecture at <link href="%s" color="#1B4FA0">'
        '<u>youtu.be/lN-N6OE-tRA</u></link>. It is a study summary, not an official '
        'document. Exam rules can change, so on exam day always follow the latest official '
        'RRB and RDSO instructions. The teacher\'s comments about his own test platform are '
        'reported here as his advice and claims.' % SOURCE_URL))
    st.append(P("Prepared 24 October 2026  |  Written for candidates who want simple, clear English.", "small"))
    st.append(PageBreak())

    # ---------------------------------------------------------- CONTENTS
    st.append(P("Contents", "title"))
    st.append(P("Use the page numbers to jump to the part you need. The bold entries are the "
                "main parts; the smaller entries are individual topics.", "body"))
    toc = TableOfContents()
    toc.levelStyles = [S["toc1"], S["toc2"]]
    toc.dotsMinLevel = 0
    st.append(toc)
    st.append(Spacer(1, 12))
    st.append(HRule())
    st.append(heading("How to use this guide", 1))
    st.extend(B([
        "Read Part 3 once and keep the reference image in front of you. Every example in this guide uses that same picture.",
        "Read each concept slowly. The green box is the rule you must remember; the red box is the mistake most students make.",
        "After the concepts, try Part 7 before looking at the answer key. Cover the answers with a sheet of paper.",
        "Finish with Part 9. It is one page you can revise on the morning of the exam.",
    ]))
    st.append(note_box(
        "A note about language",
        "The psycho test itself is given in Hindi and English only - there is no third language. "
        "This guide is written in English only, as you asked. In the Hindi version of the paper "
        "you will see Hindi words for these same ideas; every rule in this guide stays exactly the same."))
    st.append(Spacer(1, 8))
    st.append(info_box(
        "At a glance",
        "Time: 10 minutes. Questions: 20. Target: 20 correct. Final answer: always the digit inside "
        "the square. Weightage: 30 percent of the final result. Around half of the candidates fail "
        "this stage, so the lecture's advice is simple - learn the rules once, then practise."))
    st.append(Spacer(1, 8))
    st.append(P("<b>If you only have ten minutes today:</b> read Part 3 (the picture), then Part 9 "
                "(the revision sheet), then solve five questions from Part 7.", "body"))
    st.append(PageBreak())

    # ------------------------------------------------------------- PART 1
    st.append(PartBanner(1, "The big picture", "Where the Watch Table Test sits in the ALP psycho test"))
    st.append(heading("1.1  One post, two ways to reach it", 2))
    st.append(P(
        "The lecture begins with a doubt that many students have. There are two ways to become an "
        "Assistant Loco Pilot (ALP).", "body"))
    st.extend(B([
        "<b>Fresh vacancy (RRB ALP).</b> You apply from outside the railways, sit for the RRB ALP exam, then the psycho test.",
        "<b>Departmental / GDCE.</b> You already work in a railway zone in a lower grade. When an ALP vacancy comes in that same zone, you sit for the GDCE exam, then the psycho test, and become an ALP.",
    ]))
    st.append(rule_box(
        "The point to remember",
        "In both cases the final post is ALP, and an ALP drives a train. Because the post is the same, "
        "the psycho test is also the same. There is NO difference between the GDCE ALP psycho test "
        "and the RRB ALP psycho test. Do not waste time looking for a difference."))

    st.append(heading("1.2  The five sections of the psycho test", 2))
    st.append(P(
        "The psycho test has five main sections. The lecture counts 17 different question types "
        "across those five sections. The table below shows the full map.", "body"))
    rows = [
        [th("No."), th("Section"), th("Types"), th("What is inside it")],
        [td("1"), td("Memory Test", True), td("5"), td("Memory-based question types. Covered in a separate lecture.")],
        [td("2"), td("Following Direction Test", True), td("3"), td("<b>Table Test (alphabetic)</b>, <b>Table Test (numeric)</b>, and <b>Watch Table / Clock Test</b>. This guide is about the third one.")],
        [td("3"), td("Depth Perception Test", True), td("2"), td("Brick Test and Hidden Cube Test. Separate lectures already exist for these.")],
        [td("4"), td("Test of Power of Observation", True), td("4"), td("Yes/No Test, Find Digit 6, Find Digit 9, and Picture Placement / Position Test. These are very likely in the exam.")],
        [td("5"), td("Perceptual Speed Test", True), td("3"), td("Similarity Test, Same Figure Test (hexagonal type) and Same Figure Test (octagon type). Also very likely.")],
    ]
    st.append(table(rows, [30, 128, 44, CONTENT_W - 202]))
    st.append(P("Total: 5 + 3 + 2 + 4 + 3 = 17 question types.", "small"))
    st.append(P(
        "The teacher says he provides these topics in three forms - 17 bilingual videos, 17 English "
        "videos and 17 Hindi videos (51 videos in all). Watch the version you are comfortable in, "
        "then stop watching and start practising. The Following Direction Test is the section where "
        "your choice of language matters most, because the questions are made of words.", "body"))

    st.append(heading("1.3  Why you must take this test seriously", 2))
    st.extend(B([
        "The psycho test is a separate stage with <b>30 percent weightage</b> in the final result.",
        "Roughly <b>half the candidates fail the psycho test</b> (the teacher says 50 to 55 percent). Those candidates are out of the race immediately, no matter how high their CBT 1 and CBT 2 marks were.",
        "Only candidates who pass the psycho test are placed in the final merit list.",
        "The final merit is made from <b>CBT 2 (70 percent) + psycho test (30 percent)</b>.",
        "Selection can be missed by a margin as small as <b>0.003</b>. So every single question matters.",
    ]))
    st.append(warn_box(
        "Do not treat this as a small section",
        "A high written score does not save you if you fail the psycho stage. And a good psycho score "
        "adds real marks to your merit. Prepare for it the same way you prepare for the written exam."))

    st.append(heading("1.4  Where this test sits", 2))
    st.append(P(
        "<b>Section 2: Following Direction Test</b> has three types. Two of them are the Table Test "
        "(one alphabetic and one numeric). The third is the <b>Watch Table Test</b>, which is also "
        "called the <b>Clock Test</b>. The lecture says the Clock Test is currently the most "
        "important type in this section, so it gets its own long class.", "body"))
    st.append(PageBreak())

    # ------------------------------------------------------------- PART 2
    st.append(PartBanner(2, "The official instruction", "What RDSO says, translated into plain English"))
    st.append(heading("2.1  Who writes the rules", 2))
    st.append(P(
        "RDSO designs the psycho test syllabus. It decides which psycho tests are needed for ALP, "
        "for Station Master, for Metro exams and so on. Its written instruction for this test is "
        "short, but every line matters.", "body"))

    st.append(heading("2.2  The instruction, and what each line really means", 2))
    st.append(Callout([
        P("The official instruction (in simple words)", "box_h"),
        P("&quot;This is a test of your ability to follow a set of given directions. In this test "
          "some English letters are given in a circle along with some numbers written inside a square. "
          "The centre of the circle gives indication about direction. You will be asked questions based "
          "on this complete pattern. The answer will be a number given inside the square.&quot;", "quote"),
    ], bg=BLUE_SOFT, border=BLUE_LINE, bar=BLUE))
    st.append(Spacer(1, 8))
    st.extend(B([
        "<b>&quot;Ability to follow directions&quot;</b> - the test does not check memory or general knowledge. It checks whether you can read one instruction and follow it exactly, without adding your own ideas.",
        "<b>&quot;Letters in a circle, numbers inside a square&quot;</b> - letters sit around the ring; numbers sit in small square boxes next to them. A letter and its number together make one unit.",
        "<b>&quot;The centre of the circle gives indication about direction&quot;</b> - this is the most important line in the whole instruction. Direction is always read FROM THE CENTRE, never from outside the circle. Almost every doubt in this test disappears once you accept this line.",
        "<b>&quot;Questions based on this complete pattern&quot;</b> - one picture is given, and many questions are asked on that same picture.",
        "<b>&quot;The answer will be a number given inside the square&quot;</b> - your final answer is always a DIGIT. Never a letter. Never the letter-and-number pair.",
    ]))
    st.append(rule_box(
        "Write this on your rough sheet",
        "The answer is the number inside the square. Find the component first, then read its digit, "
        "then mark that digit. Nothing else."))

    st.append(heading("2.3  Time, questions and options", 2))
    st.extend(B([
        "<b>Time:</b> 10 minutes. &nbsp; <b>Questions:</b> 20.",
        "The options are usually the digits 1, 2, 3, 4, 5, but they may be shuffled - for example 4, 5, 2, 1, 3. Do not mark by option letter. Work out your number, then click the option that contains that number.",
        "Target: <b>20 correct out of 20 in 10 minutes</b>. Keep practising until you reach it.",
    ]))

    st.append(heading("2.4  The two sample questions shown in the lecture", 2))
    st.append(note_box(
        "Important note about the sample picture",
        "In the lecture the teacher first shows the picture printed in the RDSO guideline. That sample "
        "picture uses DIFFERENT letters and numbers (for example b3, d2, a6, g5). Later in the class "
        "he uses the exam-style picture, which is the one we use in this guide (a3, g4, c2, f3, k5, "
        "e5, d1, m4). The picture changes; the method does not. Both are solved below."))

    st.append(P("<b>Sample 1 (as printed in the guideline).</b> Question: &quot;Which number appears "
                "just opposite to the number between b3 and d2?&quot;", "body"))
    st.extend([
        P("Step 1: Find the component that lies between b3 and d2. In that picture it is a6.", "step"),
        P("Step 2: Find the component directly opposite a6. In that picture it is g5.", "step"),
        P("Step 3: The answer must be the number inside the square. g5 carries 5. <b>Answer = 5.</b>", "step"),
    ])
    st.append(P("<b>Sample 2 (as printed in the guideline).</b> Question: &quot;While moving from "
                "North to East by the shortest route, which number appears in between?&quot;", "body"))
    st.extend([
        P("Step 1: The shortest way from North to East passes through North-East.", "step"),
        P("Step 2: In the guideline picture, North-East holds d2.", "step"),
        P("Step 3: Read the digit. <b>Answer = 2.</b>", "step"),
    ])
    st.append(info_box(
        "The same two questions on OUR reference picture",
        "1) Between m4 (North-West) and g4 (North-East) sits a3 (North). Opposite a3 is k5, so the "
        "answer is <b>5</b>.<br/>"
        "2) The shortest way from North to East passes through North-East, which holds g4, so the "
        "answer is <b>4</b>.<br/>"
        "Same method, different digits. This is why you must read the picture given in YOUR question."))
    st.append(PageBreak())

    # ------------------------------------------------------------- PART 3
    st.append(PartBanner(3, "The one reference image", "Keep this picture in front of you for the rest of the guide"))
    st.append(P(
        "The exam gives you one picture and asks many questions on it. The picture below is our "
        "reference image. It has the same shape you should expect in the final exam: eight "
        "directions, a letter next to a digit, and the digit inside a square.", "body"))
    img = ref_image(CONTENT_W - 10)
    img.hAlign = "CENTER"
    st.append(img)
    st.append(P("Reference image. Directions are read from the centre. Each position has one letter and one number.",
                "caption"))

    st.append(heading("3.1  Three facts to memorise", 2))
    st.extend(B([
        "<b>Centre gives the direction.</b> Stand at the black dot in the middle and look outwards.",
        "<b>Component</b> means one letter plus its digit, for example a3 or k5. It is also called a pair.",
        "<b>Value</b> means the digit inside the square. This digit is your final answer.",
    ]))

    st.append(heading("3.2  The eight positions written out", 2))
    rows = [[th("Direction"), th("Short"), th("Component"), th("Value"),
             th("Opposite direction"), th("Opposite component")]]
    for i, (short, name, letter, digit) in enumerate(POS):
        opp = (i + 4) % 8
        rows.append([
            td(name, bold=True), td(short), td(COMP[i], bold=True), td(VAL[i], bold=True),
            td(POS[opp][1]), td(COMP[opp], bold=True),
        ])
    st.append(table(rows, [96, 44, 82, 46, 130, CONTENT_W - 398]))
    st.append(P("Clockwise from North: N, NE, E, SE, S, SW, W, NW - then back to N.", "small"))
    st.append(note_box(
        "Practical tip from the lecture",
        "As soon as the section starts, draw this circle roughly on your rough sheet, or take a "
        "screenshot of the figure if the interface allows it. Then you can mark steps, swaps and "
        "shapes on paper instead of holding everything in your head."))

    st.append(heading("3.3  Check yourself on the picture", 2))
    st.append(P("Answer these five without looking back at the table. They use only the ideas you "
                "have met so far.", "body"))
    rows = [
        [th("No."), th("Quick question"), th("Answer")],
        [td("1"), td("What digit is in the West?"), td("1", True)],
        [td("2"), td("Which two components carry the digit 5?"), td("k5 and e5", True)],
        [td("3"), td("What is directly across from g4?"), td("e5, value 5", True)],
        [td("4"), td("Name the direction between North and East."), td("North-East", True)],
        [td("5"), td("Which component comes right after k5, clockwise?"), td("e5, value 5", True)],
    ]
    st.append(table(rows, [30, 275, CONTENT_W - 305]))
    st.append(rule_box(
        "Why this matters",
        "In the real test you get about 30 seconds for each question. If you have to stop and work "
        "out what &quot;North-East&quot; or &quot;value&quot; means, you lose that time. Make the "
        "picture automatic before exam day."))
    st.append(PageBreak())

    # ------------------------------------------------------------- PART 4
    st.append(PartBanner(4, "Different pictures, same concept", "Do not get confused by design changes"))
    st.append(P(
        "When you practise on different books, apps and test series, you will meet the SAME test "
        "drawn in several different ways. Students often think it is a new topic. It is not. The "
        "teacher lists these differences in the class.", "body"))
    st.extend(B([
        "Some pictures print the direction names (N, E, S, W) inside the circle near the centre. Some do not print them at all - then you must remember the directions yourself.",
        "Some pictures print the letter and the digit joined together (a3). Some print them separately with a small gap. Both mean the same component.",
        "Some pictures draw a clear square around the digit. Some do not draw any box. The digit still means the value.",
        "The letters may be inside small circles, or just written as plain text. Only the design changes.",
    ]))
    st.append(warn_box(
        "One design the teacher tells you to leave aside",
        "A few practice pictures print the direction names OUTSIDE the circle. The teacher says this "
        "type does NOT come in the final exam, because putting the directions outside changes the "
        "whole concept. He keeps that type for a later class. Do not mix it with the exam pattern."))
    st.append(rule_box(
        "What you should expect in the final exam",
        "Eight directions, with direction names near the centre; a letter and a digit at each "
        "position; the digit inside a square. That is the exam-style picture, and it is exactly the "
        "reference image on the previous page."))
    st.append(P(
        "So when a practice figure looks strange, do not panic. Ask yourself three questions: where "
        "is the centre, which letter sits with which digit, and what digit is in the square. The "
        "concept is identical in every design.", "body"))
    st.append(PageBreak())

    # ------------------------------------------------------------- PART 5
    st.append(PartBanner(5, "The concepts, one by one", "Eleven ideas explained on the same reference image"))
    st.append(P(
        "The teacher lists the concepts before he starts solving questions. Here they are in the "
        "same order, each with a plain-English meaning, the rule, a worked example on our reference "
        "picture, and the mistake to avoid.", "body"))
    st.append(info_box(
        "The eleven concepts in this part",
        "1 Direction &nbsp;|&nbsp; 2 Component, value, pair, frequency &nbsp;|&nbsp; 3 Rotation "
        "(left/right, clockwise/anti-clockwise) &nbsp;|&nbsp; 4 Preceding and succeeding &nbsp;|&nbsp; "
        "5 Exchange (four kinds) &nbsp;|&nbsp; 6 From and of &nbsp;|&nbsp; 7 In front and opposite "
        "&nbsp;|&nbsp; 8 Shapes made by joining points &nbsp;|&nbsp; 9 Vertex and perpendicular "
        "vertex &nbsp;|&nbsp; 10 Alphabetical order &nbsp;|&nbsp; 11 Simple maths."))

    # C1 -----------------------------------------------------------------
    st.append(heading("Concept 1 - Direction", 2))
    st.append(P(
        "Think of the map of India. North is up towards Kashmir, South is down towards Kanyakumari, "
        "East is to the right, West is to the left towards Gujarat. Between them come four more "
        "directions: North-East, North-West, South-East and South-West.", "body"))
    st.append(P(
        "If you stand facing East, North is on your left, South is on your right, and West is behind "
        "you. In this test, however, you never use your own body position. You always stand at the "
        "<b>centre of the circle</b> and look outwards.", "body"))
    mc1 = MiniClock(CONTENT_W, 215, labels="direction", highlight=[0, 2, 4, 6],
                    title="The eight directions, read from the centre",
                    note="North is up, East is right, South is down, West is left.")
    st.append(mc1)
    st.append(rule_box(
        "Rule",
        "Read every direction from the centre: N (a3), NE (g4), E (c2), SE (f3), S (k5), "
        "SW (e5), W (d1), NW (m4)."))
    st.extend([
        P("Example: &quot;What is in the North?&quot; - a3, value <b>3</b>.", "step"),
        P("Example: &quot;What is in the South-West?&quot; - e5, value <b>5</b>.", "step"),
    ])
    st.append(warn_box("Mistake to avoid",
                       "Never decide a direction by looking at the circle from outside. The centre is your "
                       "viewpoint, every single time."))

    # C2 -----------------------------------------------------------------
    st.append(heading("Concept 2 - Component, value, pair and frequency", 2))
    st.append(P(
        "A <b>component</b> is one letter plus one digit written together, for example a3. The teacher "
        "also calls it a <b>pair</b>. The <b>value</b> of a component is the digit inside the square - "
        "that is the number you finally mark.", "body"))
    st.extend(B([
        "In a3, the letter is <b>a</b> and the digit is <b>3</b>. Value of a3 = 3. Value of the letter a = 3.",
        "East holds c2, so the value of the East component = 2.",
        "South holds k5, so the value of the South component = 5.",
    ]))
    st.append(P(
        "<b>Pair</b> means the same digit appears twice on the clock. In our picture the digits are "
        "3, 4, 2, 3, 5, 5, 1, 4. So 3 has a pair (a3 and f3), 4 has a pair (g4 and m4), 5 has a pair "
        "(k5 and e5). Digits 2 and 1 do not have a pair.", "body"))
    st.append(P(
        "A <b>continuous pair</b> means those two equal digits stand next to each other on the ring. "
        "Here 5 and 5 are neighbours (k5 at South, e5 at South-West), so <b>5 is a continuous pair</b>. "
        "The two 3s are far apart, and the two 4s are far apart, so they are pairs but not continuous pairs.", "body"))
    st.append(P(
        "<b>Frequency</b> means how many times a digit appears - but only on the path the question "
        "asks about. It does not always mean the whole clock.", "body"))
    mc2 = MiniClock(CONTENT_W, 205, labels="component",
                    highlight=[2, 3, 4, 5, 6], path=[2, 3, 4, 5, 6],
                    title="Frequency example: walking from East to West",
                    note="Green path = c2, f3, k5, e5, d1. The digit 5 appears twice on this path.")
    st.append(mc2)
    st.extend([
        P("Example A: From East to West (clockwise) the components are c2, f3, k5, e5, d1. The frequency of 5 is <b>2</b>.", "step"),
        P("Example B: From West to North the components are d1, m4, a3. The digit 4 appears twice on the whole clock but only <b>1</b> time on this path, so the answer is 1.", "step"),
    ])
    st.append(warn_box(
        "Mistake to avoid",
        "Do not count the whole clock when the question gives you a route. Count only the positions "
        "you actually pass, including or excluding the ends exactly as the question says."))

    # C3 -----------------------------------------------------------------
    st.append(heading("Concept 3 - Rotation: left, right, clockwise, anti-clockwise", 2))
    st.append(P(
        "<b>Clockwise</b> is the direction a clock's hands move. On our circle that is "
        "N, NE, E, SE, S, SW, W, NW, then back to N. <b>Anti-clockwise</b> is the exact reverse: "
        "N, NW, W, SW, S, SE, E, NE, back to N.", "body"))
    st.append(P(
        "In this test <b>right = clockwise</b> and <b>left = anti-clockwise</b>. But there is a catch: "
        "you must imagine you are standing at the centre facing the direction in the question. Your "
        "right and left are then decided from the centre, not from where you sit.", "body"))
    mc3 = MiniClock(CONTENT_W, 200, labels="component", highlight=[0, 1, 7], arc=True,
                    title="One step right and one step left from a3 (North)",
                    note="Right from a3 is g4. Left from a3 is m4.")
    st.append(mc3)
    st.append(rule_box(
        "Rule",
        "Always stand at the centre. Right = clockwise. Left = anti-clockwise."))
    st.extend([
        P("One step right from a3 (N) is g4 (NE), value <b>4</b>.", "step"),
        P("One step left from a3 (N) is m4 (NW), value <b>4</b>.", "step"),
        P("Two steps right from g4 (NE) goes E then SE, so f3, value <b>3</b>.", "step"),
    ])
    st.append(warn_box("Mistake to avoid",
                       "Do not use your own left and right while staring at the page. Turn with the "
                       "centre point of the circle."))

    # C4 -----------------------------------------------------------------
    st.append(heading("Concept 4 - Preceding and succeeding", 2))
    st.append(P(
        "<b>Preceding</b> means the one just before. <b>Succeeding</b> means the one just after. "
        "The problem is: before and after in which direction?", "body"))
    st.append(rule_box(
        "Rule",
        "Always use CLOCKWISE order to decide before and after. So preceding = one step "
        "anti-clockwise, and succeeding = one step clockwise. Never use the printed order on the page."))
    st.extend([
        P("Preceding of a3 (N) is m4 (NW), value <b>4</b>.", "step"),
        P("Succeeding of a3 (N) is g4 (NE), value <b>4</b>.", "step"),
        P("Preceding of m4 (NW) is d1 (W), value <b>1</b>. Succeeding of m4 is a3 (N), value <b>3</b>.", "step"),
    ])
    st.append(note_box(
        "Why students get this wrong",
        "On paper, g4 is printed to the right of a3, so it looks like it comes &quot;before&quot;. "
        "It does not. The clock moves clockwise, so the position you passed just before reaching "
        "North is North-West. Follow the clock, not the page."))

    # C5 -----------------------------------------------------------------
    st.append(heading("Concept 5 - Exchange: change only the named part", 2))
    st.append(P(
        "Exchange questions are very common. There are four kinds, and the golden rule for all of "
        "them is: <b>change only the part the question names. Do nothing else on your own.</b>", "body"))
    st.append(P("<b>1. Exchange of direction.</b> Swap the two direction names. The components do "
                "not move physically. If you swap North and South, the label &quot;South&quot; now sits "
                "where &quot;North&quot; was. Question: &quot;What is in the South now?&quot; The "
                "component there is still a3, so the answer is <b>3</b> - not 5.", "body"))
    st.append(P("<b>2. Exchange of component.</b> Swap the full pairs, letter and digit both. Swap a3 "
                "and k5: South now holds a3, North holds k5. Question: &quot;What is in the South "
                "now?&quot; Answer a3, value <b>3</b>. The direction names did not change.", "body"))
    st.append(P("<b>3. Exchange of letter.</b> Swap only the letters. North a3 and South k5 become "
                "North k3 and South a5. The digits stay. Question: &quot;Value of the North "
                "component?&quot; It is still <b>3</b>.", "body"))
    st.append(P("<b>4. Exchange of digit / number.</b> Swap only the digits. North becomes a5 and "
                "South becomes k3. Question: &quot;Value of the North component?&quot; It is now "
                "<b>5</b>.", "body"))
    rows = [
        [th("Type of exchange"), th("What actually moves"), th("Does the value at a place change?")],
        [td("Direction", True), td("Only the direction labels swap. Components stay where they are."), td("The label you read changes, so you may read a different component.")],
        [td("Component", True), td("The whole pair moves - letter and digit together."), td("Yes. Values swap places.")],
        [td("Letter", True), td("Only letters swap. Digits stay with their positions."), td("<b>No.</b> Values do not change anywhere. This is a useful shortcut.")],
        [td("Digit / number", True), td("Only digits swap. Letters stay."), td("Yes. Just swap the two values.")],
    ]
    st.append(table(rows, [112, 205, CONTENT_W - 317]))
    st.append(rule_box(
        "Speed trick",
        "If the question exchanges only LETTERS, do not redraw anything - every value stays the same. "
        "If it exchanges only DIGITS, just swap the two values. Only a component exchange or a "
        "direction exchange needs careful redrawing."))
    st.append(warn_box(
        "Mistake to avoid",
        "&quot;Exchange of component&quot; and &quot;exchange of letter&quot; are not the same "
        "instruction. In a component exchange both the letter and the digit move; in a letter "
        "exchange only the letter moves."))

    # C6 -----------------------------------------------------------------
    st.append(heading("Concept 6 - &quot;From&quot; and &quot;of&quot;", 2))
    st.append(P(
        "This is a pure word trap. The two sentences look almost the same, but the answers are one "
        "step apart.", "body"))
    st.append(rule_box(
        "Rule",
        "<b>FROM = INCLUDE the starting point in your count.</b> &nbsp; "
        "<b>OF = EXCLUDE (leave out) the starting point.</b> "
        "Easy memory trick: OF sounds like OFF - leave it OFF. FROM starts FROM that point, so count it."))
    st.extend([
        P("&quot;Second right <b>from</b> a3&quot; - count a3 as 1 and g4 as 2. You stop at g4, value <b>4</b>.", "step"),
        P("&quot;Second right <b>of</b> a3&quot; - leave out a3; g4 is 1 and c2 is 2. You stop at c2, value <b>2</b>.", "step"),
        P("The same rule works for left, and for third or fourth steps.", "step"),
    ])
    st.append(note_box(
        "Why the teacher spends time on this",
        "He says students do not really misunderstand this - they simply forget which word does what. "
        "Underline FROM or OF in the question before you start counting. One underlined word protects "
        "one full mark."))

    # C7 -----------------------------------------------------------------
    st.append(heading("Concept 7 - &quot;In front of&quot; and &quot;opposite&quot;", 2))
    st.append(P(
        "The teacher calls this the biggest confusion in the whole test. He says books, teachers and "
        "students argue about it, and one popular book even gives different answers in two different "
        "chapters. His answer is simple: go back to the RDSO line - the centre of the circle gives "
        "the direction.", "body"))
    st.append(P(
        "The reason for the confusion is that <b>directions live at the centre</b>, while "
        "<b>components live on the ring</b>. They are not the same kind of thing, so the same two "
        "words behave differently.", "body"))

    st.append(P("<b>When the word after it is a DIRECTION:</b>", "h3"))
    st.extend(B([
        "&quot;In front of North&quot; = look from the centre towards North = a3, value <b>3</b>.",
        "&quot;Opposite of North&quot; = turn to the opposite direction, South = k5, value <b>5</b>.",
        "&quot;In front of East&quot; = c2 (2). &quot;Opposite of East&quot; = West = d1 (1).",
        "&quot;In front of West&quot; = d1 (1). &quot;Opposite of West&quot; = East = c2 (2).",
        "&quot;In front of South&quot; = k5 (5). &quot;Opposite of South&quot; = North = a3 (3).",
    ]))
    st.append(P("<b>When the word after it is a COMPONENT:</b>", "h3"))
    st.extend(B([
        "&quot;In front of a3&quot; = the component straight across the circle = k5, value <b>5</b>.",
        "&quot;Opposite of a3&quot; = the very same k5, value <b>5</b>.",
        "&quot;In front of d1&quot; and &quot;opposite of d1&quot; both give c2, value <b>2</b>.",
    ]))
    st.append(rule_box(
        "Rule in one line",
        "For a DIRECTION, in front and opposite are DIFFERENT. For a COMPONENT, in front and "
        "opposite are THE SAME."))
    mc7 = MiniClock(CONTENT_W, 195, labels="both", highlight=[0, 2, 6],
                    title="North is a direction; a3 is a component",
                    note="In front of North = a3. Opposite of North = k5. In front of a3 = opposite of a3 = k5.")
    st.append(mc7)
    st.append(warn_box(
        "Mistake to avoid",
        "Do not carry the &quot;North is opposite South&quot; habit into a question about a component. "
        "Read the word after &quot;in front of&quot;: if it is a direction, look along that ray; if it "
        "is a component, jump across the circle."))

    # C8 -----------------------------------------------------------------
    st.append(heading("Concept 8 - Shapes made by joining points", 2))
    st.append(P(
        "Some questions ask you to join three or four named components to make a triangle, a "
        "rectangle, a square or a rhombus, and then ask a question about that shape. The trap is "
        "in the words <b>&quot;inside this shape&quot;</b>.", "body"))
    mc8 = MiniClock(CONTENT_W, 210, labels="component", highlight=[0, 2, 4, 6],
                    polygon=[0, 2, 4, 6],
                    title="Join a3, c2, k5, d1 - a rhombus inside the clock",
                    note="Only these four corners count when the question says 'inside this shape'.")
    st.append(mc8)
    st.extend(B([
        "Join a3 (N), c2 (E), k5 (S) and d1 (W). You get a diamond shape, a rhombus.",
        "<b>Inside this rhombus</b>, right of a3 is c2, value <b>2</b>. On the full clock, right of a3 is g4, value 4.",
        "<b>Inside this rhombus</b>, right of c2 is k5, value <b>5</b>. On the full clock, right of c2 is f3, value 3.",
        "Same idea works for triangles, rectangles and squares: once you are told &quot;inside the shape&quot;, the other positions on the ring stop existing for that question.",
    ]))
    st.append(warn_box(
        "Mistake to avoid",
        "&quot;Inside the shape&quot; is a condition, not a decoration. If you ignore it you will "
        "answer using the full clock and lose the mark."))

    # C9 -----------------------------------------------------------------
    st.append(heading("Concept 9 - Vertex and perpendicular vertex", 2))
    st.append(P(
        "In ordinary geometry every corner of a triangle is a vertex. In this test the teacher uses "
        "the words in a special, narrow way:", "body"))
    st.extend(B([
        "<b>Vertex of the triangle</b> = the corner where the TWO EQUAL sides of an isosceles triangle meet.",
        "<b>Perpendicular vertex</b> = that same corner, but the two equal sides also meet at a 90 degree right angle.",
    ]))
    st.append(P(
        "How to spot the equal sides on the clock: count the steps along the ring between the three "
        "points. If two of the gaps have the same number of steps, those two sides are equal, and "
        "they meet at the point they share.", "body"))

    tri = Table(
        [[MiniClock((CONTENT_W - 16) / 2, 205, labels="component",
                    highlight=[0, 3, 5], polygon=[0, 3, 5],
                    title="Vertex = a3",
                    note="a3-e5 and a3-f3 are equal sides."),
          MiniClock((CONTENT_W - 16) / 2, 205, labels="component",
                    highlight=[3, 5, 7], polygon=[3, 5, 7], right_angle_at=5,
                    title="Perpendicular vertex = e5",
                    note="e5-m4 and e5-f3 are equal AND make 90 degrees.")]],
        colWidths=[(CONTENT_W - 16) / 2, (CONTENT_W - 16) / 2], hAlign="LEFT")
    tri.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    st.append(tri)
    st.extend([
        P("Example 1: join a3 (N), e5 (SW) and f3 (SE). The gap from a3 to e5 is 3 steps, and from a3 to f3 is also 3 steps. The equal sides meet at a3. So the vertex is a3, value <b>3</b>.", "step"),
        P("Example 2: join m4 (NW), e5 (SW) and f3 (SE). The gaps e5 to m4 and e5 to f3 are both 2 steps, and they meet at e5 at a right angle. So e5 is the perpendicular vertex, value <b>5</b>.", "step"),
    ])
    st.append(rule_box(
        "Rule",
        "Every perpendicular vertex is also a vertex, but not every vertex is a perpendicular "
        "vertex. Look for the equal sides first, then check the 90 degree angle."))

    # C10 ----------------------------------------------------------------
    st.append(heading("Concept 10 - Alphabetical order", 2))
    st.append(P(
        "Here you completely ignore the digits. Arrange only the letters from A to Z, then give the "
        "value of the letter the question asks for.", "body"))
    rows = [
        [th("Letters in our picture"), th("In A-Z order"), th("First letter"), th("Last letter")],
        [td("a, g, c, f, k, e, d, m"), td("a, c, d, e, f, g, k, m"), td("a - value 3", True), td("m - value 4", True)],
    ]
    st.append(table(rows, [150, 150, 96, CONTENT_W - 396]))
    st.extend(B([
        "&quot;Smallest letter in alphabetical order, what is its value?&quot; - a, value <b>3</b>.",
        "&quot;Largest letter in alphabetical order, what is its value?&quot; - m, value <b>4</b>.",
        "If a question asks for the letter just after d, that is e, value <b>5</b>. The letter just before g is f, value <b>3</b>.",
    ]))
    st.append(note_box("Mistake to avoid",
                       "Do not sort by the digits. In this picture 1 is the smallest digit (d1), but d "
                       "is not the first letter. The question says alphabetical, so sort the LETTERS."))

    # C11 ----------------------------------------------------------------
    st.append(heading("Concept 11 - Simple maths on the value", 2))
    st.append(P(
        "First find the value of the component. Then do the maths the question asks: add, subtract, "
        "multiply, square, square root, cube or cube root.", "body"))
    rows = [[th("Direction"), th("Component"), th("Value"), th("Square"), th("Cube")]]
    for i, (short, name, letter, digit) in enumerate(POS):
        v = int(digit)
        rows.append([td(name), td(COMP[i], True), td(str(v), True),
                     td(str(v * v)), td(str(v * v * v))])
    st.append(table(rows, [130, 100, 70, 95, CONTENT_W - 395]))
    st.append(P(
        "Square roots and cube roots are normally asked on clean numbers: square root of 1 = 1, "
        "of 4 = 2, of 9 = 3; cube root of 1 = 1, of 8 = 2, of 27 = 3, of 64 = 4, of 125 = 5.", "small"))
    st.extend(B([
        "&quot;What is the square root of the component in the North-East?&quot; - g4 has value 4, square root of 4 is <b>2</b>.",
        "&quot;What is the cube root of the value in the West?&quot; - d1 has value 1, cube root of 1 is <b>1</b>.",
        "Add the North and East values: 3 + 2 = <b>5</b>. Subtract East from South: 5 - 2 = <b>3</b>.",
        "Multiply the North-West and West values: 4 x 1 = <b>4</b>.",
    ]))
    st.append(warn_box(
        "Mistake to avoid",
        "Do the maths on the VALUE (the digit in the square), never on the letter and never on the "
        "whole pair. And read the question fully - it may ask for a square in one line and a square "
        "root in the next."))
    st.append(PageBreak())

    # ------------------------------------------------------------- PART 6
    st.append(PartBanner(6, "Worked examples", "Full reasoning, step by step, on our reference picture"))
    st.append(P(
        "For every question the method is the same four moves: <b>read the key word</b>, "
        "<b>find the place</b>, <b>apply the rule</b>, <b>mark the digit in the square</b>.", "body"))

    worked = [
        ("W1. Which number appears just opposite to the number between m4 and g4?",
         ["m4 is North-West and g4 is North-East. The position between them is North, which holds a3.",
          "Opposite a3 is k5 at South.",
          "The digit in that square is 5. Answer: 5."]),
        ("W2. Moving from North to East by the shortest route, which number is in between?",
         ["The short way from North to East passes through North-East.",
          "North-East holds g4.",
          "Digit = 4. Answer: 4."]),
        ("W3. What is the value of the component in the South?",
         ["South holds k5.",
          "The digit in the square is 5. Answer: 5."]),
        ("W4. Second right of a3?",
         ["The word OF means exclude a3.",
          "Right = clockwise. 1st is g4, 2nd is c2.",
          "Digit = 2. Answer: 2."]),
        ("W5. Which component precedes a3?",
         ["Preceding is decided in clockwise order, so it is one step anti-clockwise.",
          "One step anti-clockwise from a3 (N) is m4 (NW).",
          "Digit = 4. Answer: 4."]),
        ("W6. Exchange the letters of the North and South components. Value of the North component?",
         ["Only the letters move. North a3 becomes k3; South k5 becomes a5.",
          "The digits did not change, so the North value is still 3.",
          "Answer: 3. (This is the shortcut: a letter exchange never changes any value.)"]),
        ("W7. In front of East? And opposite of East?",
         ["The word after the phrase is a DIRECTION, so read from the centre.",
          "In front of East = the component on the East side = c2, value 2.",
          "Opposite of East = West = d1, value 1. Two different answers."]),
        ("W8. Join a3, c2, k5, d1. Inside that shape, what is right of c2?",
         ["The four points make a rhombus. The words 'inside that shape' limit us to these four corners.",
          "Moving clockwise around the rhombus, after c2 comes k5.",
          "Digit = 5. Answer: 5. On the full clock it would have been f3."]),
        ("W9. Which letter is last in A-Z order here, and what is its value?",
         ["Letters are a, g, c, f, k, e, d, m. Sorted: a, c, d, e, f, g, k, m.",
          "The last letter is m, which sits at m4.",
          "Digit = 4. Answer: 4."]),
        ("W10. From West to North, what is the frequency of 4?",
         ["The path is d1 (W), m4 (NW), a3 (N).",
          "The digit 4 appears once on this path, although it appears twice on the whole clock.",
          "Answer: 1."]),
    ]
    for title, steps in worked:
        block = [P(title, "h3")]
        for i, s in enumerate(steps, 1):
            block.append(P("%d. %s" % (i, s), "step"))
        block.append(Spacer(1, 3))
        st.append(KeepTogether(block))
    st.append(PageBreak())

    # ------------------------------------------------------------- PART 7
    st.append(PartBanner(7, "Practice set", "20 questions - answers are on the next page"))
    st.append(P("Use the reference image. Write your answers down before you turn the page.", "body"))
    questions = [
        "What is the value of the component in the North-East?",
        "Which component is opposite to f3? Give its value.",
        "Move three steps clockwise from d1. Where do you stop?",
        "Move two steps anti-clockwise from k5. Where do you stop?",
        "Which component succeeds e5? Give its value.",
        "Which component precedes c2? Give its value.",
        "Exchange the direction names North and South. What is in the South now?",
        "Exchange the components a3 and k5. What is in the South now?",
        "Exchange the digits of the North and South components. What is the new North value?",
        "Second right FROM g4 - which component?",
        "Second right OF g4 - which component?",
        "&quot;In front of South&quot; - which component and value?",
        "&quot;Opposite of South&quot; - which component and value?",
        "&quot;In front of d1&quot; - what is the value?",
        "&quot;Opposite of d1&quot; - what is the value?",
        "Which digit makes a continuous pair in this picture?",
        "From North to South by the shortest clockwise route, what is the frequency of 3?",
        "Join a3, c2, k5, d1. Inside that shape, what is right of a3?",
        "Join a3, e5, f3. At which point do the two equal sides meet? Give its value.",
        "What is the square root of the value in the North-West?",
    ]
    half = (len(questions) + 1) // 2
    left = [[td("%d. %s" % (i + 1, q), small=True)] for i, q in enumerate(questions[:half])]
    right = [[td("%d. %s" % (i + half + 1, q), small=True)] for i, q in enumerate(questions[half:])]
    colw = (CONTENT_W - 12) / 2
    qtab = Table([[table(left, [colw], header=False), table(right, [colw], header=False)]],
                 colWidths=[colw + 6, colw + 6], hAlign="LEFT")
    qtab.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    st.append(qtab)
    st.append(Spacer(1, 10))
    st.append(note_box(
        "Before you look",
        "Questions 7 and 8 look almost the same but use two different exchange types. Questions 12 "
        "to 15 test the in-front/opposite rule. If you get those right, you have understood the "
        "hardest part of this test."))
    st.append(PageBreak())

    st.append(heading("Answer key with short reasons", 1))
    answers = [
        ("4", "North-East holds g4."),
        ("m4, value 4", "f3 is South-East; opposite is North-West."),
        ("g4, value 4", "d1 is West: NW, N, NE."),
        ("c2, value 2", "k5 is South: SE, then E."),
        ("d1, value 1", "Succeeding = one step clockwise from e5 (SW) to W."),
        ("g4, value 4", "Preceding = one step anti-clockwise from c2 (E) to NE."),
        ("a3, value 3", "Only the labels swap; a3 has not moved."),
        ("a3, value 3", "The whole pair moved to the South; directions stayed."),
        ("5", "North a3 becomes a5; South k5 becomes k3."),
        ("c2, value 2", "FROM counts g4 as 1, then c2 as 2."),
        ("f3, value 3", "OF skips g4; c2 is 1, f3 is 2."),
        ("k5, value 5", "After a direction, 'in front of' points along that ray."),
        ("a3, value 3", "Opposite of a direction is the other direction."),
        ("2", "For a component, in front = opposite. Across from d1 is c2."),
        ("2", "Same reason as 14; both give c2."),
        ("5", "k5 and e5 are neighbours on the ring."),
        ("2", "Path: a3, g4, c2, f3, k5 - the digit 3 appears twice."),
        ("c2, value 2", "Inside the rhombus the next corner after a3 is c2."),
        ("a3, value 3", "The equal sides a3-e5 and a3-f3 meet at a3."),
        ("2", "North-West is m4, value 4; square root of 4 is 2."),
    ]
    rows = [[th("No."), th("Answer"), th("Why")]]
    for i, (ans, why) in enumerate(answers, 1):
        rows.append([td(str(i), True), td(ans, True), td(why, small=True)])
    st.append(table(rows, [30, 92, CONTENT_W - 122]))
    st.append(PageBreak())

    # ------------------------------------------------------------- PART 8
    st.append(PartBanner(8, "Exam screen, scoring and practice plan", "What the teacher says after the concepts"))
    st.append(heading("8.1  What the test screen looks like", 2))
    st.extend(B([
        "A <b>5-minute instruction screen</b> appears before the section starts. In the real exam you must sit through it. When practising at home you can skip it so you get more question time.",
        "In the latest exams the question panel <b>scrolls</b>. Only part of the question is visible at first. You scroll to read the rest, then answer, then scroll back for the next one. This wastes a lot of seconds.",
        "The teacher advises practising <b>both</b> versions: questions with scrolling and questions without scrolling. Students who only practise the easy version are shocked in the exam.",
        "Answers are <b>auto-saved</b>. You do not press a Save button. Learn the interface before exam day so you do not panic.",
    ]))

    st.append(heading("8.2  Time and accuracy target", 2))
    st.append(P(
        "You get 10 minutes for 20 questions. The target is <b>20 out of 20</b>. The teacher says "
        "that with a scrolling panel many students manage only 10 or 11 questions before time runs "
        "out. Speed in this test comes from practice, not from learning more theory.", "body"))
    st.append(rule_box(
        "The teacher's main message",
        "Psycho test is all about practice. Watch the concept lecture ONCE, understand it, and then "
        "only practise. He repeats this many times in the class."))

    st.append(heading("8.3  The order of preparation he recommends", 2))
    st.extend([
        P("1. Watch the video lectures (the mobile app is fine for this).", "step"),
        P("2. Practise <b>sectional tests</b> first - for this topic, the Watch Table Test inside the Following Direction Test section.", "step"),
        P("3. Then practise <b>full tests</b>. A full test puts Memory, Watch Table, Brick, Picture Position, Octagon and the rest one after another. That is where mental pressure appears.", "step"),
        P("4. Practise on a <b>laptop</b>. The teacher calls it mandatory - your own, a friend's, or a cyber cafe. The real interface is tough and a phone does not prepare you for it.", "step"),
    ])
    st.append(note_box(
        "Why full tests matter",
        "In a sectional test you may score 20/20 easily. In the full test your mind is tired and "
        "under pressure from the sections that came before. Only full-test practice teaches you to "
        "handle that pressure."))

    st.append(heading("8.4  Score, rank and T-score (as explained in the lecture)", 2))
    st.extend(B([
        "The practice report shows your <b>score</b>, your <b>rank</b>, your <b>accuracy</b>, the <b>average</b> of everyone who attempted that test, and a <b>T-score</b>.",
        "The T-score is calculated from real data - your score, the mean, the standard deviation and the variance of all attempts. Because the data is live, your T-score can change when more students take the same test.",
        "In that test series, a T-score <b>above 42 means qualify</b> and <b>below 42 means disqualify</b>.",
        "The teacher warns that some other platforms show fixed or manipulated T-scores, for example always showing 62 for a score of 17 no matter how many students attempt. He suggests taking free tests on several platforms, comparing them, and asking friends for feedback before you pay for any test series.",
    ]))
    st.append(P(
        "These are the teacher's own claims about his platform and others, reported here so you know "
        "what he said. Whatever platform you use, the useful habit is the same: check your score, "
        "your accuracy and your rank after every test, and watch whether they improve.", "small"))

    st.append(heading("8.5  This lecture is Part 1", 2))
    st.append(P(
        "At the end of the class the teacher says this is <b>Part 1</b>. He plans a Part 2 with about "
        "40 to 45 solved questions, quick methods, speed tricks and ways to save time - including how "
        "to answer some questions without reading the whole sentence. He also asks students to leave "
        "their remaining doubts in the comments so he can clear them in that class.", "body"))
    st.append(info_box(
        "What to do next after this guide",
        "Revise Part 9, then solve as many Watch Table sections as you can against a timer. When you "
        "can get 20/20 in 10 minutes, move to full psycho tests."))

    st.append(heading("8.6  Other course details mentioned in the lecture", 2))
    st.append(P(
        "A large part of the class is the teacher describing his own preparation platform. These "
        "are his statements, not official RRB information, and they are listed here only so that "
        "nothing from the lecture is left out.", "body"))
    st.extend(B([
        "He asks all GDCE ALP and RRB ALP students to join his Telegram group for updates. The link is in the video description; he expects 75,000+ students.",
        "He says the platform allows <b>many attempts per test</b> (he shows nine for the Watch Table section) and that the limit can be increased.",
        "He offers <b>a website and a mobile app</b>: lectures on the phone, psycho practice on a laptop. He quotes <b>50+ full tests</b>, <b>300+ sectional tests</b>, Hindi and English test series, a claimed exam-like interface, error-free tests and <b>one-year validity</b>.",
        "He says one ALP full test is free so you can see the pattern before paying. Registration needs a name, email, mobile number and password; OTP login and forgot-password are available.",
    ]))
    st.append(note_box(
        "Keep your own judgement",
        "He also claims other platforms show fixed T-scores. His advice: take free tests on several "
        "platforms, compare them, ask friends, and only then pay. Whatever you choose, what matters "
        "is how many timed tests you complete."))

    st.append(heading("8.7  Exam-day checklist", 2))
    st.extend(B([
        "Read every direction from the centre of the circle.",
        "Underline the key words: from, of, in front, opposite, inside the shape, preceding, succeeding, letter, digit, direction, component.",
        "Change only the part the question names in an exchange question.",
        "Always mark the digit in the square - never the letter.",
        "If the options are shuffled, match your number to the right option instead of marking by position.",
        "Sketch the figure on your rough sheet at the start of the section.",
        "Do not spend too long on one question; 20 questions in 10 minutes means about 30 seconds each.",
        "Follow the latest official RRB and RDSO instructions given on the exam day.",
    ]))
    st.append(PageBreak())

    # ------------------------------------------------------------- PART 9
    st.append(PartBanner(9, "One-page revision sheet", "Read this on the morning of the exam"))
    st.append(Callout([
        P("The seven lines that matter most", "box_h"),
        P("1. The centre of the circle gives the direction. Always stand at the centre.", "box_b"),
        P("2. Component = letter + digit (a3). Value = the digit in the square. The value is your answer.", "box_b"),
        P("3. Clockwise: N, NE, E, SE, S, SW, W, NW. Right = clockwise. Left = anti-clockwise.", "box_b"),
        P("4. Preceding = one step before (anti-clockwise). Succeeding = one step after (clockwise).", "box_b"),
        P("5. FROM includes the start point. OF excludes it.", "box_b"),
        P("6. Direction: in front is NOT opposite. Component: in front IS opposite.", "box_b"),
        P("7. Exchange only what is named: direction, component, letter or digit.", "box_b"),
    ], bg=GREEN_SOFT, border=colors.HexColor("#BFE4D2"), bar=GREEN))
    st.append(Spacer(1, 8))

    st.append(heading("Word meanings at a glance", 2))
    rows = [
        [th("Word in the question"), th("What it means in this test")],
        [td("Component / pair", True), td("One letter plus one digit, for example a3 or k5.")],
        [td("Value", True), td("The digit inside the square. This is always your final answer.")],
        [td("Pair", True), td("The same digit appears two times on the clock.")],
        [td("Continuous pair", True), td("A pair whose two digits are next to each other on the ring.")],
        [td("Frequency", True), td("How many times a digit appears on the path named in the question.")],
        [td("Clockwise", True), td("N, NE, E, SE, S, SW, W, NW, back to N.")],
        [td("Anti-clockwise", True), td("The reverse of clockwise.")],
        [td("Right / left", True), td("Right = clockwise. Left = anti-clockwise. Decide from the centre.")],
        [td("Preceding", True), td("The one before in clockwise order, i.e. one step anti-clockwise.")],
        [td("Succeeding", True), td("The one after in clockwise order, i.e. one step clockwise.")],
        [td("From", True), td("Count the starting point as number 1.")],
        [td("Of", True), td("Leave the starting point out; start counting from the next position.")],
        [td("In front of + direction", True), td("The component sitting on that direction (in front of North = a3).")],
        [td("Opposite + direction", True), td("The component on the opposite direction (opposite of North = k5).")],
        [td("In front of + component", True), td("The component straight across the circle (in front of a3 = k5).")],
        [td("Opposite + component", True), td("The same as above (opposite of a3 = k5).")],
        [td("Inside the shape", True), td("Use only the corners of the shape you were told to join.")],
        [td("Vertex", True), td("The corner where the two equal sides of the triangle meet.")],
        [td("Perpendicular vertex", True), td("That corner also makes a 90 degree angle.")],
        [td("Alphabetical order", True), td("Sort the letters A to Z; ignore the digits; then give the value.")],
        [td("Exchange", True), td("Swap only the named part and nothing else.")],
    ]
    st.append(table(rows, [158, CONTENT_W - 158]))

    st.append(heading("Numbers to remember", 2))
    st.extend(B([
        "10 minutes, 20 questions, target 20 correct.",
        "Psycho test = 30 percent of the final result; CBT 2 = 70 percent.",
        "Around half of the candidates fail the psycho stage and leave the race immediately.",
        "A margin as small as 0.003 can change selection, so each question counts.",
    ]))
    st.append(heading("My practice log", 2))
    st.append(P("Photocopy this page or copy the table into a notebook. Fill one row after every "
                "Watch Table section you attempt. Watch the score go up and the time go down.", "body"))
    rows = [[th("Date"), th("Test / section"), th("Score out of 20"), th("Time taken"), th("One mistake to fix")]]
    for _ in range(6):
        rows.append([td(" "), td(" "), td(" "), td(" "), td(" ")])
    st.append(table(rows, [72, 130, 90, 78, CONTENT_W - 370]))
    st.append(Spacer(1, 6))
    st.append(info_box(
        "Last line",
        "Learn the rules once. Then practise. That is the whole method. "
        'Source lecture: <link href="%s" color="#1B4FA0"><u>youtu.be/lN-N6OE-tRA</u></link>.' % SOURCE_URL))

    return st


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main():
    if not os.path.exists(REF_PNG):
        raise SystemExit("Reference image missing: %s" % REF_PNG)

    doc = GuideDocTemplate(
        OUT_PDF,
        pagesize=A4,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T,
        bottomMargin=MARGIN_B,
        title="Watch Table Test (Clock Test) - ALP Psycho Test Study Guide",
        author="Simple English study guide",
        subject="ALP Psycho Test - Following Direction Test - Watch Table / Clock Test",
        keywords="ALP, psycho test, watch table test, clock test, RRB, RDSO, following direction test",
    )
    doc.multiBuild(build_story(), onFirstPage=cover_bg, onLaterPages=later)
    print("Wrote", OUT_PDF, os.path.getsize(OUT_PDF), "bytes")


if __name__ == "__main__":
    main()
