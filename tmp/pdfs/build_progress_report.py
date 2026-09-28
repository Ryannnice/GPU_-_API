from collections import Counter
from pathlib import Path
import json
import sys

sys.path.insert(0, r'C:/Users/renyv/AppData/Local/codex-pdf-deps')

from fontTools.ttLib import TTFont as FontToolsFont
from pypdf import PdfReader
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'output/pdf/clbench_progress_1943_onepage.pdf'
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
TMP = ROOT / 'tmp/pdfs'
FONT_REGULAR = 'C:/Windows/Fonts/msyh.ttc'
FONT_BOLD = 'C:/Windows/Fonts/msyhbd.ttc'
pdfmetrics.registerFont(TTFont('YaHei', FONT_REGULAR, subfontIndex=0))
pdfmetrics.registerFont(TTFont('YaHeiBold', FONT_BOLD, subfontIndex=0))

W, H = landscape(A3)
M = 34
CW = W - 2 * M
COLORS = {
    'ink': '#172B43',
    'muted': '#607185',
    'line': '#DCE4EC',
    'pale': '#F3F6FA',
    'complete': '#0A7B65',
    'complete_bg': '#E7F4EF',
    'first': '#996007',
    'first_bg': '#FFF3D9',
    'running': '#225FA9',
    'running_bg': '#EAF2FD',
    'blocked': '#687485',
    'blocked_bg': '#EEF1F5',
    'queued': '#708396',
    'queued_bg': '#F3F6F9',
}


def cell(state, detail=''):
    return {'state': state, 'detail': detail}


C = lambda: cell('complete')
D = lambda: cell('blocked')
Q = lambda: cell('queued')
F = lambda: cell('first', '1/5+B')
R = lambda detail: cell('running', detail)

rows = [
    ('ACE / Sol', [C(), C(), C(), C(), R('5/5；B 43/120'), C()], 5),
    ('Claude / Sol', [D(), D(), D(), D(), D(), D()], 0),
    ('Codex / Sol', [C(), D(), D(), D(), D(), D()], 1),
    ('Mem0 / Sol', [C(), C(), C(), C(), C(), C()], 6),
    ('ICL / GPT-5.5', [C(), D(), F(), D(), R('1/5；B 74/120'), D()], 1),
    ('ICL / Luna', [C(), D(), F(), D(), Q(), D()], 1),
    ('ICL / Sol', [C(), C(), C(), C(), C(), C()], 6),
    ('ICL / Terra', [C(), D(), F(), D(), Q(), D()], 1),
    ('ICL / Astra', [C(), D(), R('1/5；B 9/20'), D(), Q(), D()], 1),
    ('ICL-Notepad / Luna', [C(), D(), R('第1轮 13/20'), D(), Q(), D()], 1),
    ('ICL-Notepad / Sol', [C(), C(), C(), C(), C(), C()], 6),
    ('ICL-Notepad / Astra', [Q(), D(), Q(), D(), Q(), D()], 0),
]

datasets = [
    ('Blind Spectrum Monitoring', 90, 540, 10, '最接近完成的数据集'),
    ('Codebase Adaptation', 19, 114, 4, '其余均受 Docker/WSL 影响'),
    ('Cohort Studies', 20, 120, 4, '3 个首轮完成，2 个运行中'),
    ('Database Exploration', 40, 240, 4, '其余均受 Docker/WSL 影响'),
    ('Exploitable Poker', 120, 720, 3, '两条 baseline 正在并行'),
    ('Sales Prediction', 12, 72, 4, '其余均受 Docker/WSL 影响'),
]

statuses = [
    ('complete', '完整', 29, ['5/5 轮 + baseline 完成']),
    ('first', '首轮完成', 3, ['1 轮 + baseline 完成', '待补第 2-5 轮']),
    ('running', '运行中', 4, ['正在产生正式结果']),
    ('blocked', 'Docker 阻塞', 29, ['等待 Docker/WSL 恢复']),
    ('queued', '已排队', 7, ['API-only', '可在当前队列继续运行']),
]

running = [
    ('Sol + ACE + Poker', 'baseline', 43, 120),
    ('Astra + ICL + Cohort', 'baseline', 9, 20),
    ('Luna + ICL-Notepad + Cohort', '第 1 轮', 13, 20),
    ('GPT-5.5 + ICL + Poker', 'baseline', 74, 120),
]

