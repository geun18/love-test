from io import BytesIO
from math import cos, sin, pi
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
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
    Flowable,
    HRFlowable,
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


MBTI_TYPES = tuple(
    e + s + t + j for e in "IE" for s in "SN" for t in "TF" for j in "JP"
)
MBTI_NOTE = "본인이 선택한 유형을 대화 방법을 고르는 참고로 사용했습니다. 실제로 편한 방법을 선택하세요. MBTI는 설문 점수나 유형 비중에 반영되지 않습니다."


def mbti_reflection(mbti, rows):
    if mbti not in MBTI_TYPES:
        return []
    valid = [row for row in rows if row["score"] is not None]
    focus = max(valid, key=lambda row: row["score"], default=None)
    if focus and focus["score"] >= 62.5:
        evidence = max(focus["evidence"], key=lambda item: item[2])
        context = f"‘{focus['label']}’을 먼저 살펴볼 수 있어요. 그중 {evidence[1]} 이 문항과 비슷한 실제 상황 하나를 떠올려 아래 방법을 적용해 보세요."
    else:
        context = "특별히 높게 나온 주제가 없다면 최근에 대화가 조금 어려웠던 장면 하나를 골라 아래 방법을 적용해 보세요."

    timing = {
        "I": "혼자 생각을 정리한 뒤 말하는 게 편하다면, 전하고 싶은 말을 한 줄 적고 대화를 다시 시작할 시간을 알려 주세요.",
        "E": "말하면서 생각을 정리하는 게 편하다면, 상대에게 잠깐 들어줄 여유가 있는지 먼저 묻고 이야기해 보세요.",
    }
    framing = {
        "S": "구체적인 예가 편하다면, 실제로 있었던 일 한 가지를 시간이나 행동을 넣어 설명해 보세요.",
        "N": "대화의 큰 그림부터 보는 게 편하다면, 두 사람이 원하는 관계를 먼저 말한 뒤 이번에 있었던 일 하나로 좁혀 보세요.",
    }
    response = {
        "T": "문제와 해결책을 정리하는 게 편하다면, 제안을 하기 전에 상대가 지금 공감을 원하는지 해결책을 원하는지 물어보세요.",
        "F": "서로의 감정과 중요하게 여기는 점부터 살피는 게 편하다면, 공감을 표현한 뒤 내가 필요한 것도 한 문장으로 말해 보세요.",
    }
    plan = {
        "J": "일정이 정해지면 마음이 편하다면, 다음 대화 시간을 정하고 함께 지킬 작은 약속 하나만 골라보세요.",
        "P": "여러 선택지를 열어두는 게 편하다면, 가능한 방법 두 가지 중 하나를 며칠간 시험해 보고 다시 이야기할 날짜를 정해 보세요.",
    }

    return [
        ("설문 응답과 함께 보기", context),
        ("대화 시작", timing[mbti[0]]),
        ("상황 설명", framing[mbti[1]]),
        ("상대와 의견 나누기", response[mbti[2]]),
        ("다음 행동 정하기", plan[mbti[3]]),
    ]


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
    accent = colors.HexColor("#8355CD")
    if all(score is not None for score in scores):
        chart.add(Polygon(polygon([score / 100 for score in scores]),
                          fillColor=colors.Color(0.32, 0.27, 0.80, alpha=0.18),
                          strokeColor=accent, strokeWidth=2))
    else:
        available = [i for i, score in enumerate(scores) if score is not None]
        if len(available) >= 2:
            pairs = list(zip(available, available[1:]))
            if len(available) > 2:
                pairs.append((available[-1], available[0]))
            elif (available[0] - available[1]) % 6 == 1:
                pairs = [(available[1], available[0])]

            for start, end in pairs:
                x1, y1 = point(start, scores[start] / 100)
                x2, y2 = point(end, scores[end] / 100)
                line = Line(x1, y1, x2, y2, strokeColor=accent, strokeWidth=2)
                if (end - start) % 6 != 1:
                    line.strokeDashArray = [5, 4]
                chart.add(line)
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


class LoveOnHeader(Flowable):
    def __init__(self, result):
        super().__init__()
        self.result = result
        self.assets = Path(__file__).resolve().parent
        style = ParagraphStyle(
            "LoveOnRecipient", fontName="Korean", fontSize=16, leading=22,
            alignment=TA_CENTER, wordWrap="CJK", textColor=colors.HexColor("#2F2244"),
        )
        self.recipient = Paragraph(
            escape(f"{result['name']}님의 관계 성향 결과"), style
        )

    def wrap(self, available_width, available_height):
        self.width = available_width
        _, self.recipient_height = self.recipient.wrap(self.width - 40, available_height)
        self.height = 183 + self.recipient_height
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        w, h = self.width, self.height
        canvas.saveState()
        outline = canvas.beginPath()
        outline.roundRect(0, 0, w, h, 18)
        canvas.clipPath(outline, stroke=0, fill=0)
        canvas.setFillColor(colors.HexColor("#FFF4F9"))
        canvas.rect(0, 0, w, h, fill=1, stroke=0)
        background = self.assets / "loveon-background.png"
        if background.is_file():
            canvas.drawImage(str(background), 0, 0, w, h, mask="auto")
        logo = self.assets / "loveon-logo.png"
        if logo.is_file():
            canvas.drawImage(str(logo), w / 2 - 42, h - 95, 84, 84, mask="auto")
        canvas.setFillColor(colors.HexColor("#592B82"))
        canvas.setFont("Korean", 34)
        canvas.drawCentredString(w / 2, h - 127, "Love:ON")
        self.recipient.drawOn(canvas, 20, 44)
        canvas.setFillColor(colors.HexColor("#553972"))
        canvas.setFont("Korean", 10)
        subtitle = f"떠올린 관계 · {self.result['relationship']}"
        if self.result.get("mbti") in MBTI_TYPES:
            subtitle += f"   |   MBTI · {self.result['mbti']} (본인 입력)"
        canvas.drawCentredString(w / 2, 24, subtitle)
        canvas.restoreState()


