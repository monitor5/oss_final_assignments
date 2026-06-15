from typing import List, Literal
from pydantic import BaseModel, Field

Budget = Literal["under_50", "50_100", "100_200", "over_200"]
Purpose = Literal["여행", "인물", "풍경", "야경", "브이로그", "스포츠"]
SkillLevel = Literal["beginner", "hobby", "intermediate"]


# FastAPI 강의자료(08)의 흐름대로, 클라이언트가 보내는 입력은
# 미리 정의된 Pydantic 모델로만 받아 검증한다.
class RecommendationRequest(BaseModel):
    budget: Budget = Field(..., description="예산 구간")
    purposes: List[Purpose] = Field(default_factory=list, description="주 촬영 목적")
    # 휴대성 중요도 (1~5)
    portability: int = Field(..., ge=1, le=5, description="휴대성 중요도")
    # 저조도 중요도 (1~5)
    low_light: int = Field(..., ge=1, le=5, description="저조도 중요도")
    # 영상 촬영 비중 (0~100 %)
    video_ratio: int = Field(..., ge=0, le=100, description="영상 촬영 비중(%)")
    skill_level: SkillLevel = Field(..., description="사용자 숙련도")
    # 렌즈 교환 의향: True / False
    lens_exchange: bool = Field(..., description="렌즈 교환 의향")


class ScoreBreakdown(BaseModel):
    match: int          # 궁합도
    sharpness: int      # 예상 선명성
    portability: int    # 휴대성
    low_light: int      # 저조도 적합도
    video: int          # 영상 적합도
    budget: int         # 예산 적합도


class LensGuideItem(BaseModel):
    purpose: str
    lens: str


# 추천 결과 응답 모델 (JSON 으로 반환됨)
class RecommendationResponse(BaseModel):
    sensor: str                       # 추천 센서
    lens: str                         # 추천 렌즈 조합
    headline: str                     # 최종 추천 카드 문구
    scores: ScoreBreakdown            # 점수 시각화용
    reason: str                       # 추천 이유
    lens_guide: List[LensGuideItem]   # 목적별 렌즈 가이드
    notice: str                       # 주의 문구


# --- 결과 저장 / 불러오기 ---------------------------------------------------

class SaveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=30, description="사용자 이름")
    password: str = Field(..., min_length=1, max_length=50, description="패스워드")
    # 저장 시점의 입력 요약과 추천 결과를 함께 보관 (그대로 다시 보여주기 위함)
    inputs: dict = Field(default_factory=dict, description="입력 요약")
    result: RecommendationResponse = Field(..., description="추천 결과")


class SaveResponse(BaseModel):
    msg: str
    count: int           # 해당 사용자의 누적 저장 개수


class LoadRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=30, description="사용자 이름")
    password: str = Field(..., min_length=1, max_length=50, description="패스워드")


class SavedRecord(BaseModel):
    saved_at: str
    inputs: dict
    result: RecommendationResponse


class LoadResponse(BaseModel):
    records: List[SavedRecord]


class RestoreRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=30, description="사용자 이름")
    password: str = Field(..., min_length=1, max_length=50, description="패스워드")
    # JSON 백업 파일에서 읽어온 기록 목록
    records: List[SavedRecord] = Field(..., description="복원할 기록 목록")
