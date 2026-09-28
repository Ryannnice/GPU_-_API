from pathlib import Path
from collections import Counter
import sys

sys.path.insert(0, r'C:/Users/renyv/AppData/Local/codex-pdf-deps')

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'output/pdf/clbench_progress_1943_onepage.pdf'
pdfmetrics.registerFont(TTFont('CN', 'C:/Windows/Fonts/msyh.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('CNBold', 'C:/Windows/Fonts/msyhbd.ttc', subfontIndex=0))
W, H = landscape(A3)
M = 28
CW = W - 2 * M
c = canvas.Canvas(str(OUTPUT), pagesize=(W, H), pageCompression=1)
c.setTitle('CLBench 实验进度（截至 19:43）')
c.setSubject('单页黑白表格')
c.setAuthor('CLBench')
all_strings = []


def text(x, baseline, value, size=10.5, bold=False, align='left'):
    font = 'CNBold' if bold else 'CN'
    width = pdfmetrics.stringWidth(value, font, size)
    start = x - width if align == 'right' else x
    assert start >= M - 0.5 and start + width <= W - M + 0.5, value
    c.setFont(font, size)
    c.setFillColor(colors.black)
    if align == 'right':
        c.drawRightString(x, H - baseline, value)
    else:
        c.drawString(x, H - baseline, value)
    all_strings.append(value)


def table(data, top, widths, header_height, row_height, footer_height=None,
          left_columns=(0,), font_size=10):
    heights = [header_height] + [row_height] * (len(data) - 1)
    if footer_height is not None:
        heights[-1] = footer_height
    style = [
        ('FONTNAME', (0, 0), (-1, -1), 'CN'),
        ('FONTSIZE', (0, 0), (-1, -1), font_size),
        ('LEADING', (0, 0), (-1, -1), font_size + 2),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('FONTNAME', (0, 0), (-1, 0), 'CNBold'),
    ]
    for col in left_columns:
        style.append(('ALIGN', (col, 0), (col, -1), 'LEFT'))
    if footer_height is not None:
        style.append(('FONTNAME', (0, -1), (-1, -1), 'CNBold'))
    for i, row in enumerate(data):
        for j, val in enumerate(row):
            val = str(val)
            font = 'CNBold' if i == 0 or (footer_height is not None and i == len(data) - 1) else 'CN'
            assert pdfmetrics.stringWidth(val, font, font_size) <= widths[j] - 12, (val, widths[j])
            all_strings.append(val)
    t = Table(data, colWidths=widths, rowHeights=heights)
    t.setStyle(TableStyle(style))
    width, height = t.wrap(CW, H)
    assert abs(width - CW) < 0.01
    assert top + height < H - M
    t.drawOn(c, M, H - top - height)
    return top + height


text(M, 38, 'CLBench 实验进度（截至 19:43）', 16, True)
text(M, 60, '截至 19:43，正式完整条件为 29/72（40.3%）；Sol 已完成 24/36。', 11)
text(M, 78, '“完整”要求 5 轮有记忆实验 + 1 轮无记忆 baseline 全部完成。', 10.5)

text(M, 99, '状态汇总', 11.5, True)
status_data = [
    ['状态', '条件数', '含义'],
    ['完整', '29', '5/5 轮 + baseline 完成'],
    ['首轮完成', '3', '1 轮 + baseline 完成，待补第 2-5 轮'],
    ['运行中', '4', '正在产生正式结果'],
    ['Docker 阻塞', '29', '等待 Docker/WSL 恢复'],
    ['已排队', '7', 'API-only，可在当前队列继续运行'],
    ['合计', '72', '-'],
]
table(status_data, 108, [190, 120, CW - 310], 20, 18, 18, (0, 2), 10.3)

text(M, 256, '72 条件完整矩阵', 11.5, True)
text(W - M, 256, 'B = 无记忆 baseline；阻塞 = Docker/WSL 阻塞；列标题数字为每轮实例数。', 9.7, align='right')
C, D, Q, F = '完整', '阻塞', '已排队', '首轮 1/5+B'
matrix_rows = [
    ['ACE / Sol', C, C, C, C, '运行中 5/5；B 43/120', C, '5/6'],
    ['Claude / Sol', D, D, D, D, D, D, '0/6'],
    ['Codex / Sol', C, D, D, D, D, D, '1/6'],
    ['Mem0 / Sol', C, C, C, C, C, C, '6/6'],
    ['ICL / GPT-5.5', C, D, F, D, '运行中 1/5；B 74/120', D, '1/6'],
    ['ICL / Luna', C, D, F, D, Q, D, '1/6'],
    ['ICL / Sol', C, C, C, C, C, C, '6/6'],
    ['ICL / Terra', C, D, F, D, Q, D, '1/6'],
    ['ICL / Astra', C, D, '运行中 1/5；B 9/20', D, Q, D, '1/6'],
    ['ICL-Notepad / Luna', C, D, '运行中 第1轮 13/20', D, Q, D, '1/6'],
    ['ICL-Notepad / Sol', C, C, C, C, C, C, '6/6'],
    ['ICL-Notepad / Astra', Q, D, Q, D, Q, D, '0/6'],
]
states = Counter('运行中' if val.startswith('运行中') else val for row in matrix_rows for val in row[1:7])
assert states == {C: 29, D: 29, Q: 7, F: 3, '运行中': 4}
assert all(sum(val == C for val in row[1:7]) == int(row[-1][0]) for row in matrix_rows)
assert sum(int(row[-1][0]) for row in matrix_rows if row[0].endswith('/ Sol')) == 24
assert [sum(row[j] == C for row in matrix_rows) for j in range(1, 7)] == [10, 4, 4, 4, 3, 4]
matrix_data = [
    ['方法 / 模型', '频谱监测 90', '代码库适应 19', '队列研究 20', '数据库探索 40', '可利用扑克 120', '销售预测 12', '完整数'],
] + matrix_rows + [
    ['完整数', '10/12', '4/12', '4/12', '4/12', '3/12', '4/12', '29/72'],
]
table(matrix_data, 266, [179, 136, 137, 150, 137, 169, 135, CW - 1043], 24, 18, 20, (0,), 9.8)

text(M, 549, '数据集与实验规模', 11.5, True)
text(W - M, 549, '单条件完整规模含 5 轮有记忆实验和 baseline；总计为全部 72 条件的目标。', 9.7, align='right')
dataset_data = [
    ['数据集', '每轮实例', '单条件完整规模', '完整条件', '当前说明'],
    ['Blind Spectrum Monitoring', '90', '540', '10/12', '最接近完成的数据集'],
    ['Codebase Adaptation', '19', '114', '4/12', '其余均受 Docker/WSL 影响'],
    ['Cohort Studies', '20', '120', '4/12', '3 个首轮完成，2 个运行中'],
    ['Database Exploration', '40', '240', '4/12', '其余均受 Docker/WSL 影响'],
    ['Exploitable Poker', '120', '720', '3/12', '两条 baseline 正在并行'],
    ['Sales Prediction', '12', '72', '4/12', '其余均受 Docker/WSL 影响'],
    ['总计', '301/轮', '21,672 个实例', '29/72', '全量目标，含全部 5 轮和 baseline'],
]
assert sum(int(row[1]) for row in dataset_data[1:-1]) == 301
assert sum(int(row[2]) for row in dataset_data[1:-1]) * 12 == 21672
table(dataset_data, 559, [270, 115, 175, 115, CW - 675], 22, 18, 20, (0, 4), 10)

text(M, 730, '当前四路仍在运行：', 11.5, True)
for i, val in enumerate([
    'Sol + ACE + Poker baseline：43/120',
    'Astra + ICL + Cohort baseline：9/20',
    'Luna + ICL-Notepad + Cohort 第 1 轮：13/20',
    'GPT-5.5 + ICL + Poker baseline：74/120',
]):
    text(M, 748 + i * 14, '- ' + val, 10.3)
text(M, 814, '今日已完成阶段累计 906 个有效实例。下一批最可能完成的是 Astra Cohort 首轮条件和 Luna-Notepad Cohort rollout。', 10.3)

c.showPage()
c.save()
reader = PdfReader(OUTPUT)
assert len(reader.pages) == 1
extracted = reader.pages[0].extract_text()
for val in all_strings:
    assert val in extracted, val
assert '\ufffd' not in extracted
# All color-setting commands must use neutral grayscale values.
content = reader.pages[0].get_contents().get_data().decode('latin1')
import re
for a, b, d in re.findall(r'([.0-9]+) ([.0-9]+) ([.0-9]+) [rR][gG]', content):
    assert float(a) == float(b) == float(d), (a, b, d)
print(f'Plain PDF ready: {OUTPUT}; pages=1; required text checks={len(all_strings)}; colors=black/white')
