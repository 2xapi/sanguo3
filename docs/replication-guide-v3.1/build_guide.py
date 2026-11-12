#!/usr/bin/env python3
"""Build the editable guide from its Markdown source with python-docx."""
from pathlib import Path
import re
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

BASE = Path(__file__).resolve().parent
SOURCE = BASE / 'MD版三国志Ⅲ_独立网页游戏项目施工开发指南书_v3.1.md'


def font(style, size, bold=False, family='Heiti SC'):
    style.font.name = family
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = RGBColor(0, 0, 0)
    el = style.element.get_or_add_rPr()
    rf = el.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts'); el.insert(0, rf)
    for attribute in list(rf.attrib):
        if 'theme' in attribute.lower(): del rf.attrib[attribute]
    rf.set(qn('w:eastAsia'), 'Heiti SC')


def inline(paragraph, text):
    for token in re.split(r'(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^\)]+\))', text):
        if not token:
            continue
        link = re.fullmatch(r'\[([^\]]+)\]\(([^\)]+)\)', token)
        if link:
            run = paragraph.add_run(link[1] + ' (' + link[2] + ')')
        elif token.startswith('**'):
            run = paragraph.add_run(token[2:-2]); run.bold = True
        elif token.startswith('`'):
            run = paragraph.add_run(token[1:-1]); run.font.name = 'Consolas'; run.font.size = Pt(9)
        else:
            run = paragraph.add_run(token)
        run.font.color.rgb = RGBColor(0, 0, 0)


def table(doc, rows):
    count = len(rows[0]); tbl = doc.add_table(rows=1, cols=count)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    weights = []
    for col in range(count):
        lengths = [len(row[col]) for row in rows if col < len(row)]
        weights.append(max(7, min(32, sorted(lengths)[len(lengths) // 2])))
    widths = [170 * w / sum(weights) for w in weights]
    for c, w in zip(tbl.columns, widths): c.width = Mm(w)
    for ri, row in enumerate(rows):
        cells = tbl.rows[0].cells if ri == 0 else tbl.add_row().cells
        trpr = tbl.rows[ri]._tr.get_or_add_trPr()
        no_split = OxmlElement('w:cantSplit'); trpr.append(no_split)
        if ri == 0:
            repeat = OxmlElement('w:tblHeader'); trpr.append(repeat)
        for ci, cell in enumerate(cells):
            cell.width = Mm(widths[ci]); cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pr = cell._tc.get_or_add_tcPr()
            borders = OxmlElement('w:tcBorders')
            for side in ['top', 'left', 'bottom', 'right']:
                edge = OxmlElement('w:' + side); edge.set(qn('w:val'), 'single'); edge.set(qn('w:sz'), '4'); edge.set(qn('w:color'), 'D9D9D9'); borders.append(edge)
            pr.append(borders)
            margins = OxmlElement('w:tcMar')
            for side in ['top', 'left', 'bottom', 'right']:
                margin = OxmlElement('w:' + side); margin.set(qn('w:w'), '90'); margin.set(qn('w:type'), 'dxa'); margins.append(margin)
            pr.append(margins)
            if ri == 0:
                shade = OxmlElement('w:shd'); shade.set(qn('w:fill'), 'E7EDF4'); pr.append(shade)
            para = cell.paragraphs[0]; para.style = doc.styles['Table Text']
            inline(para, row[ci] if ci < len(row) else '')
            if ri == 0:
                for run in para.runs: run.bold = True
            if all(len(r[ci]) < 12 for r in rows if ci < len(r)):
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def main():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.top_margin, sec.bottom_margin = Mm(19), Mm(22)
    sec.left_margin = sec.right_margin = Mm(20)
    sec.header_distance = sec.footer_distance = Mm(8)
    styles = doc.styles
    font(styles['Normal'], 10.5)
    styles['Normal'].paragraph_format.line_spacing = 1.22
    styles['Normal'].paragraph_format.space_after = Pt(5)
    font(styles['Title'], 20, True)
    styles['Title'].paragraph_format.space_after = Pt(14)
    for border in list(styles['Title'].element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
    for level, size in [(1, 14), (2, 11.5), (3, 10.5)]:
        style = styles['Heading ' + str(level)]; font(style, size, True)
        pf = style.paragraph_format; pf.space_before = Pt(12); pf.space_after = Pt(5); pf.keep_with_next = True
    for name in ['Table Text', 'Code Text']:
        if name not in styles: styles.add_style(name, 1)
    font(styles['Table Text'], 9)
    styles['Table Text'].paragraph_format.line_spacing = 1.15
    styles['Table Text'].paragraph_format.space_after = Pt(2)
    font(styles['Code Text'], 8, family='Consolas')
    styles['Code Text'].paragraph_format.line_spacing = 1.05
    styles['Code Text'].paragraph_format.space_after = Pt(1)
    for name in ['List Bullet', 'List Number']:
        font(styles[name], 10.5); styles[name].paragraph_format.space_after = Pt(3)
    header = sec.header.paragraphs[0]
    header.text = '三国志Ⅲ独立网页重写  项目施工开发指南  v3.1'
    for run in header.runs: run.font.size = Pt(8); run.font.color.rgb = RGBColor(0, 0, 0)
    footer = sec.footer.paragraphs[0]; footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run('v3.1  ·  ')
    field = OxmlElement('w:fldSimple'); field.set(qn('w:instr'), 'PAGE'); footer._p.append(field)
    lines, i, code = SOURCE.read_text().splitlines(), 0, False
    while i < len(lines):
        line = lines[i]
        if line.startswith('```'):
            code = not code; i += 1; continue
        if code:
            doc.add_paragraph(line or ' ', 'Code Text'); i += 1; continue
        if not line.strip(): i += 1; continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', c) for c in cells): rows.append(cells)
                i += 1
            table(doc, rows); continue
        m = re.match(r'^(#{1,4})\s+(.+)', line)
        if m:
            level, value = len(m[1]), m[2]
            value = re.sub(r'[、，：／与\s]+', lambda x: ' ' if x[0] != '与' else x[0], value) if level == 1 else value
            if level == 1:
                doc.add_paragraph(value.replace('独立网页', '\n独立网页', 1), 'Title')
            else:
                doc.add_heading(value, level=level-1)
            i += 1; continue
        if re.match(r'^[-*] ', line):
            para = doc.add_paragraph(style='List Bullet'); inline(para, line[2:])
        else:
            para = doc.add_paragraph(); inline(para, line)
        i += 1
    doc.core_properties.title = 'MD版三国志Ⅲ独立网页游戏项目施工开发指南书'
    doc.core_properties.subject = '原版取证 范围冻结 开发验收 发布和恢复'
    doc.core_properties.author = 'Codex'
    doc.core_properties.comments = '工程规范与工具；非原版游戏验收报告。'
    output = SOURCE.with_suffix('.docx'); doc.save(output)
    print(output)


if __name__ == '__main__':
    main()
