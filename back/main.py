from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from models import RecommendationRequest, RecommendationResponse
from recommender import recommend

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


app.include_router(camera_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
