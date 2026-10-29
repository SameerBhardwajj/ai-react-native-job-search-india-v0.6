FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV WEB_HOST=127.0.0.1
CMD ["uvicorn","rnjob.web:app","--host","127.0.0.1","--port","8000"]