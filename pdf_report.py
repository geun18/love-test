from io import BytesIO
from math import cos, sin, pi
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    PageBreak,
    KeepTogether,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Polygon, Line, Circle
from reportlab.graphics import renderSVG


# 각 문항은 한 주제에만 사용합니다. 검증된 하위척도가 아닙니다.
TOPICS = [
    ("연락과 확인", (1, 5, 7, 19), "연락이나 표현이 달라졌을 때 관계의 변화를 의심하거나 확인하려는 반응",
     "메시지를 다시 보기 전에, 실제로 달라진 점과 내가 추측한 점을 한 줄씩 적어보세요.",
     "오늘은 평소보다 연락이 뜸해서 조금 걱정됐어. 통화하기 편한 시간이 있을까?"),
    ("관계 안정감", (3, 9, 11, 21), "상대의 애정이 유지되는지 걱정하거나 갈등을 관계의 위협으로 느끼는 반응",
     "갈등의 주제와 관계에 대한 걱정을 나눠 적고, 오늘 이야기할 주제 하나만 정해보세요.",
     "우리 사이 전체를 판단하기보다, 아까 의견이 달랐던 부분부터 이야기하고 싶어."),
    ("독립과 자기표현", (15, 17, 22, 23), "서로의 독립성을 받아들이거나 자신의 필요와 경계를 지키는 데 느끼는 어려움",
     "부담이 작은 상황에서 원하는 것 한 가지를 말하고, 상대의 실제 반응을 기록해 보세요.",
     "나는 오늘 혼자 쉬는 시간이 필요해. 내일 저녁에 만나는 건 어때?"),
    ("감정 공유", (2, 8, 10, 20), "개인적인 감정이나 고민을 이야기할 때 느끼는 불편",
     "안전하다고 느끼는 상대와 작은 감정 한 가지를 나누고, 어떤 반응이 도움이 됐는지 살펴보세요.",
     "오늘 조금 지쳤어. 해결책보다 잠깐 들어주면 좋겠어."),
    ("도움과 의지", (4, 12, 16, 24), "상대에게 도움을 요청하거나 서로 의지할 때 느끼는 부담",
     "부탁할 일의 범위를 작게 정하고, 상대가 선택할 수 있게 제안해 보세요.",
     "괜찮다면 이 문제에 대해 10분만 같이 생각해 줄 수 있어?"),
    ("갈등과 거리", (6, 13, 14, 18), "긴장하거나 가까워지는 상황에서 관계 확인이 급해지거나 거리를 두려는 반응",
     "대화를 계속하기 어렵다면 잠시 쉬고, 다시 이야기할 시간을 함께 정해 보세요.",
     "지금은 정리할 시간이 필요해. 오늘 저녁에 이 이야기를 이어갈 수 있을까?"),
]
REVERSED = {3, 4, 9, 10, 15, 16, 21, 22}
RADAR_NOTE = ("바깥쪽일수록 해당 주제에서 걱정이나 부담을 더 많이 보고했다는 뜻입니다. "
              "네 유형 비중과 별개인 문항 묶음이며, 검증된 하위척도가 아닙니다.")


def analyze_topics(result, questions):
    answers = result["answers"]
    rows = []
    for label, items, meaning, practice, example in TOPICS:
        values = [(n, answers[n], 6 - answers[n] if n in REVERSED else answers[n])
                  for n in items if answers.get(n) is not None]
        score = (sum(v for _, _, v in values) / len(values) - 1) * 25 if len(values) >= 3 else None
        evidence = [
            (n, f"{n}번 (선택 {raw}/5{', 역채점 문항' if n in REVERSED else ''}): {questions[n - 1]}", adjusted)
            for n, raw, adjusted in values
        ]
        rows.append(dict(label=label, score=score, count=len(values), meaning=meaning,
                         practice=practice, example=example, evidence=evidence))
    return rows


