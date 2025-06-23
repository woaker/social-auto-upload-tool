# Docker 部署说明

## 🐳 Docker 部署优势

- **环境一致性**: 确保开发、测试、生产环境完全一致
- **快速部署**: 一键启动所有服务
- **资源隔离**: 容器间相互独立，避免依赖冲突
- **易于扩展**: 可以轻松进行水平扩展
- **便于维护**: 容器化管理，版本控制更简单

## 🚀 Docker 部署步骤

### 1. 安装 Docker 和 Docker Compose

#### Ubuntu/Debian
```bash
# 更新系统包
sudo apt update

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 添加用户到 docker 组
sudo usermod -aG docker $USER

# 重新登录或执行
newgrp docker
```

#### CentOS/RHEL
```bash
# 安装 Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 准备项目文件

```bash
# 克隆项目
git clone https://github.com/your-username/social-auto-upload.git
cd social-auto-upload

# 确保所有必要文件存在
ls -la Dockerfile docker-compose.yml nginx.conf
```

### 3. 构建和启动服务

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 4. 验证部署

```bash
# 检查容器状态
docker ps

# 测试服务
curl http://localhost/health
curl http://localhost

# 查看后端日志
docker-compose logs social-auto-upload

# 查看 Nginx 日志
docker-compose logs nginx
```

## 🛠️ 管理命令

### 基础操作
```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f [service_name]
```

### 更新部署
```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build

# 或者单独重新构建某个服务
docker-compose build social-auto-upload
docker-compose up -d social-auto-upload
```

### 数据管理
```bash
# 查看数据卷
docker volume ls

# 备份数据库
docker-compose exec social-auto-upload cp /app/db/database.db /app/db/database.backup.db

# 进入容器
docker-compose exec social-auto-upload bash

# 查看容器内文件
docker-compose exec social-auto-upload ls -la /app
```

## 🔧 配置自定义

### 1. 环境变量配置

创建 `.env` 文件：
```bash
# 服务端口
HOST_PORT=80
BACKEND_PORT=5409

# 数据库配置
DB_PATH=./db/database.db

# 日志级别
LOG_LEVEL=INFO

# 文件上传大小限制 (MB)
MAX_UPLOAD_SIZE=200
```

更新 `docker-compose.yml`：
```yaml
version: '3.8'

services:
  social-auto-upload:
    build: .
    ports:
      - "${BACKEND_PORT}:5409"
    environment:
      - LOG_LEVEL=${LOG_LEVEL}
      - MAX_UPLOAD_SIZE=${MAX_UPLOAD_SIZE}
    # ... 其他配置
```

### 2. 持久化存储

确保重要数据持久化：
```yaml
volumes:
  - ./db:/app/db              # 数据库文件
  - ./videoFile:/app/videoFile # 上传的视频文件
  - ./logs:/app/logs          # 日志文件
```

### 3. 网络配置

如果需要自定义网络：
```yaml
networks:
  sau-network:
    driver: bridge

services:
  social-auto-upload:
    networks:
      - sau-network
```

## 🔒 生产环境配置

### 1. HTTPS 配置

添加 SSL 证书支持：
```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/conf.d/default.conf
    - ./ssl:/etc/nginx/ssl
  environment:
    - SSL_CERT_PATH=/etc/nginx/ssl/cert.pem
    - SSL_KEY_PATH=/etc/nginx/ssl/key.pem
```

### 2. 资源限制

为容器设置资源限制：
```yaml
services:
  social-auto-upload:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 3. 健康检查

添加健康检查：
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5409/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

## 📊 监控和日志

### 1. 日志管理

```bash
# 实时查看所有日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f social-auto-upload

# 查看最近 100 行日志
docker-compose logs --tail=100 social-auto-upload

# 日志轮转配置
docker run --log-driver json-file --log-opt max-size=10m --log-opt max-file=3
```

### 2. 性能监控

使用 Docker stats 监控资源使用：
```bash
# 查看容器资源使用情况
docker stats

# 查看特定容器
docker stats social-auto-upload
```

### 3. 集成监控工具

可以集成 Prometheus + Grafana：
```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

## 🆘 故障排查

### 常见问题

1. **容器无法启动**
```bash
# 查看容器日志
docker-compose logs social-auto-upload

# 检查 Dockerfile 语法
docker build -t test .
```

2. **端口冲突**
```bash
# 查看端口占用
netstat -tulpn | grep :80

# 修改端口映射
docker-compose down
# 编辑 docker-compose.yml 修改端口
docker-compose up -d
```

3. **数据丢失**
```bash
# 检查数据卷挂载
docker-compose exec social-auto-upload ls -la /app/db

# 恢复备份
docker-compose exec social-auto-upload cp /app/db/database.backup.db /app/db/database.db
```

4. **网络问题**
```bash
# 检查容器网络
docker network ls
docker inspect social-auto-upload_default

# 重启网络
docker-compose down
docker-compose up -d
```

## 🎯 最佳实践

1. **使用 .dockerignore**
```
node_modules
*.log
.git
.env
```

2. **多阶段构建优化**
```dockerfile
# 构建阶段
FROM node:16 as frontend-builder
WORKDIR /app
COPY sau_frontend/package*.json ./
RUN npm install
COPY sau_frontend/ .
RUN npm run build

# 运行阶段
FROM python:3.9-slim
WORKDIR /app
COPY --from=frontend-builder /app/dist ./sau_frontend/dist
# ... 其他配置
```

3. **环境分离**
```bash
# 开发环境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 生产环境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
```

## 🔄 自动化部署

### 使用脚本自动化

创建 `deploy-docker.sh`：
```bash
#!/bin/bash
set -e

echo "🚀 开始 Docker 部署..."

# 拉取最新代码
git pull

# 停止现有服务
docker-compose down

# 构建新镜像
docker-compose build --no-cache

# 启动服务
docker-compose up -d

# 等待服务启动
sleep 10

# 验证部署
if curl -f http://localhost/health; then
    echo "✅ 部署成功！"
else
    echo "❌ 部署失败！"
    docker-compose logs
    exit 1
fi
```

### CI/CD 集成

可以集成到 GitHub Actions、GitLab CI 等：
```yaml
# .github/workflows/deploy.yml
name: Deploy to Server

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Deploy to server
      uses: appleboy/ssh-action@v0.1.4
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /var/www/social-auto-upload
          ./deploy-docker.sh
```

---

**Docker 部署完成后访问：**
- 应用地址: `http://server-ip:80`
- 健康检查: `http://server-ip:80/health` 