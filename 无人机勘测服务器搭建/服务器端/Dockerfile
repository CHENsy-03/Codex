# V2.0 无人机勘测服务器 Docker 镜像
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir duckdb pyyaml protobuf psutil
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null; exit 0
COPY . .
RUN mkdir -p data/temp data/backups
EXPOSE 9000 8080
ENV PYTHONUNBUFFERED=1
CMD ["python", "main.py"]
