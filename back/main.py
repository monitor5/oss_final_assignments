from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from models import (
    RecommendationRequest,
    RecommendationResponse,
    SaveRequest,
    SaveResponse,
    LoadRequest,
    LoadResponse,
    RestoreRequest,
)
from recommender import recommend
import storage

# 서버 시작 시 storage.json 을 준비한다 (없으면 생성, 있으면 기존 데이터 유지)
storage.init_store()

app = FastAPI(title="Camera Match API", description="입문자용 카메라 센서·렌즈 추천 API")

# Streamlit(다른 컨테이너/호스트)에서 호출하므로 CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 강의자료(08) 흐름대로 APIRouter 를 사용해 라우트를 구성한다.
camera_router = APIRouter()


@app.get("/")
async def welcome() -> dict:
    return {"msg": "Camera Match API is running"}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# POST 요청을 Pydantic 모델(RecommendationRequest)로 검증해서 받고,
# 추천 결과를 JSON(RecommendationResponse)으로 반환한다.
@camera_router.post("/recommend", response_model=RecommendationResponse)
async def recommend_camera(req: RecommendationRequest) -> RecommendationResponse:
    return recommend(req)


# 추천 결과를 (이름, 패스워드)로 저장
@camera_router.post("/save", response_model=SaveResponse)
async def save_result(req: SaveRequest) -> SaveResponse:
    try:
        count = storage.save_record(
            req.name,
            req.password,
            {"inputs": req.inputs, "result": req.result.model_dump()},
        )
    except storage.AuthError:
        raise HTTPException(status_code=401, detail="이름은 있지만 패스워드가 일치하지 않습니다.")
    return SaveResponse(msg="saved", count=count)


# (이름, 패스워드)로 저장된 결과 불러오기
@camera_router.post("/load", response_model=LoadResponse)
async def load_results(req: LoadRequest) -> LoadResponse:
    try:
        records = storage.load_records(req.name, req.password)
    except storage.AuthError:
        raise HTTPException(status_code=401, detail="패스워드가 일치하지 않습니다.")
    return LoadResponse(records=records)


# JSON 백업 파일의 기록들을 (이름, 패스워드) 사용자에게 복원(추가)
@camera_router.post("/restore", response_model=SaveResponse)
async def restore_results(req: RestoreRequest) -> SaveResponse:
    try:
        count = storage.restore_records(
            req.name,
            req.password,
            [r.model_dump() for r in req.records],
        )
    except storage.AuthError:
        raise HTTPException(status_code=401, detail="이름은 있지만 패스워드가 일치하지 않습니다.")
    return SaveResponse(msg="restored", count=count)


app.include_router(camera_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
