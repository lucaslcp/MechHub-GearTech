"""Serviço compartilhado de Relatórios em PDF (ReportLab).

Uso:
    rep = PdfReport("Título", subtitle="GearTech", author="Fulano")
    rep.heading("Seção")
    rep.paragraph("Texto")
    rep.table([["A", "B"], [1, 2]])
    rep.bar_chart(["x", "y"], {"Série": [1, 2]}, "Título do gráfico")
    pdf_bytes = rep.build()
"""
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor("#1f4e79")
ORANGE = colors.HexColor("#e07a1f")
SERIES_COLORS = [NAVY, ORANGE, colors.HexColor("#2a9d8f"), colors.HexColor("#8e5ea2"),
                 colors.HexColor("#c0392b"), colors.HexColor("#6c757d")]

# As fontes padrão do PDF (Helvetica) não têm letras gregas nem setas.
_REPLACEMENTS = {"η": "eta", "→": "->", "≤": "<=", "≥": ">=", "τ": "tau", "β": "beta",
                 "α": "alfa", "π": "pi", "Δ": "delta", "ω": "omega", "Π": "prod", "Σ": "soma",
                 "✓": "OK", "⚠": "!", "–": "-", "—": "-"}


def _wrap(text: str, width: int = 24) -> str:
    words, lines, line = safe_text(text).split(), [], ""
    for word in words:
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    return "\n".join(lines[:3])


def _axis_number(value) -> str:
    text = f"{value:,.2f}".rstrip("0").rstrip(".")
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def safe_text(value) -> str:
    text = "" if value is None else str(value)
    for src, dst in _REPLACEMENTS.items():
        text = text.replace(src, dst)
    return text


