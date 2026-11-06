import streamlit as st
from pdf_report import create_pdf

st.set_page_config(
    page_title="나의 관계 성향 테스트",
    page_icon="💛"
)

QUESTIONS = [
    "연락이 평소보다 줄면, 다른 이유보다 우리 사이에 문제가 생겼을 가능성을 먼저 떠올린다.",
    "개인적인 고민을 이야기할수록 상대에게 약점을 드러낸다는 느낌이 든다.",
    "상대가 다른 일에 집중하고 있어도, 나를 소중히 여기는 마음은 유지된다고 느낀다.",
    "힘든 일을 겪을 때 상대에게 기대는 것이 자연스럽다.",
    "상대의 짧은 말이나 표정에서 관계가 달라졌다는 신호를 찾게 된다.",
    "관계가 진지해질수록 혼자 지내던 때로 돌아가고 싶어지는 편이다.",
    "애정 표현을 받아도 시간이 조금 지나면 다시 확인받고 싶어진다.",
    "상대가 내 감정을 물어보면, 대답을 피하고 다른 이야기로 넘기고 싶다.",
    "의견이 부딪혀도 그 일만으로 관계가 끝날 것 같지는 않다.",
    "내게 중요한 감정을 상대와 나누고 나면 가까워졌다는 느낌이 든다.",
    "상대의 마음이 내 마음보다 작을까 봐 신경을 많이 쓴다.",
    "서로 의지하는 사이가 되면 내 선택의 자유가 줄어들 것 같다.",
    "갈등을 겪은 뒤 관계가 괜찮다는 확인을 받기 전까지 다른 일에 집중하기 어렵다.",
    "서운함을 함께 풀기보다 감정이 사라질 때까지 상대를 멀리하는 편이다.",
    "상대가 나와 따로 시간을 보내더라도 우리 관계를 의심하지 않는다.",
    "내게 필요한 도움을 상대에게 구체적으로 부탁할 수 있다.",
    "상대가 원하는 사람이 되어야 관계를 유지할 수 있을 것 같다.",
    "상대가 나를 더 깊이 알고 싶어 하면 부담스러워 거리를 조절하게 된다.",
    "관계가 불확실하다고 느끼면 메시지나 대화를 반복해서 확인한다.",
    "서로의 속마음을 자세히 알아가는 일은 내게 불편하다.",
    "상대가 당장 애정 표현을 하지 않아도 그동안 쌓인 신뢰를 떠올릴 수 있다.",
    "가까운 관계를 유지하면서도 내 생활과 경계를 지킬 수 있다고 느낀다.",
    "상대에게 불만을 말하면 버림받을까 봐 참는 경우가 많다.",
    "상대에게 기대고 싶어질 때, 그런 마음 자체를 억누르려고 한다.",
]

OPTIONS = [
    "선택하세요",
    "1 · 전혀 그렇지 않다",
    "2 · 대체로 그렇지 않다",
    "3 · 어느 쪽도 아니다",
    "4 · 대체로 그렇다",
    "5 · 매우 그렇다",
    "판단하기 어려움",
]

REVERSE = {3, 4, 9, 10, 15, 16, 21, 22}


def calculate_score(answers, numbers):
    values = []

    for number in numbers:
        value = answers[number]

        if value is None:
            continue

        if number in REVERSE:
            value = 6 - value

        values.append(value)

    if len(values) < 10:
        return None

    average = sum(values) / len(values)
    return (average - 1) / 4 * 100


st.title("💛 나의 관계 성향 테스트")
st.write("24문항으로 가까운 관계에서 나타나는 나의 반응을 살펴봅니다.")

st.info(
    "최근 6개월 동안의 경험을 기준으로 답해 주세요. "
    "끝까지 같은 사람과의 관계를 떠올려 주세요."
)

st.caption(
    "검증 전 자체 제작 자기이해용 설문입니다. "
    "진단이나 고정된 성격 판정을 위한 검사가 아닙니다."
)