counts = Counter(item['state'] for _, cells, _ in rows for item in cells)
assert counts == {state: n for state, _, n, _ in statuses}
assert sum(counts.values()) == 72
assert all(sum(x['state'] == 'complete' for x in cells) == n for _, cells, n in rows)
assert sum(n for name, _, n in rows if name.endswith('/ Sol')) == 24
assert sum(name.endswith('/ Sol') for name, _, _ in rows) * 6 == 36
column_counts = [sum(cells[i]['state'] == 'complete' for _, cells, _ in rows) for i in range(6)]
assert column_counts == [10, 4, 4, 4, 3, 4]
assert sum(column_counts) == 29
assert sum(ds[1] for ds in datasets) == 301
assert all(ds[2] == ds[1] * 6 for ds in datasets)
assert sum(ds[2] for ds in datasets) * 12 == 21672
assert f'{29 / 72 * 100:.1f}%' == '40.3%'

c = canvas.Canvas(str(OUTPUT), pagesize=(W, H), pageCompression=1)
c.setTitle('CLBench 正式实验进度 | 截至 19:43')
c.setSubject('72 条件完整矩阵、数据集与实验规模、当前四路运行进度')
c.setAuthor('CLBench')
drawn_text = []


def color(value):
    return HexColor(COLORS.get(value, value))


def rect(x, top, width, height, fill, radius=0, stroke=None):
    c.setFillColor(color(fill))
    c.setStrokeColor(color(stroke or fill))
    c.setLineWidth(0.6)
    if radius:
        c.roundRect(x, H - top - height, width, height, radius, fill=1, stroke=bool(stroke))
    else:
        c.rect(x, H - top - height, width, height, fill=1, stroke=bool(stroke))


def text(x, baseline, s, size=10.5, fill='ink', bold=False, align='left', max_width=None):
    font = 'YaHeiBold' if bold else 'YaHei'
    width = pdfmetrics.stringWidth(s, font, size)
    if max_width is not None:
        assert width <= max_width, (s, width, max_width)
    assert all(ch not in s for ch in ['\u2011', '\u2013', '\u2014'])
    left = x if align == 'left' else x - width if align == 'right' else x - width / 2
    assert left >= M - 2 and left + width <= W - M + 2, (s, left, width)
    assert 15 < baseline < H - 15
    c.setFillColor(color(fill))
    c.setFont(font, size)
    if align == 'right':
        c.drawRightString(x, H - baseline, s)
    elif align == 'center':
        c.drawCentredString(x, H - baseline, s)
    else:
        c.drawString(x, H - baseline, s)
    drawn_text.append((s, font))


def line(x1, top1, x2, top2, fill='line', width=0.6):
    c.setStrokeColor(color(fill))
    c.setLineWidth(width)
    c.line(x1, H - top1, x2, H - top2)


def icon(state, x, top, size=10):
    y = H - top
    c.saveState()
    c.setStrokeColor(color(state))
    c.setFillColor(color(state))
    c.setLineWidth(1.7)
    c.setLineCap(1)
    r = size / 2
    if state == 'complete':
        p = c.beginPath()
        p.moveTo(x - r * 0.85, y)
        p.lineTo(x - r * 0.2, y - r * 0.6)
        p.lineTo(x + r, y + r * 0.8)
        c.drawPath(p, stroke=1, fill=0)
    elif state == 'blocked':
        c.roundRect(x - r * 0.8, y - r, r * 0.48, size, 0.7, stroke=0, fill=1)
        c.roundRect(x + r * 0.3, y - r, r * 0.48, size, 0.7, stroke=0, fill=1)
    elif state == 'running':
        p = c.beginPath()
        p.moveTo(x - r * 0.6, y - r)
        p.lineTo(x + r, y)
        p.lineTo(x - r * 0.6, y + r)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
    elif state == 'queued':
        c.setLineWidth(1.25)
        c.circle(x, y, r * 0.9, stroke=1, fill=0)
    elif state == 'first':
        c.setLineWidth(1.1)
        c.circle(x, y, r, stroke=1, fill=0)
        c.setFont('YaHeiBold', size * 0.65)
        c.drawCentredString(x, y - size * 0.23, '1')
    c.restoreState()


# Header and primary metrics.
rect(M, 31, 4, 43, 'complete', radius=2)
text(M + 16, 55, 'CLBench 正式实验进度', size=25, bold=True)
text(M + 16, 79, '完整口径：5 轮有记忆实验 + 1 轮无记忆 baseline 全部完成', size=11, fill='muted')
text(W - M, 36, '截至 19:43', size=10, fill='muted', align='right')
text(W - M - 142, 65, '29 / 72', size=26, fill='complete', bold=True, align='right')
text(W - M, 65, '40.3%', size=26, fill='complete', bold=True, align='right')
text(W - M, 83, 'Sol 已完成 24/36', size=11, align='right')

