# 多阶段构建：阶段 1 构建前端 dist，阶段 2 Python 后端伺服

# 阶段 1: 构建前端（Vite 产物）
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 阶段 2: Python 后端
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 先复制依赖文件，利用 Docker 层缓存
# 只要 requirements.txt 没变，这一层不会重新构建
COPY requirements.txt .

# 安装依赖（--no-cache-dir 减小镜像体积）
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目代码
COPY . .

# 复制前端构建产物（app.py 在 frontend/dist 存在时自动挂载伺服）
COPY --from=frontend /app/frontend/dist ./frontend/dist

# 创建运行时需要的目录
RUN mkdir -p workspace/memory workspace/outputs workspace/skills

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "app.py"]
