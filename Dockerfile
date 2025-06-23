# 使用官方 Python 3.9 镜像作为基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Node.js 18
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# 复制 Python 依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 复制配置文件
RUN cp conf.example.py conf.py

# 初始化数据库
RUN cd db && python createTable.py

# 构建前端
RUN cd sau_frontend && \
    npm install && \
    npm run build

# 创建必要的目录
RUN mkdir -p videoFile logs

# 设置权限
RUN chmod +x *.sh

# 暴露端口
EXPOSE 5409

# 设置环境变量
ENV PYTHONPATH=/app
ENV FLASK_APP=sau_backend.py

# 启动命令
CMD ["python", "sau_backend.py"] 