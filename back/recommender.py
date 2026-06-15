"""규칙 기반(rule-based) 카메라 센서 / 렌즈 추천 로직.

복잡한 머신러닝 없이, 입력값에 따라 센서 타입별 점수를 계산하고
가장 점수가 높은 센서를 고른 뒤, 촬영 목적에 맞는 렌즈 조합을 추천한다.
(과제 조건: 추천 로직은 반드시 FastAPI 백엔드에서 처리)
"""

from models import (
    RecommendationRequest,
    RecommendationResponse,
    ScoreBreakdown,
    LensGuideItem,
)


# ---------------------------------------------------------------------------
# 센서 타입별 기본 특성 (0~100). 입문자용 가이드 기준의 대략적인 값.
# ---------------------------------------------------------------------------
SENSORS = {
    "compact": {
        "label": "스마트폰 / 하이엔드 컴팩트",
        "portability": 95,
        "low_light": 45,
        "sharpness": 55,
        "video": 70,
        # 예산 구간별 적합도
        "budget_fit": {"under_50": 95, "50_100": 80, "100_200": 55, "over_200": 40},
    },
    "m43": {
        "label": "마이크로 포서드 미러리스",
        "portability": 82,
        "low_light": 62,
        "sharpness": 72,
        "video": 82,
        "budget_fit": {"under_50": 60, "50_100": 90, "100_200": 80, "over_200": 65},
    },
    "apsc": {
        "label": "APS-C 미러리스",
        "portability": 68,
        "low_light": 74,
        "sharpness": 82,
        "video": 80,
        "budget_fit": {"under_50": 45, "50_100": 85, "100_200": 90, "over_200": 80},
    },
    "fullframe": {
        "label": "풀프레임 미러리스",
        "portability": 42,
        "low_light": 95,
        "sharpness": 93,
        "video": 86,
        "budget_fit": {"under_50": 20, "50_100": 45, "100_200": 80, "over_200": 95},
    },
}

SKILL_LABEL = {"beginner": "입문자", "hobby": "취미", "intermediate": "중급"}

# 목적별 렌즈 가이드 (전체 표)
LENS_GUIDE = {
    "인물": "50mm / 85mm 계열 단렌즈",
    "여행": "표준 줌 렌즈 (예: 18-50mm)",
    "풍경": "광각 줌 렌즈",
    "야경": "밝은 단렌즈 (F1.8 이하)",
    "브이로그": "광각 줌 + 손떨림 보정",
    "스포츠": "망원 줌 렌즈",
}


def _clamp(value: int) -> int:
    return max(0, min(100, int(round(value))))


