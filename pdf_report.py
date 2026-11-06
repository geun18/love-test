from io import BytesIO
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
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Drawing, Rect, String


def create_pdf(result):
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
        leading=20,
        spaceBefore=16,
        spaceAfter=8,
        wordWrap="CJK",
    )

    body_style = ParagraphStyle(
        "BodyKR",
        fontName="Korean",
        fontSize=10,
        leading=17,
        spaceAfter=8,
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

    # 6. 점수에 따른 기본 해설
    add_heading("3. 응답에서 살펴볼 관계 패턴")

    add_body(
        "아래 문구는 두 점수를 비교한 기본 해설입니다. "
        "점수의 작은 차이보다 실제 경험과 맞는지 살펴보세요."
    )

    anxiety = result["anxiety"]
    avoidance = result["avoidance"]

    if abs(anxiety - avoidance) < 10:
        add_body(
            "이번 응답에서는 불안과 회피 점수가 비슷하게 "
            "나타났습니다. 두 점수가 모두 낮은지, 모두 높은지에 "
            "따라 경험은 다를 수 있습니다. "
            "가까워지고 싶은 마음과 혼자 있고 싶은 마음이 "
            "언제 나타나는지 각각 돌아보세요."
        )

    elif anxiety > avoidance:
        add_body(
            "이번 응답에서는 친밀감을 피하는 반응보다 "
            "상대의 마음이나 관계 유지에 대해 걱정하는 "
            "반응의 점수가 더 높았습니다. "
            "연락이나 표현이 달라졌을 때 어떤 생각이 "
            "먼저 드는지 살펴보세요."
        )

    else:
        add_body(
            "이번 응답에서는 관계 유지에 대한 걱정보다 "
            "친밀감이나 의지하는 상황에 대한 불편의 "
            "점수가 더 높았습니다. "
            "개인 시간이 필요한 때와 감정을 나누기 어려워 "
            "거리를 두는 때를 구분해 보세요."
        )

    # 7. 실행 안내
    add_heading("4. 이번 주에 해볼 작은 행동")

    add_body(
        "1. 마음이 흔들린 상황을 하나 적고, "
        "실제로 일어난 일과 내가 추측한 내용을 나누어 적어보세요."
    )

    add_body(
        "2. 상대에게 필요한 것을 한 문장으로 말해보세요. "
        "예: '연락이 어려운 날에는 미리 알려주면 마음이 편할 것 같아.'"
    )

    add_body(
        "3. 대화를 잠시 멈추고 싶다면 다시 이야기할 시간을 "
        "함께 정해보세요. "
        "예: '지금은 정리가 필요해. 오늘 저녁에 다시 이야기하자.'"
    )

    add_heading("결과를 읽을 때")

    add_body(
        "검증 전 자체 제작 자기이해용 설문입니다. "
        "점수는 응답 범위를 0~100으로 환산한 값이며 "
        "인구 백분위가 아닙니다. "
        "결과는 선택한 관계에 대한 응답을 설명하며, "
        "성격이나 다른 관계의 모습을 확정하지 않습니다."
    )

    # 8. PDF 완성
    doc.build(story)

    return buffer.getvalue()