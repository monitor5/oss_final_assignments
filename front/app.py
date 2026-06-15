"""Camera Match — Streamlit 프론트엔드.

역할(과제 조건):
  - 사용자 입력 받기
  - 추천 요청 버튼
  - FastAPI 에 HTTP 요청 보내기
  - FastAPI 가 반환한 JSON 결과를 화면에 표시
추천 로직은 절대 여기서 계산하지 않는다. (모두 FastAPI 백엔드가 처리)
"""

import os
import requests
import streamlit as st

# 백엔드 주소. docker-compose 에서는 서비스명 'back' 으로 통신한다.
# (로컬 단독 실행 시에는 http://localhost:8000 으로 환경변수 지정)
BACKEND_URL = os.getenv("BACKEND_URL", "http://back:8000")

st.set_page_config(page_title="Camera Match", page_icon="📷", layout="centered")

st.title("📷 Camera Match")
st.caption("입문자를 위한 카메라 센서·렌즈 조합 추천기")

st.markdown("아래 정보를 입력하고 **추천 받기** 버튼을 누르면, "
            "FastAPI 백엔드가 조건에 맞는 센서와 렌즈 조합을 추천합니다.")

# --------------------------------------------------------------------------
# 1) 사용자 입력 (과제 주제.md 의 입력 항목과 일치)
# --------------------------------------------------------------------------
with st.form("recommend_form"):
    budget_label = st.selectbox(
        "예산",
        ["50만 원 이하", "50~100만 원", "100~200만 원", "200만 원 이상"],
    )
    purposes = st.multiselect(
        "주 촬영 목적 (복수 선택 가능)",
        ["여행", "인물", "풍경", "야경", "브이로그", "스포츠"],
        default=["여행"],
    )
    portability = st.slider("휴대성 중요도", 1, 5, 3)
    low_light = st.slider("저조도 중요도", 1, 5, 3)
    video_ratio = st.slider("영상 촬영 비중 (%)", 0, 100, 20)
    skill_label = st.radio("사용자 숙련도", ["입문자", "취미", "중급"], horizontal=True)
    lens_exchange_label = st.radio("렌즈 교환 의향", ["있음", "없음"], horizontal=True)

    submitted = st.form_submit_button("추천 받기")

# 화면 라벨 → 백엔드 코드값 매핑
BUDGET_MAP = {
    "50만 원 이하": "under_50",
    "50~100만 원": "50_100",
    "100~200만 원": "100_200",
    "200만 원 이상": "over_200",
}
SKILL_MAP = {"입문자": "beginner", "취미": "hobby", "중급": "intermediate"}

# --------------------------------------------------------------------------
# 2) FastAPI 호출 → 3) 결과 출력
# --------------------------------------------------------------------------
if submitted:
    payload = {
        "budget": BUDGET_MAP[budget_label],
        "purposes": purposes,
        "portability": portability,
        "low_light": low_light,
        "video_ratio": video_ratio,
        "skill_level": SKILL_MAP[skill_label],
        "lens_exchange": lens_exchange_label == "있음",
    }

    try:
        resp = requests.post(f"{BACKEND_URL}/recommend", json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"백엔드(FastAPI) 호출에 실패했습니다: {e}")
        st.info(f"현재 설정된 백엔드 주소: {BACKEND_URL}")
        st.stop()

    # ---- 최종 추천 카드 ----
    st.success(data["headline"])

    col1, col2 = st.columns(2)
    col1.metric("추천 센서", data["sensor"])
    col2.metric("추천 렌즈", data["lens"])

    # ---- 점수 시각화 ----
    st.subheader("점수")
    scores = data["scores"]
    score_items = [
        ("궁합도", scores["match"]),
        ("선명성", scores["sharpness"]),
        ("휴대성", scores["portability"]),
        ("저조도 적합도", scores["low_light"]),
        ("영상 적합도", scores["video"]),
        ("예산 적합도", scores["budget"]),
    ]
    for label, value in score_items:
        st.write(f"**{label}** — {value}점")
        st.progress(value / 100)

    # ---- 추천 이유 ----
    st.subheader("추천 이유")
    st.write(data["reason"])

    # ---- 목적별 렌즈 가이드 ----
    st.subheader("목적별 렌즈 가이드")
    for item in data["lens_guide"]:
        st.write(f"- **{item['purpose']}**: {item['lens']}")

    # ---- 주의 문구 ----
    st.warning(data["notice"])