class ScoreCards(Flowable):
    def __init__(self, result):
        super().__init__()
        self.result = result
        self.height = 64

    def wrap(self, available_width, available_height):
        self.width = available_width
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        card_width = (self.width - 12) / 2
        for index, (label, key, fill, ink) in enumerate((
            ("관계 불안", "anxiety", "#F6F0FF", "#3F2864"),
            ("관계 회피", "avoidance", "#FFF0F6", "#6B2D51"),
        )):
            x = index * (card_width + 12)
            canvas.setFillColor(colors.HexColor(fill))
            canvas.roundRect(x, 0, card_width, self.height, 12, fill=1, stroke=0)
            canvas.setFillColor(colors.HexColor(ink))
            canvas.setFont("Korean", 11)
            canvas.drawString(x + 16, 42, label)
            canvas.setFont("Korean", 20)
            canvas.drawString(x + 16, 14, f"{self.result[key]:.1f} / 100")


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

    heading_style = ParagraphStyle(
        "HeadingKR",
        fontName="Korean",
        fontSize=13,
        leading=18,
        spaceBefore=12,
        spaceAfter=6,
        wordWrap="CJK",
    )

    section_style = ParagraphStyle(
        "MajorSectionKR", parent=heading_style, fontSize=14,
        textColor=colors.HexColor("#592B82"), spaceAfter=4, keepWithNext=True,
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

    def add_section(text):
        story.append(Paragraph(escape(text), section_style))
        rule = HRFlowable(
            width="100%", thickness=1, color=colors.HexColor("#C9ACDE"),
            spaceAfter=7,
        )
        rule.keepWithNext = True
        story.append(rule)

    def add_body(text):
        story.append(
            Paragraph(escape(text), body_style)
        )

    story.extend([LoveOnHeader(result), Spacer(1, 12), ScoreCards(result), Spacer(1, 10)])

    add_body(
        "관계 불안은 상대의 마음이나 관계 유지에 대한 걱정을, "
        "관계 회피는 친밀감이나 상대에게 의지하는 상황에 대한 "
        "불편을 묻는 응답에서 계산했습니다."
    )

    # 5. 네 성향의 가로 막대그래프
    add_section("네 성향의 참고용 비중")

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
            fillColor=colors.HexColor("#EEE8F6"),
            strokeColor=None,
        ))

        chart.add(Rect(
            140, y, 280 * score / 100, 14,
            fillColor=colors.HexColor("#8355CD"),
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

    add_section("한눈에 보는 응답")
    for title, detail in list(reflection(rows))[:2]:
        add_body(f"{title}: {detail}")

    add_section("결과를 읽을 때")

    add_body(
        "검증 전 자체 제작 자기이해용 설문입니다. "
        "점수는 응답 범위를 0~100으로 환산한 값이며 "
        "인구 백분위가 아닙니다. "
        "결과는 선택한 관계에 대한 응답을 설명하며, "
        "성격이나 다른 관계의 모습을 확정하지 않습니다."
    )

    story.append(PageBreak())
    add_section("여섯 가지 관계 주제")
    story.append(radar(rows))
    add_body(RADAR_NOTE)
    if any(row["score"] is None for row in rows):
        add_body("실선은 인접한 점을, 점선은 응답 부족 축을 건너뛴 구간을 연결합니다. 응답이 부족한 축은 점수를 표시하지 않습니다.")

    add_section("응답 근거와 주제별 해설")
    add_body("주제별 4문항 중 최소 3개를 답한 경우에만 역채점 후 평균을 0~100으로 환산합니다. "
             "각 점수는 집단과 비교한 기준이 아니며, 선택한 관계에만 해당합니다.")

    for row in rows:
        start = len(story)
        score = row["score"]
        label = f"{score:.1f}점" if score is not None else "응답 부족"
        add_heading(f"{row['label']}  |  {label}  |  응답 {row['count']}/4")
        add_body(f"살펴보는 내용: {row['meaning']}.")
        evidence = row["evidence"]
        high = max(evidence, key=lambda item: item[2], default=None)
        low = min(evidence, key=lambda item: item[2], default=None)
        for item in evidence:
            tag = ""
            if score is not None:
                if item == high and item[2] >= 4:
                    tag = " [부담과 연결된 응답]"
                elif item == low and item[2] <= 2:
                    tag = " [편안함과 연결된 응답]"
            add_body(item[1] + tag)
        story[start:] = [KeepTogether(story[start:])]

    story.append(PageBreak())
    add_section("내 응답을 바탕으로 돌아보기")
    for title, detail in reflection(rows):
        story.append(KeepTogether([
            Paragraph(escape(title), heading_style),
            Paragraph(escape(detail), body_style),
        ]))

    mbti = result.get("mbti")
    tips = mbti_reflection(mbti, rows)
    if tips:
        add_section(f"MBTI 참고 · {mbti}")
        add_body(MBTI_NOTE)
        for title, detail in tips:
            add_body(f"{title}: {detail}")

    doc.title = "Love:ON | 관계 성향 결과지"

    # 8. PDF 완성
    def page_number(canvas, doc):
        canvas.setFont("Korean", 9)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawRightString(A4[0] - 40, 24, str(doc.page))

    doc.build(story, onFirstPage=page_number, onLaterPages=page_number)

    return buffer.getvalue()