class PdfReport:
    def __init__(self, title: str, subtitle: str = "", author: str = ""):
        self.title = safe_text(title)
        self.subtitle = safe_text(subtitle)
        self.author = safe_text(author)
        self.story = []
        base = getSampleStyleSheet()
        self.styles = {
            "title": ParagraphStyle("t", parent=base["Title"], alignment=TA_LEFT, textColor=NAVY,
                                    fontSize=19, spaceAfter=4),
            "subtitle": ParagraphStyle("s", parent=base["Normal"], textColor=colors.HexColor("#5b6675"),
                                       fontSize=10, spaceAfter=14),
            "h2": ParagraphStyle("h2", parent=base["Heading2"], textColor=NAVY, fontSize=13,
                                 spaceBefore=12, spaceAfter=6),
            "body": ParagraphStyle("b", parent=base["Normal"], fontSize=9.5, leading=13),
            "small": ParagraphStyle("sm", parent=base["Normal"], fontSize=8, leading=10,
                                    textColor=colors.HexColor("#5b6675")),
            "warn": ParagraphStyle("w", parent=base["Normal"], fontSize=9, leading=12,
                                   textColor=colors.HexColor("#8a4b00")),
        }
        self.story.append(Paragraph(escape(self.title), self.styles["title"]))
        meta = f"{self.subtitle}  ·  Gerado em {datetime.now():%d/%m/%Y %H:%M}"
        if self.author:
            meta += f"  ·  {self.author}"
        self.story.append(Paragraph(escape(meta), self.styles["subtitle"]))

    def heading(self, text: str):
        self.story.append(Paragraph(escape(safe_text(text)), self.styles["h2"]))

    def paragraph(self, text: str, style: str = "body"):
        self.story.append(Paragraph(escape(safe_text(text)), self.styles[style]))

    def spacer(self, height_cm: float = 0.3):
        self.story.append(Spacer(1, height_cm * cm))

    def table(self, rows: list[list], col_widths: list[float] | None = None, header: bool = True):
        data = [[Paragraph(escape(safe_text(c)), self.styles["small" if i else "body"]) if isinstance(c, str)
                 else safe_text(c) for c in row] for i, row in enumerate(rows)]
        widths = [w * cm for w in col_widths] if col_widths else None
        tbl = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
        style = [
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d2dc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6f9")]),
        ]
        if header:
            style += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
            data[0] = [Paragraph(f'<font color="white"><b>{escape(safe_text(c))}</b></font>', self.styles["small"])
                       for c in rows[0]]
            tbl = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
        tbl.setStyle(TableStyle(style))
        self.story.append(tbl)

    def _legend(self, drawing: Drawing, names: list[str], x: float, y: float):
        if len(names) < 2:
            return
        legend = Legend()
        legend.x, legend.y = x, y
        legend.fontSize = 7
        legend.alignment = "right"
        legend.columnMaximum = 1
        legend.deltax = 90
        legend.colorNamePairs = [(SERIES_COLORS[i % len(SERIES_COLORS)], safe_text(n)) for i, n in enumerate(names)]
        drawing.add(legend)

    def bar_chart(self, categories: list[str], series: dict[str, list[float]], title: str, y_label: str = ""):
        drawing = Drawing(17 * cm, 6.8 * cm)
        drawing.add(String(0, 6.4 * cm, safe_text(title), fontSize=10, fillColor=NAVY, fontName="Helvetica-Bold"))
        chart = VerticalBarChart()
        chart.x, chart.y = 1.4 * cm, 1.3 * cm
        chart.width, chart.height = 15 * cm, 4.4 * cm
        chart.data = [list(map(float, v)) for v in series.values()]
        chart.categoryAxis.categoryNames = [_wrap(c) for c in categories]
        chart.categoryAxis.labels.fontSize = 7
        chart.categoryAxis.labels.dy = -2
        chart.valueAxis.valueMin = 0
        chart.valueAxis.labels.fontSize = 7
        chart.valueAxis.labelTextFormat = _axis_number
        chart.barSpacing = 1
        chart.groupSpacing = 8
        for i in range(len(chart.data)):
            chart.bars[i].fillColor = SERIES_COLORS[i % len(SERIES_COLORS)]
            chart.bars[i].strokeColor = None
        drawing.add(chart)
        if y_label:
            drawing.add(String(0, 5.9 * cm, safe_text(y_label), fontSize=7, fillColor=colors.HexColor("#5b6675")))
        self._legend(drawing, list(series.keys()), 17 * cm, 6.5 * cm)
        self.story.append(KeepTogether([drawing, Spacer(1, 0.2 * cm)]))

    def line_chart(self, categories: list[str], series: dict[str, list[float]], title: str, y_label: str = ""):
        drawing = Drawing(17 * cm, 6.8 * cm)
        drawing.add(String(0, 6.4 * cm, safe_text(title), fontSize=10, fillColor=NAVY, fontName="Helvetica-Bold"))
        chart = HorizontalLineChart()
        chart.x, chart.y = 1.4 * cm, 1.3 * cm
        chart.width, chart.height = 15 * cm, 4.4 * cm
        chart.data = [list(map(float, v)) for v in series.values()]
        step = max(1, len(categories) // 8)
        chart.categoryAxis.categoryNames = [safe_text(c) if i % step == 0 else "" for i, c in enumerate(categories)]
        chart.categoryAxis.labels.fontSize = 7
        chart.valueAxis.labels.fontSize = 7
        chart.valueAxis.valueMin = 0
        chart.valueAxis.labelTextFormat = _axis_number
        for i in range(len(chart.data)):
            chart.lines[i].strokeColor = SERIES_COLORS[i % len(SERIES_COLORS)]
            chart.lines[i].strokeWidth = 1.6
        drawing.add(chart)
        if y_label:
            drawing.add(String(0, 5.9 * cm, safe_text(y_label), fontSize=7, fillColor=colors.HexColor("#5b6675")))
        self._legend(drawing, list(series.keys()), 17 * cm, 6.5 * cm)
        self.story.append(KeepTogether([drawing, Spacer(1, 0.2 * cm)]))

    def _footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#5b6675"))
        canvas.drawString(2 * cm, 1.2 * cm, "MechHub · Plataforma integrada de Engenharia Mecânica")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
        canvas.setStrokeColor(ORANGE)
        canvas.setLineWidth(2)
        canvas.line(2 * cm, A4[1] - 1.3 * cm, A4[0] - 2 * cm, A4[1] - 1.3 * cm)
        canvas.restoreState()

    def build(self) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                                topMargin=1.8 * cm, bottomMargin=1.8 * cm, title=self.title,
                                author=self.author or "MechHub")
        doc.build(self.story, onFirstPage=self._footer, onLaterPages=self._footer)
        return buffer.getvalue()
