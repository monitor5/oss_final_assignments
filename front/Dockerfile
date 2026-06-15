# Docker 강의자료(10)의 Dockerfile 기본 흐름에 맞춰 작성
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Streamlit 기본 포트
EXPOSE 8501

# Streamlit 실행 (외부 접속 허용을 위해 0.0.0.0 바인딩)
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