def reflection(rows):
    valid = [row for row in rows if row["score"] is not None]
    focus = max(valid, key=lambda row: row["score"], default=None)
    strength = min(valid, key=lambda row: row["score"], default=None)
    if focus and focus["score"] >= 62.5:
        yield "먼저 살펴볼 반응", (f"이번 응답에서 ‘{focus['label']}’은 점수가 높은 주제에 해당합니다. "
                                    f"{focus['meaning']}이 실제로 언제 나타나는지 한 장면을 떠올려 보세요.")
    else:
        yield "먼저 살펴볼 반응", "높게 응답한 주제가 뚜렷하지 않습니다. 최근에 불편했던 장면이 있다면 당시 상황과 자신의 반응을 나눠 살펴보세요."
    if strength and strength["score"] <= 37.5:
        yield "유지할 만한 강점", (f"‘{strength['label']}’에서는 걱정이나 부담이 비교적 적게 나타났습니다. "
                                    "이미 편안하게 대응했던 장면과 그때 도움이 된 행동을 떠올려 보세요.")
    else:
        yield "유지할 만한 강점", "이 결과만으로 뚜렷한 강점을 고르기 어렵습니다. 불편한 상황에서도 지켜낸 경계나 솔직하게 말한 경험을 찾아보세요."
    if focus and focus["score"] >= 62.5:
        yield "이번 주 연습", focus["practice"]
        yield "대화 예시", focus["example"]
    else:
        yield "이번 주 연습", "실제로 있었던 일, 그때 든 생각, 내가 한 행동을 각각 한 줄씩 적어보세요."
    yield "4주 뒤 점검", "같은 관계에서 비슷한 상황이 생겼을 때 어떤 행동을 시도했고 무엇이 달랐는지 비교해 보세요. 점수의 변화보다 구체적인 행동을 살펴보세요."


def radar(rows, font="Korean"):
    chart = Drawing(490, 290)
    chart.hAlign = "CENTER"

    def point(i, fraction):
        angle = pi / 2 - i * pi / 3
        return 245 + 96 * fraction * cos(angle), 144 + 96 * fraction * sin(angle)

    def polygon(fractions):
        return [xy for i, f in enumerate(fractions) for xy in point(i, f)]

    for step in (0.25, 0.5, 0.75, 1):
        chart.add(Polygon(polygon([step] * 6), fillColor=None,
                          strokeColor=colors.HexColor("#CBD5E1")))
    for i in range(6):
        x, y = point(i, 1)
        chart.add(Line(245, 144, x, y, strokeColor=colors.HexColor("#CBD5E1")))

    scores = [row["score"] for row in rows]
    accent = colors.HexColor("#5145CD")
    if all(score is not None for score in scores):
        chart.add(Polygon(polygon([score / 100 for score in scores]),
                          fillColor=colors.Color(0.32, 0.27, 0.80, alpha=0.18),
                          strokeColor=accent, strokeWidth=2))
    for i, row in enumerate(rows):
        score = scores[i]
        x, y = point(i, 1.25)
        anchor = "middle" if i in (0, 3) else ("start" if i < 3 else "end")
        score_label = f"{score:.0f}점" if score is not None else "응답 부족"
        chart.add(String(x, y - 3, f"{row['label']} {score_label}",
                         textAnchor=anchor, fontName=font, fontSize=11,
                         fillColor=colors.HexColor("#24324A")))
        if score is not None:
            x, y = point(i, score / 100)
            chart.add(Circle(x, y, 3, fillColor=accent, strokeColor=None))
    return chart


def radar_svg(rows):
    # 브라우저는 자체 한글 글꼴을 사용합니다.
    return "<svg" + renderSVG.drawToString(radar(rows, "Helvetica")).split("<svg", 1)[1]


