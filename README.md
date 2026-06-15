# 📷 Camera Match — 입문자를 위한 카메라 센서·렌즈 조합 추천기

2023204020 정보융합학부 김우현

오픈소스소프트웨어실습 기말 대체 과제.
**Streamlit(프론트) + FastAPI(백엔드) + Docker + AWS EC2** 로 구성된 추천 웹 애플리케이션입니다.

사용자가 예산·촬영 목적·휴대성·저조도·영상 비중·숙련도·렌즈 교환 의향을 입력하면,
FastAPI 백엔드가 규칙 기반(rule-based)으로 점수를 계산해 적합한 **센서 타입과 렌즈 조합**을 추천합니다.

> 이 서비스는 입문자용 선택 가이드이며, 실제 카메라 모델을 정확히 맞히는 서비스가 아닙니다.

---

## 동작 흐름

```
사용자 입력 → Streamlit → (HTTP POST) → FastAPI 추천 처리 → JSON 응답 → Streamlit 화면 표시
```

- **Streamlit (front)** : 사용자 입력 받기 / 추천 요청 버튼 / 결과 출력 (추천 계산은 하지 않음)
- **FastAPI (back)** : 입력값 검증(Pydantic) / 추천 로직 실행 / JSON 응답 반환
- **Docker** : front, back 을 각각 별도 컨테이너로 실행
- **AWS EC2** : 실제 배포 환경

---

## 프로젝트 구조

```
.
├── front/                 # Streamlit 프론트엔드
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
├── back/                  # FastAPI 백엔드
│   ├── main.py            # FastAPI 앱 + 라우터 + uvicorn
│   ├── models.py          # Pydantic 요청/응답 모델
│   ├── recommender.py     # 규칙 기반 추천 로직
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
├── docker-compose.yml     # front(8501) + back(8000) 동시 실행
├── docx/                  # 과제/강의/대본 참고 문서 (gitignore)
├── .gitignore
└── README.md
```

---

## 입력 항목 / 추천 결과

| 입력 | UI | 예시 값 |
|------|-----|--------|
| 예산 | selectbox | 50만 이하 / 50~100만 / 100~200만 / 200만 이상 |
| 주 촬영 목적 | multiselect | 여행, 인물, 풍경, 야경, 브이로그, 스포츠 |
| 휴대성 중요도 | slider | 1~5 |
| 저조도 중요도 | slider | 1~5 |
| 영상 촬영 비중 | slider | 0~100% |
| 사용자 숙련도 | radio | 입문자 / 취미 / 중급 |
| 렌즈 교환 의향 | radio | 있음 / 없음 |

추천 결과: **추천 센서**, **추천 렌즈 조합**, 점수(궁합도·선명성·휴대성·저조도·영상·예산 적합도),
**추천 이유**, **목적별 렌즈 가이드**, **주의 문구**.

---

## API 명세 (FastAPI)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/` | 동작 확인 |
| GET | `/health` | 상태 확인 |
| POST | `/recommend` | 추천 결과(JSON) 반환 |
| GET | `/docs` | Swagger 자동 문서 |

요청 예시:

```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"budget":"50_100","purposes":["여행","인물"],"portability":3,"low_light":3,"video_ratio":20,"skill_level":"beginner","lens_exchange":true}'
```

---

## 로컬 실행 (Docker Compose 권장)

```bash
docker compose up --build
```

- Streamlit : http://localhost:8501
- FastAPI 문서 : http://localhost:8000/docs

종료:

```bash
docker compose down
```

### Docker 없이 실행 (개발용)

```bash
# 1) 백엔드
cd back
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py            # http://localhost:8000

# 2) 프론트 (새 터미널)
cd front
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export BACKEND_URL=http://localhost:8000
streamlit run app.py      # http://localhost:8501
```

---


### 1) 보안 그룹(방화벽) 포트 오픈

인바운드 규칙에 아래 포트를 추가합니다.

- **8501** (Streamlit, 외부 접속용)
- **8000** (FastAPI, 확인/문서용)

### 2) EC2 접속 후 Docker 설치 확인

```bash
sudo docker version
sudo docker compose version
```

### 3) 코드 가져오기 (GitHub clone)

```bash
git clone <이-저장소-주소>
cd <repo-folder>
```

### 4) 컨테이너 빌드 & 실행

```bash
sudo docker compose up --build -d
```

### 5) 실행 상태 확인

```bash
sudo docker ps          # camera_front, camera_back 컨테이너 확인
sudo docker logs camera_back   # FastAPI 로그
```