with st.form("relationship_test"):
    name = st.text_input("이름 또는 별명 — 선택")

    relationship = st.selectbox(
        "어떤 관계를 떠올리며 답할까요?",
        ["현재 연인", "최근 연인", "가까운 친구"]
    )

    st.divider()

    selected = {}

    for number, question in enumerate(QUESTIONS, start=1):
        selected[number] = st.selectbox(
            f"{number}. {question}",
            OPTIONS,
            key=f"question_{number}"
        )

    submitted = st.form_submit_button(
        "결과 보기",
        use_container_width=True
    )

if submitted:
    # 새 제출이 잘못되었을 때 예전 결과가 남지 않도록 합니다.
    st.session_state.pop("result", None)

    missing = [
        number
        for number, answer in selected.items()
        if answer == "선택하세요"
    ]

    if missing:
        missing_text = ", ".join(map(str, missing))
        st.warning(f"아직 선택하지 않은 문항이 있어요: {missing_text}번")

    else:
        answers = {}

        for number, answer in selected.items():
            if answer == "판단하기 어려움":
                answers[number] = None
            else:
                answers[number] = int(answer[0])

        anxiety = calculate_score(answers, range(1, 25, 2))
        avoidance = calculate_score(answers, range(2, 25, 2))

        if anxiety is None or avoidance is None:
            st.warning(
                "점수를 계산할 응답이 부족합니다. "
                "홀수 문항과 짝수 문항에서 각각 "
                "최소 10개에 1~5점으로 답해 주세요. "
                "경험이 없다면 억지로 답하지 않아도 됩니다."
            )

        else:
            a = anxiety / 100
            v = avoidance / 100

            type_scores = {
                "안정형": (1 - a) * (1 - v) * 100,
                "불안형": a * (1 - v) * 100,
                "회피형": (1 - a) * v * 100,
                "공포회피형(혼란형)": a * v * 100,
            }

            st.session_state["result"] = {
                "name": name.strip() or "참여자",
                "relationship": relationship,
                "answers": answers,
                "anxiety": anxiety,
                "avoidance": avoidance,
                "types": type_scores,
            }

if "result" in st.session_state:
    result = st.session_state["result"]

    st.divider()
    st.subheader(f"📊 {result['name']}님의 결과")
    st.write(f"떠올린 관계: **{result['relationship']}**")

    left, right = st.columns(2)

    with left:
        st.metric(
            "관계 불안",
            f"{result['anxiety']:.1f} / 100"
        )

    with right:
        st.metric(
            "관계 회피",
            f"{result['avoidance']:.1f} / 100"
        )

    st.write(
        "관계 불안은 상대의 마음이나 관계 유지에 대한 걱정, "
        "관계 회피는 친밀감이나 의지하는 상황에 대한 "
        "불편을 묻는 응답에서 계산했습니다."
    )

    st.subheader("네 성향의 참고용 비중")

    for label, score in result["types"].items():
        st.write(f"**{label}: {score:.1f}%**")
        st.progress(max(0.0, min(1.0, score / 100)))

    st.caption(
        "두 점수는 설문 응답을 0~100으로 환산한 값이며 "
        "인구 백분위가 아닙니다. 네 성향의 비중은 자체 환산식에 "
        "따른 참고값으로, 해당 유형일 확률이나 진단 결과가 아닙니다. "
        "반올림으로 합계에 작은 차이가 날 수 있습니다."
    )

    st.info(
        "응답을 수정했다면 '결과 보기'를 다시 눌러 주세요. "
        "결과는 마지막으로 제출한 답변을 기준으로 표시됩니다."
    )
    
if "result" in st.session_state:
    st.divider()
    st.subheader("결과지 저장하기")

    try:
        pdf_bytes = create_pdf(st.session_state["result"])

    except FileNotFoundError as error:
        st.error(str(error))

    else:
        st.download_button(
            label="📄 결과지 PDF 다운로드",
            data=pdf_bytes,
            file_name="관계성향_결과지.pdf",
            mime="application/pdf",
            use_container_width=True,
        )