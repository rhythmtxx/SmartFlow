# 基础镜像：Python 3.11 slim（体积小，够用）
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

# 创建运行时需要的目录
RUN mkdir -p workspace/memory workspace/outputs workspace/skills

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "app.py"]
