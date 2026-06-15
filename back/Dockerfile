# Docker 강의자료(10)의 Dockerfile 기본 흐름:
# FROM(베이스) → WORKDIR(작업폴더) → COPY(파일이동) → RUN(종속성 설치)
# → EXPOSE(포트 오픈) → CMD(컨테이너 시작 명령)
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# FastAPI 내부 포트
EXPOSE 8000

# uvicorn 으로 FastAPI 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
