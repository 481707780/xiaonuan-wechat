# ============================================================
# 小暖 - Docker 部署（含风格数据）
# ============================================================
FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY data/ ./data/
COPY run.py .

# 数据目录权限
RUN chmod -R 755 /app/data

# 暴露端口
EXPOSE 8000

# 启动
CMD ["python", "run.py"]
