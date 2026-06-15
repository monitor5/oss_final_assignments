"""Camera Match — Streamlit 프론트엔드.

역할(과제 조건):
  - 사용자 입력 받기
  - 추천 요청 버튼
  - FastAPI 에 HTTP 요청 보내기
  - FastAPI 가 반환한 JSON 결과를 화면에 표시
  - (추가) 이름+패스워드로 결과 저장/불러오기 → 저장도 FastAPI 가 처리
추천 계산과 저장 로직은 절대 여기서 하지 않는다. (모두 FastAPI 백엔드가 처리)
"""

import os
import json
import requests
import pandas as pd
import altair as alt
import streamlit as st

# 백엔드 주소. docker-compose 에서는 서비스명 'back' 으로 통신한다.
BACKEND_URL = os.getenv("BACKEND_URL", "http://back:8000")

st.set_page_config(page_title="Camera Match", page_icon="📷", layout="wide")

# --------------------------------------------------------------------------
# 화려한 스타일 (커스텀 CSS)
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .reco-card {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 22px 26px; border-radius: 16px; color:#fff;
        box-shadow: 0 6px 18px rgba(17,153,142,0.28); margin: 6px 0 14px 0;
    }
    .reco-card .sensor { font-size: 1.6rem; font-weight: 800; }
    .reco-card .lens   { font-size: 1.05rem; opacity: 0.95; margin-top:4px; }
    div[data-testid="stMetric"] {
        background: #f6f8fc; border: 1px solid #e6ebf5;
        border-radius: 12px; padding: 12px 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📷 Camera Match")
st.caption("입문자를 위한 카메라 센서·렌즈 조합 추천기 — 조건을 입력하면 FastAPI 가 딱 맞는 조합을 찾아드립니다.")

# 라벨 ↔ 백엔드 코드값 매핑
BUDGET_MAP = {
    "50만 원 이하": "under_50",
    "50~100만 원": "50_100",
    "100~200만 원": "100_200",
    "200만 원 이상": "over_200",
}
SKILL_MAP = {"입문자": "beginner", "취미": "hobby", "중급": "intermediate"}

# 세션 상태 초기화
st.session_state.setdefault("last_result", None)
st.session_state.setdefault("last_inputs", None)
st.session_state.setdefault("loaded_records", None)


# --------------------------------------------------------------------------
# 사이드바: 이름 + 패스워드 (계정)
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("👤 내 계정")
    st.caption("이름과 패스워드로 추천 결과를 저장하고 다시 불러올 수 있어요.")
    user_name = st.text_input("이름", key="user_name", placeholder="예: 김우현")
    user_pw = st.text_input("패스워드", key="user_pw", type="password")
    st.divider()
    st.caption(f"백엔드: {BACKEND_URL}")


# --------------------------------------------------------------------------
# 점수 차트 (Altair 가로 막대) — 화려한 시각화
# --------------------------------------------------------------------------
def score_chart(scores: dict):
    label_map = {
        "match": "궁합도",
        "sharpness": "선명성",
        "portability": "휴대성",
        "low_light": "저조도",
        "video": "영상 적합도",
        "budget": "예산 적합도",
    }
    df = pd.DataFrame(
        {"항목": [label_map[k] for k in label_map], "점수": [scores[k] for k in label_map]}
    )
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=8, height=22)
        .encode(
            x=alt.X("점수:Q", scale=alt.Scale(domain=[0, 100]), title=None),
            y=alt.Y("항목:N", sort=None, title=None),
            color=alt.Color(
                "점수:Q",
                scale=alt.Scale(scheme="tealblues", domain=[0, 100]),
                legend=None,
            ),
            tooltip=["항목", "점수"],
        )
        .properties(height=230)
    )
    text = chart.mark_text(align="left", dx=4, color="#333").encode(text="점수:Q")
    return chart + text