def create_pdf(result, rows):
    # 1. 한글 글꼴 준비
    font_path = (
        Path(__file__).resolve().parent
        / "NanumGothic-Regular.ttf"
    )

    if not font_path.exists():
        raise FileNotFoundError(
            "love-test 폴더에 "
            "NanumGothic-Regular.ttf 파일을 넣어 주세요."
        )

    pdfmetrics.registerFont(
        TTFont("Korean", str(font_path))
    )

    # 2. PDF를 메모리에서 생성
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    title_style = ParagraphStyle(
        "TitleKR",
        fontName="Korean",
        fontSize=20,
        leading=28,
        textColor=colors.HexColor("#24324A"),
        spaceAfter=16,
        wordWrap="CJK",
    )

    heading_style = ParagraphStyle(
        "HeadingKR",
        fontName="Korean",
        fontSize=13,
        leading=18,
        spaceBefore=12,
        spaceAfter=6,
        wordWrap="CJK",
    )

    body_style = ParagraphStyle(
        "BodyKR",
        fontName="Korean",
        fontSize=10,
        leading=15,
        spaceAfter=6,
        wordWrap="CJK",
    )

    story = []

    def add_heading(text):
        story.append(
            Paragraph(escape(text), heading_style)
        )

    def add_body(text):
        story.append(
            Paragraph(escape(text), body_style)
        )

    # 3. 제목과 기본 정보
    story.append(
        Paragraph("나의 관계 성향 결과지", title_style)
    )

    add_body(f"이름 또는 별명: {result['name']}")
    add_body(f"떠올린 관계: {result['relationship']}")

    # 4. 불안·회피 점수 표
    add_heading("1. 관계 불안과 회피")

    data = [
        ["항목", "점수"],
        ["관계 불안", f"{result['anxiety']:.1f} / 100"],
        ["관계 회피", f"{result['avoidance']:.1f} / 100"],
    ]

    table = Table(data, colWidths=[300, 130])

    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Korean"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("BACKGROUND", (0, 0), (-1, 0),
         colors.HexColor("#EAF0F8")),
        ("GRID", (0, 0), (-1, -1),
         0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))

    story.append(table)
    story.append(Spacer(1, 10))

    add_body(
        "관계 불안은 상대의 마음이나 관계 유지에 대한 걱정을, "
        "관계 회피는 친밀감이나 상대에게 의지하는 상황에 대한 "
        "불편을 묻는 응답에서 계산했습니다."
    )

    # 5. 네 성향의 가로 막대그래프
    add_heading("2. 네 성향의 참고용 비중")

    chart = Drawing(490, 155)

    for index, (label, score) in enumerate(
        result["types"].items()
    ):
        y = 125 - index * 35

        chart.add(String(
            0, y + 3, label,
            fontName="Korean",
            fontSize=10,
        ))

        chart.add(Rect(
            140, y, 280, 14,
            fillColor=colors.HexColor("#E5E7EB"),
            strokeColor=None,
        ))

        chart.add(Rect(
            140, y, 280 * score / 100, 14,
            fillColor=colors.HexColor("#6366F1"),
            strokeColor=None,
        ))

        chart.add(String(
            432, y + 3, f"{score:.1f}%",
            fontName="Korean",
            fontSize=10,
        ))

    story.append(chart)

    add_body(
        "이 비중은 불안·회피 점수를 조합한 자체 환산값입니다. "
        "각 유형일 확률이나 진단 결과가 아닙니다. "
        "반올림으로 합계에 작은 차이가 날 수 있습니다."
    )

    add_heading("한눈에 보는 응답")
    for title, detail in list(reflection(rows))[:2]:
        add_body(f"{title}: {detail}")

    add_heading("결과를 읽을 때")

    add_body(
        "검증 전 자체 제작 자기이해용 설문입니다. "
        "점수는 응답 범위를 0~100으로 환산한 값이며 "
        "인구 백분위가 아닙니다. "
        "결과는 선택한 관계에 대한 응답을 설명하며, "
        "성격이나 다른 관계의 모습을 확정하지 않습니다."
    )

    story.append(PageBreak())
    add_heading("3. 여섯 가지 관계 주제")
    story.append(radar(rows))
    add_body(RADAR_NOTE)
    if any(row["score"] is None for row in rows):
        add_body("응답이 3개 미만인 축은 점과 면을 채우지 않았습니다.")

    add_heading("4. 응답 근거와 주제별 해설")
    add_body("주제별 4문항 중 최소 3개를 답한 경우에만 역채점 후 평균을 0~100으로 환산합니다. "
             "각 점수는 집단과 비교한 기준이 아니며, 선택한 관계에만 해당합니다.")

    for row in rows:
        start = len(story)
        score = row["score"]
        label = f"{score:.1f}점" if score is not None else "응답 부족"
        add_heading(f"{row['label']}  |  {label}  |  응답 {row['count']}/4")
        add_body(f"살펴보는 내용: {row['meaning']}.")
        if score is not None:
            items = sorted(row["evidence"], key=lambda item: (-item[2], item[0]))
            high = next((item for item in items if item[2] >= 4), None)
            low = next((item for item in reversed(items) if item[2] <= 2), None)
            if high:
                add_body(f"부담과 연결된 응답: {high[1]}")
            if low:
                add_body(f"편안함과 연결된 응답: {low[1]}")
            if not high and not low:
                add_body("이 주제에서는 걱정이나 편안함 어느 쪽도 강하게 답하지 않았습니다.")
        story[start:] = [KeepTogether(story[start:])]

    add_heading("5. 강점과 개선을 위한 실행 계획")
    for title, detail in reflection(rows):
        story.append(KeepTogether([
            Paragraph(escape(title), heading_style),
            Paragraph(escape(detail), body_style),
        ]))

    doc.title = "나의 관계 성향 결과지"

    # 8. PDF 완성
    def page_number(canvas, doc):
        canvas.setFont("Korean", 9)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawRightString(A4[0] - 40, 24, str(doc.page))

    doc.build(story, onFirstPage=page_number, onLaterPages=page_number)

    return buffer.getvalue()