def recommend(req: RecommendationRequest) -> RecommendationResponse:
    # 입력에서 가중치 도출 (1~5 → 0~1, 영상은 0~100 → 0~1)
    w_port = req.portability / 5.0
    w_low = req.low_light / 5.0
    w_video = req.video_ratio / 100.0
    # 선명성은 목적 기반 + 기본 가중
    w_sharp = 0.6
    if "풍경" in req.purposes or "인물" in req.purposes:
        w_sharp += 0.3
    # 저조도 중요 목적이면 저조도 가중 강화
    if "야경" in req.purposes:
        w_low = min(1.0, w_low + 0.3)
    if "인물" in req.purposes:
        w_low = min(1.0, w_low + 0.1)

    best_key = None
    best_match = -1.0
    for key, s in SENSORS.items():
        budget_fit = s["budget_fit"][req.budget]
        # 가중 합산: 사용자가 중요하게 본 항목일수록 해당 센서 특성이 크게 반영
        score = (
            w_port * s["portability"]
            + w_low * s["low_light"]
            + w_sharp * s["sharpness"]
            + w_video * s["video"]
            + 1.2 * budget_fit  # 예산 적합도는 항상 강하게 반영
        )

        # 숙련도/렌즈 교환 의향에 따른 보정
        if req.skill_level == "beginner":
            score += s["portability"] * 0.15      # 입문자는 가벼운 쪽을 우대
            if key == "fullframe":
                score -= 25                        # 입문자에게 풀프레임은 부담
        if req.skill_level == "intermediate" and key in ("apsc", "fullframe"):
            score += 20                            # 중급은 큰 센서 감당 가능

        if not req.lens_exchange:
            # 렌즈 교환 의향이 없으면 고정 렌즈형(컴팩트)을 강하게 우대
            if key == "compact":
                score += 60
            else:
                score -= 30

        # 스포츠/망원은 큰 센서 + AF 가 유리
        if "스포츠" in req.purposes and key in ("apsc", "fullframe"):
            score += 15

        # 정규화 (대략적인 0~100 스케일로)
        norm = score / (w_port + w_low + w_sharp + w_video + 1.2 + 0.3)
        if norm > best_match:
            best_match = norm
            best_key = key

    sensor = SENSORS[best_key]

    # 표시용 세부 점수: 센서 기본 특성에 사용자 가중을 살짝 반영
    scores = ScoreBreakdown(
        match=_clamp(best_match),
        sharpness=_clamp(sensor["sharpness"] + (10 if w_sharp > 0.8 else 0)),
        portability=_clamp(sensor["portability"]),
        low_light=_clamp(sensor["low_light"] + (5 if w_low > 0.8 else 0)),
        video=_clamp(sensor["video"] + int(w_video * 8)),
        budget=_clamp(sensor["budget_fit"][req.budget]),
    )

    lens, headline = _build_lens_and_headline(req, best_key, sensor)
    reason = _build_reason(req, best_key, sensor)

    # 사용자가 고른 목적 위주로 렌즈 가이드 구성 (없으면 전체)
    selected = req.purposes if req.purposes else list(LENS_GUIDE.keys())
    lens_guide = [
        LensGuideItem(purpose=p, lens=LENS_GUIDE[p])
        for p in selected
        if p in LENS_GUIDE
    ]

    notice = (
        "이 추천은 입문자용 가이드이며, 실제 구매 전 가격과 "
        "마운트 호환성을 반드시 확인하세요."
    )

    return RecommendationResponse(
        sensor=sensor["label"],
        lens=lens,
        headline=headline,
        scores=scores,
        reason=reason,
        lens_guide=lens_guide,
        notice=notice,
    )


def _build_lens_and_headline(req, key, sensor):
    purposes = req.purposes
    # 대표 렌즈 한 가지 (가장 우선순위 높은 목적 기준)
    priority = ["스포츠", "야경", "인물", "풍경", "브이로그", "여행"]
    primary = next((p for p in priority if p in purposes), "여행")

    if not req.lens_exchange:
        lens = "고정 렌즈 (줌 일체형) — 렌즈 교환 없이 바로 사용"
    else:
        base = LENS_GUIDE.get(primary, "표준 줌 렌즈")
        # 입문자에게는 표준 줌 + 단렌즈 조합을 기본으로 제안
        if req.skill_level == "beginner":
            lens = f"표준 줌 렌즈 + {LENS_GUIDE.get('인물')}"
        else:
            lens = base

    skill = SKILL_LABEL.get(req.skill_level, "입문자")
    headline = f"{sensor['label']} + ({lens}) 조합 추천 — {skill}, {primary} 촬영에 적합"
    return lens, headline


def _build_reason(req, key, sensor):
    parts = []
    budget_text = {
        "under_50": "50만 원 이하",
        "50_100": "50~100만 원",
        "100_200": "100~200만 원",
        "over_200": "200만 원 이상",
    }[req.budget]

    if key == "compact":
        parts.append(f"예산({budget_text})과 높은 휴대성 선호를 고려하면 "
                     "컴팩트/스마트폰 카메라가 부담이 가장 적습니다.")
    elif key == "m43":
        parts.append(f"예산({budget_text}) 대비 휴대성과 영상 성능의 균형이 좋은 "
                     "마이크로 포서드가 적합합니다.")
    elif key == "apsc":
        parts.append(f"예산({budget_text})과 입문 난이도를 고려하면 풀프레임보다 "
                     "APS-C가 가성비와 화질의 균형에서 적합합니다.")
    else:
        parts.append(f"저조도 성능과 화질을 중시하고 예산({budget_text})이 충분하므로 "
                     "풀프레임이 적합합니다.")

    if req.low_light >= 4:
        parts.append("저조도 중요도가 높아 센서 크기를 우선 고려했습니다.")
    if req.portability >= 4:
        parts.append("휴대성 중요도가 높아 가벼운 구성을 우대했습니다.")
    if req.video_ratio >= 50:
        parts.append("영상 비중이 높아 손떨림 보정과 영상 성능에 가중치를 뒀습니다.")
    if not req.lens_exchange:
        parts.append("렌즈 교환 의향이 없어 고정 렌즈형 구성을 추천했습니다.")

    return " ".join(parts)