# --------------------------------------------------------------------------
# 추천 결과 렌더링 (새 결과 / 저장된 기록 모두 재사용)
# --------------------------------------------------------------------------
def render_result(data: dict, inputs: dict | None = None, nested: bool = False):
    st.markdown(
        f"""
        <div class="reco-card">
            <div class="sensor">📸 {data['sensor']}</div>
            <div class="lens">🔍 {data['lens']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.success(data["headline"])

    if inputs:
        # 이미 expander 안에서 호출된 경우(내 기록 탭)에는 expander 를 중첩할 수 없으므로
        # 그냥 펼쳐서 보여준다.
        if nested:
            st.markdown("**🧾 입력 요약**")
            st.json(inputs)
        else:
            with st.expander("🧾 입력 요약 보기"):
                st.json(inputs)

    left, right = st.columns([1.1, 1])
    with left:
        st.markdown("##### 📊 점수")
        st.altair_chart(score_chart(data["scores"]), use_container_width=True)
    with right:
        s = data["scores"]
        st.metric("궁합도", f"{s['match']}점")
        c1, c2 = st.columns(2)
        c1.metric("선명성", s["sharpness"])
        c2.metric("휴대성", s["portability"])
        c3, c4 = st.columns(2)
        c3.metric("저조도", s["low_light"])
        c4.metric("예산 적합도", s["budget"])

    st.markdown("##### 💡 추천 이유")
    st.info(data["reason"])

    st.markdown("##### 🎒 목적별 렌즈 가이드")
    cols = st.columns(min(3, max(1, len(data["lens_guide"]))))
    for i, item in enumerate(data["lens_guide"]):
        with cols[i % len(cols)]:
            st.markdown(f"**{item['purpose']}**\n\n{item['lens']}")

    st.warning(data["notice"])


# --------------------------------------------------------------------------
# 탭 구성: 추천 받기 / 내 기록
# --------------------------------------------------------------------------
tab_reco, tab_history = st.tabs(["🎯 추천 받기", "💾 내 기록"])

# ===== 탭 1: 추천 받기 =====
with tab_reco:
    with st.form("recommend_form"):
        c1, c2 = st.columns(2)
        with c1:
            budget_label = st.selectbox(
                "💰 예산", ["50만 원 이하", "50~100만 원", "100~200만 원", "200만 원 이상"]
            )
            purposes = st.multiselect(
                "🎬 주 촬영 목적 (복수 선택)",
                ["여행", "인물", "풍경", "야경", "브이로그", "스포츠"],
                default=["여행"],
            )
            skill_label = st.radio("🧑‍🎓 숙련도", ["입문자", "취미", "중급"], horizontal=True)
            lens_exchange_label = st.radio("🔄 렌즈 교환 의향", ["있음", "없음"], horizontal=True)
        with c2:
            portability = st.slider("🎒 휴대성 중요도", 1, 5, 3)
            low_light = st.slider("🌙 저조도 중요도", 1, 5, 3)
            video_ratio = st.slider("🎥 영상 촬영 비중 (%)", 0, 100, 20)

        submitted = st.form_submit_button("✨ 추천 받기", use_container_width=True)

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
            st.stop()

        # 저장/표시용으로 사람이 읽기 좋은 입력 요약도 함께 보관
        readable_inputs = {
            "예산": budget_label,
            "촬영 목적": purposes,
            "휴대성 중요도": portability,
            "저조도 중요도": low_light,
            "영상 비중(%)": video_ratio,
            "숙련도": skill_label,
            "렌즈 교환": lens_exchange_label,
        }
        st.session_state["last_result"] = data
        st.session_state["last_inputs"] = readable_inputs
        st.balloons()

    # 마지막 추천 결과가 있으면 표시 + 저장 버튼
    if st.session_state["last_result"]:
        render_result(st.session_state["last_result"], st.session_state["last_inputs"])

        st.divider()
        st.markdown("#### 💾 이 결과 저장하기")
        if not (user_name and user_pw):
            st.caption("왼쪽 사이드바에서 이름과 패스워드를 입력하면 저장할 수 있어요.")
        if st.button("저장하기", disabled=not (user_name and user_pw)):
            try:
                r = requests.post(
                    f"{BACKEND_URL}/save",
                    json={
                        "name": user_name,
                        "password": user_pw,
                        "inputs": st.session_state["last_inputs"],
                        "result": st.session_state["last_result"],
                    },
                    timeout=10,
                )
                if r.status_code == 401:
                    st.error("이미 사용 중인 이름입니다. 패스워드가 일치하지 않습니다.")
                else:
                    r.raise_for_status()
                    st.success(f"저장 완료! (누적 {r.json()['count']}건) — '내 기록' 탭에서 확인하세요.")
            except requests.exceptions.RequestException as e:
                st.error(f"저장 실패: {e}")

# ===== 탭 2: 내 기록 =====
with tab_history:
    st.markdown("#### 💾 저장한 추천 기록 불러오기")
    st.caption("왼쪽 사이드바의 이름·패스워드로 저장했던 결과를 불러옵니다.")

    if st.button("📂 불러오기", disabled=not (user_name and user_pw), use_container_width=True):
        try:
            r = requests.post(
                f"{BACKEND_URL}/load",
                json={"name": user_name, "password": user_pw},
                timeout=10,
            )
            if r.status_code == 401:
                st.error("패스워드가 일치하지 않습니다.")
                st.stop()
            r.raise_for_status()
            st.session_state["loaded_records"] = r.json()["records"]
        except requests.exceptions.RequestException as e:
            st.error(f"불러오기 실패: {e}")
            st.stop()

    records = st.session_state["loaded_records"]
    if records is not None:
        if not records:
            st.info("저장된 기록이 없습니다. '추천 받기' 탭에서 추천 후 저장해 보세요.")
        else:
            st.success(f"총 {len(records)}건의 기록을 불러왔습니다.")
            # JSON 백업 다운로드
            backup_json = json.dumps({"records": records}, ensure_ascii=False, indent=2)
            st.download_button(
                "⬇️ JSON으로 백업 다운로드",
                data=backup_json.encode("utf-8"),
                file_name=f"camera_match_{user_name or 'backup'}.json",
                mime="application/json",
                use_container_width=True,
            )
            for idx, rec in enumerate(records, 1):
                title = f"#{idx} · {rec['saved_at']} · {rec['result']['sensor']}"
                with st.expander(title):
                    render_result(rec["result"], rec.get("inputs"), nested=True)

    # JSON 복원(업로드) — 백엔드 /restore 로 전송해 계정에 추가
    st.divider()
    st.markdown("#### ♻️ JSON 백업에서 복원")
    st.caption("백업했던 JSON 파일을 올리면, 사이드바의 이름·패스워드 계정에 기록이 추가됩니다.")
    uploaded = st.file_uploader("백업 JSON 파일 선택", type=["json"])
    if st.button("복원하기", disabled=not (user_name and user_pw and uploaded is not None)):
        try:
            payload = json.loads(uploaded.getvalue().decode("utf-8"))
            restore_records = payload["records"] if isinstance(payload, dict) else payload
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
            st.error("올바른 백업 JSON 파일이 아닙니다.")
            st.stop()
        try:
            r = requests.post(
                f"{BACKEND_URL}/restore",
                json={"name": user_name, "password": user_pw, "records": restore_records},
                timeout=10,
            )
            if r.status_code == 401:
                st.error("이미 사용 중인 이름입니다. 패스워드가 일치하지 않습니다.")
            elif r.status_code == 422:
                st.error("백업 파일의 형식이 맞지 않아 복원할 수 없습니다.")
            else:
                r.raise_for_status()
                st.success(f"복원 완료! (누적 {r.json()['count']}건) — '불러오기'로 확인하세요.")
                st.session_state["loaded_records"] = None
        except requests.exceptions.RequestException as e:
            st.error(f"복원 실패: {e}")

    if not (user_name and user_pw):
        st.caption("👈 먼저 사이드바에서 이름과 패스워드를 입력하세요.")


# --------------------------------------------------------------------------
# 추천 점수 계산 방법 안내 (백엔드 recommender.py 규칙을 설명만 표시)
# --------------------------------------------------------------------------
st.divider()
with st.expander("📐 추천 점수는 어떻게 계산되나요?"):
    st.markdown(
        """
규칙 기반(rule-based) 방식입니다. **계산은 전부 FastAPI 백엔드에서 수행**되고,
이 화면은 결과만 받아서 보여줍니다.

**① 센서 타입별 기본 특성 (0~100)**

| 센서 | 휴대성 | 저조도 | 선명성 | 영상 |
|------|:---:|:---:|:---:|:---:|
| 스마트폰/컴팩트 | 95 | 45 | 55 | 70 |
| 마이크로 포서드 | 82 | 62 | 72 | 82 |
| APS-C 미러리스 | 68 | 74 | 82 | 80 |
| 풀프레임 미러리스 | 42 | 95 | 93 | 86 |

예산 적합도는 센서마다 예산 구간(50만 이하 / 50~100 / 100~200 / 200만 이상)별로 따로 정의됩니다.

**② 입력값 → 가중치**

- 휴대성 가중치 `w_port = 휴대성 중요도 / 5`
- 저조도 가중치 `w_low = 저조도 중요도 / 5` (야경 선택 시 +0.3, 인물 +0.1)
- 영상 가중치 `w_video = 영상 비중(%) / 100`
- 선명성 가중치 `w_sharp = 0.6` (풍경·인물 선택 시 +0.3)

**③ 센서별 점수 합산**

```
점수 = w_port×휴대성 + w_low×저조도 + w_sharp×선명성
       + w_video×영상 + 1.2×예산적합도
```

여기에 보정을 더합니다.
- 입문자 → 휴대성 가산, 풀프레임 −25 (부담 큼)
- 중급 → APS-C·풀프레임 +20
- 렌즈 교환 의향 없음 → 컴팩트(고정렌즈) +60, 나머지 −30
- 스포츠 선택 → APS-C·풀프레임 +15 (AF·망원 유리)

**④ 최종 선택**

가중치 합으로 나눠 0~100 으로 정규화한 뒤, **가장 점수가 높은 센서**를 추천하고
그 값을 **궁합도**로 표시합니다. 선명성·휴대성·저조도·영상·예산 적합도 점수는
선택된 센서의 기본 특성에 입력 가중을 일부 반영해 계산합니다.
"""
    )