# Five status cards also serve as the matrix legend.
card_top, card_h, gap = 101, 75, 10
card_w = (CW - 4 * gap) / 5
for i, (state, label, n, descriptions) in enumerate(statuses):
    x = M + i * (card_w + gap)
    rect(x, card_top, card_w, card_h, state + '_bg', radius=7)
    icon(state, x + 17, card_top + 21, 11)
    text(x + 31, card_top + 25, label, size=11, fill=state, bold=True)
    text(x + card_w - 15, card_top + 31, str(n), size=25, fill=state, bold=True, align='right')
    if len(descriptions) == 1:
        text(x + 15, card_top + 58, descriptions[0], size=9.8, fill='muted', max_width=card_w - 30)
    else:
        for j, description in enumerate(descriptions):
            text(x + 15, card_top + 51 + j * 14, description, size=9.6, fill='muted', max_width=card_w - 30)

# Full 72-condition matrix.
text(M, 201, '72 条件完整矩阵', size=14, bold=True)
text(W - M, 201, '12 组方法 / 模型 × 6 数据集；B = 无记忆 baseline；列下方为每轮实例数',
     size=9.8, fill='muted', align='right')
table_top, header_h, row_h, footer_h = 214, 39, 22, 26
widths = [180, 139, 139, 146, 141, 164, 139, CW - 1048]
xs = [M]
for width in widths:
    xs.append(xs[-1] + width)
rect(M, table_top, CW, header_h, 'ink', radius=4)
text(M + 13, table_top + 24, '方法 / 模型', size=11, fill='#FFFFFF', bold=True)
headers = [('频谱监测', 90), ('代码库适应', 19), ('队列研究', 20),
           ('数据库探索', 40), ('可利用扑克', 120), ('销售预测', 12)]
for j, (label, n) in enumerate(headers, 1):
    center = (xs[j] + xs[j + 1]) / 2
    text(center, table_top + 16, label, size=10.7, fill='#FFFFFF', bold=True, align='center')
    text(center, table_top + 31, f'{n} / 轮', size=9, fill='#C9D6E5', align='center')
text((xs[7] + xs[8]) / 2, table_top + 24, '完整数', size=10.5, fill='#FFFFFF', bold=True, align='center')

for i, (label, cells, n) in enumerate(rows):
    row_top = table_top + header_h + i * row_h
    rect(M, row_top, CW, row_h, '#FFFFFF' if i % 2 == 0 else '#F7F9FC')
    text(M + 13, row_top + 15, label, size=10.5, bold=label.endswith('/ Sol'), max_width=widths[0] - 26)
    for j, item in enumerate(cells, 1):
        center = (xs[j] + xs[j + 1]) / 2
        state = item['state']
        detail = item['detail']
        if state == 'complete':
            rect(center - 17, row_top + 3, 34, 16, 'complete_bg', radius=6)
            icon(state, center, row_top + 11, 8)
        elif state == 'blocked':
            icon(state, center, row_top + 11, 8)
        elif state == 'queued':
            icon(state, center, row_top + 11, 8)
        elif state == 'first':
            rect(center - 29, row_top + 3, 58, 16, 'first_bg', radius=5)
            text(center, row_top + 14.7, detail, size=9.6, fill=state, align='center')
        elif state == 'running':
            tw = pdfmetrics.stringWidth(detail, 'YaHei', 9.8)
            group_width = tw + 15
            left = center - group_width / 2
            rect(left - 7, row_top + 3, group_width + 14, 16, 'running_bg', radius=5)
            icon(state, left + 3, row_top + 11, 7)
            text(left + 15, row_top + 14.7, detail, size=9.8, fill=state, max_width=widths[j] - 30)
    text((xs[7] + xs[8]) / 2, row_top + 15, f'{n}/6', size=10.3,
         fill='complete' if n == 6 else 'ink', bold=True, align='center')
    line(M, row_top + row_h, W - M, row_top + row_h, width=0.35)

footer_top = table_top + header_h + 12 * row_h
rect(M, footer_top, CW, footer_h, '#EDF2F7')
text(M + 13, footer_top + 17, '完整数', size=10.5, bold=True)
for j, n in enumerate(column_counts, 1):
    text((xs[j] + xs[j + 1]) / 2, footer_top + 17, f'{n}/12', size=10.7, bold=True, align='center')
text((xs[7] + xs[8]) / 2, footer_top + 17, '29/72', size=10.7, fill='complete', bold=True, align='center')
for edge in xs[1:-1]:
    line(edge, table_top + header_h, edge, footer_top + footer_h, width=0.35)

# Dataset scales, with overall target explicitly distinguished in the total row.
dataset_w = 752
text(M, 568, '数据集与实验规模', size=14, bold=True)
text(M + dataset_w, 568, '单条件为 6 轮；总计为全部 72 条件的目标',
     size=9, fill='muted', align='right')
data_top, data_header, data_row, data_footer = 583, 26, 21, 26
dw = [211, 67, 108, 69, 297]
dx = [M]
for width in dw:
    dx.append(dx[-1] + width)
rect(M, data_top, dataset_w, data_header, '#EDF2F7', radius=4)
for j, label in enumerate(['数据集', '每轮实例', '单条件完整规模', '完整条件', '当前说明']):
    if j in [0, 4]:
        text(dx[j] + 10, data_top + 17, label, size=9.8, bold=True)
    else:
        text((dx[j] + dx[j + 1]) / 2, data_top + 17, label, size=9.4, bold=True, align='center')
for i, (name, per_round, full_scale, completed, note) in enumerate(datasets):
    top = data_top + data_header + i * data_row
    rect(M, top, dataset_w, data_row, '#FFFFFF' if i % 2 == 0 else '#F7F9FC')
    text(dx[0] + 10, top + 14.5, name, size=9.8, max_width=dw[0] - 20)
    for j, value in [(1, str(per_round)), (2, str(full_scale)), (3, f'{completed}/12')]:
        text((dx[j] + dx[j + 1]) / 2, top + 14.5, value, size=9.9, align='center')
    text(dx[4] + 10, top + 14.5, note, size=9.6, fill='muted', max_width=dw[4] - 20)
    line(M, top + data_row, M + dataset_w, top + data_row, width=0.35)
data_footer_top = data_top + data_header + 6 * data_row
rect(M, data_footer_top, dataset_w, data_footer, '#EDF2F7')
text(dx[0] + 10, data_footer_top + 17, '总计', size=10, bold=True)
text((dx[1] + dx[2]) / 2, data_footer_top + 17, '301/轮', size=10, bold=True, align='center')
text((dx[2] + dx[3]) / 2, data_footer_top + 17, '21,672 个实例', size=9.4, bold=True, align='center')
text((dx[3] + dx[4]) / 2, data_footer_top + 17, '29/72', size=10, fill='complete', bold=True, align='center')
text(dx[4] + 10, data_footer_top + 17, '全量目标，含全部 5 轮和 baseline', size=9.4, fill='muted')

# Four active work streams.
rx, rw = M + dataset_w + 22, CW - dataset_w - 22
text(rx, 568, '当前四路运行', size=14, bold=True)
for i, (label, stage, current, total) in enumerate(running):
    top = 583 + i * 46
    rect(rx, top, rw, 41, '#F3F6FA', radius=5)
    icon('running', rx + 12, top + 14, 7)
    text(rx + 23, top + 18, label, size=9.6, bold=True, max_width=rw - 115)
    text(rx + rw - 12, top + 18, f'{current}/{total}', size=11.2, fill='running', bold=True, align='right')
    text(rx + 12, top + 33, stage, size=9, fill='muted')
    bar_x = rx + 73
    bar_w = rw - 85
    rect(bar_x, top + 28, bar_w, 4, '#DCE5EF', radius=2)
    rect(bar_x, top + 28, bar_w * current / total, 4, 'running', radius=2)

# Closing progress note, copied from the supplied snapshot.
line(M, 782, W - M, 782)
text(M, 806, '今日已完成阶段累计 906 个有效实例。', size=10.8, bold=True)
text(M + 277, 806, '下一批最可能完成：Astra Cohort 首轮条件、Luna-Notepad Cohort rollout。',
     size=10.5, fill='muted', max_width=CW - 277)

# Require every character to exist in its embedded font before saving.
font_maps = {
    'YaHei': FontToolsFont(FONT_REGULAR, fontNumber=0).getBestCmap(),
    'YaHeiBold': FontToolsFont(FONT_BOLD, fontNumber=0).getBestCmap(),
}
missing = sorted({ch for s, font in drawn_text for ch in s if ord(ch) not in font_maps[font]})
assert not missing, f'Unsupported glyphs: {missing}'
c.showPage()
c.save()

reader = PdfReader(OUTPUT)
assert len(reader.pages) == 1
extracted = reader.pages[0].extract_text()
required_strings = [
    '19:43', '29 / 72', '40.3%', 'Sol 已完成 24/36',
    '72 条件完整矩阵', '5 轮有记忆实验', '无记忆 baseline',
    '43/120', '74/120', '9/20', '13/20', '906', '21,672', '301/轮',
    'Astra Cohort 首轮条件', 'Luna-Notepad Cohort rollout',
] + [name for name, _, _ in rows] + [ds[0] for ds in datasets]
for required in required_strings:
    assert required in extracted, required
assert '\ufffd' not in extracted
report = {
    'file': str(OUTPUT),
    'pages': len(reader.pages),
    'page_format': 'A3 landscape',
    'page_size_points': [round(W, 2), round(H, 2)],
    'conditions_by_status': dict(counts),
    'column_completion_counts': column_counts,
    'sol_complete': '24/36',
    'total_target_instances': 21672,
    'required_texts_verified': len(required_strings),
    'missing_glyphs': missing,
}
(TMP / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
(TMP / 'extracted_text.txt').write_text(extracted, encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
