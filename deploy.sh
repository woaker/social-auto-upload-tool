#!/bin/bash

# Social Auto Upload 自动部署脚本
# 适用于 Ubuntu 20.04+ 系统

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "检测到以root用户运行，建议使用普通用户并配置sudo权限"
        read -p "是否继续？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 更新系统
update_system() {
    log_info "更新系统包..."
    sudo apt update && sudo apt upgrade -y
    log_success "系统更新完成"
}

# 安装基础软件
install_dependencies() {
    log_info "安装基础依赖..."
    
    # 安装基础工具
    sudo apt install -y curl wget git vim htop tree
    
    # 安装Python环境
    sudo apt install -y python3 python3-pip python3-venv python3-dev
    
    # 安装Node.js
    log_info "安装Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
    sudo apt-get install -y nodejs
    
    # 安装系统服务
    sudo apt install -y nginx supervisor ufw sqlite3
    
    # 安装Chrome（用于自动化操作）
    if ! command -v google-chrome &> /dev/null; then
        log_info "安装Google Chrome..."
        wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
        echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
        sudo apt update
        sudo apt install -y google-chrome-stable
    fi
    
    log_success "依赖安装完成"
}

# 设置项目目录
setup_project() {
    log_info "设置项目目录..."
    
    PROJECT_DIR="/var/www/social-auto-upload"
    
    # 创建项目目录
    sudo mkdir -p /var/www
    
    # 如果目录已存在，备份
    if [ -d "$PROJECT_DIR" ]; then
        log_warning "项目目录已存在，创建备份..."
        sudo mv "$PROJECT_DIR" "${PROJECT_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # 克隆项目
    if [ -z "$REPO_URL" ]; then
        log_error "请设置环境变量 REPO_URL 为你的项目仓库地址"
        log_info "例如: export REPO_URL=https://github.com/your-username/social-auto-upload.git"
        exit 1
    fi
    
    sudo git clone "$REPO_URL" "$PROJECT_DIR"
    
    # 设置权限
    sudo chown -R $USER:$USER "$PROJECT_DIR"
    
    log_success "项目目录设置完成"
}

# 配置Python环境
setup_python_env() {
    log_info "配置Python虚拟环境..."
    
    cd "$PROJECT_DIR"
    
    # 创建虚拟环境
    python3 -m venv venv
    
    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # 创建配置文件
    if [ ! -f "conf.py" ]; then
        cp conf.example.py conf.py
        log_info "已创建配置文件 conf.py，请根据需要修改"
    fi
    
    # 初始化数据库
    cd db
    python3 createTable.py
    cd ..
    
    log_success "Python环境配置完成"
}

# 配置前端环境
setup_frontend() {
    log_info "配置前端环境..."
    
    cd "$PROJECT_DIR/sau_frontend"
    
    # 安装依赖
    npm install
    
    # 构建生产版本
    npm run build
    
    cd ..
    
    log_success "前端环境配置完成"
}

# 配置系统服务
setup_services() {
    log_info "配置系统服务..."
    
    # 配置Supervisor
    sudo tee /etc/supervisor/conf.d/sau-backend.conf > /dev/null <<EOF
[program:sau-backend]
command=$PROJECT_DIR/venv/bin/python sau_backend.py
directory=$PROJECT_DIR
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/sau-backend.log
environment=PATH="$PROJECT_DIR/venv/bin"
EOF
    
    # 设置正确的权限
    sudo chown -R www-data:www-data "$PROJECT_DIR"
    sudo chmod +x "$PROJECT_DIR"/*.sh
    
    # 创建必要的目录
    sudo mkdir -p "$PROJECT_DIR/videoFile"
    sudo mkdir -p "$PROJECT_DIR/logs"
    sudo chown -R www-data:www-data "$PROJECT_DIR/videoFile"
    sudo chown -R www-data:www-data "$PROJECT_DIR/logs"
    
    # 重启Supervisor
    sudo supervisorctl reread
    sudo supervisorctl update
    sudo supervisorctl start sau-backend
    
    log_success "系统服务配置完成"
}

# 配置Nginx
setup_nginx() {
    log_info "配置Nginx..."
    
    # 获取域名或IP
    if [ -z "$DOMAIN" ]; then
        DOMAIN=$(curl -s http://checkip.amazonaws.com/)
        log_info "未设置域名，将使用服务器IP: $DOMAIN"
    fi
    
    # 创建Nginx配置
    sudo tee /etc/nginx/sites-available/social-auto-upload > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    # 前端静态文件
    location / {
        root $PROJECT_DIR/sau_frontend/dist;
        try_files \$uri \$uri/ /index.html;
        index index.html;
    }

    # API 代理到后端
    location /api/ {
        proxy_pass http://127.0.0.1:5409/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # SSE 特殊配置
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }

    # 直接代理后端所有路由
    location ~ ^/(upload|getFile|uploadSave|getFiles|getValidAccounts|deleteFile|deleteAccount|login|postVideo|updateUserinfo|postVideoBatch) {
        proxy_pass http://127.0.0.1:5409;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        client_max_body_size 200M;
        
        # SSE 特殊配置
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }

    # 静态资源缓存
    location /assets/ {
        root $PROJECT_DIR/sau_frontend/dist;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF
    
    # 启用站点
    sudo ln -sf /etc/nginx/sites-available/social-auto-upload /etc/nginx/sites-enabled/
    
    # 删除默认站点（如果存在）
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # 测试配置
    sudo nginx -t
    
    # 重启Nginx
    sudo systemctl reload nginx
    
    log_success "Nginx配置完成"
}

# 配置防火墙
setup_firewall() {
    log_info "配置防火墙..."
    
    # 配置UFW
    sudo ufw --force reset
    sudo ufw allow 22/tcp
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw --force enable
    
    log_success "防火墙配置完成"
}

# 创建维护脚本
create_maintenance_scripts() {
    log_info "创建维护脚本..."
    
    # 创建监控脚本
    sudo tee "$PROJECT_DIR/monitor.sh" > /dev/null <<'EOF'
#!/bin/bash

# 检查服务状态
check_service() {
    service_name=$1
    if systemctl is-active --quiet $service_name; then
        echo "✅ $service_name is running"
    else
        echo "❌ $service_name is not running"
        sudo systemctl restart $service_name
    fi
}

# 检查端口
check_port() {
    port=$1
    service_name=$2
    if netstat -tlnp | grep ":$port " > /dev/null; then
        echo "✅ Port $port ($service_name) is open"
    else
        echo "❌ Port $port ($service_name) is not accessible"
    fi
}

echo "=== System Monitor $(date) ==="
echo ""

# 检查系统资源
echo "Memory Usage:"
free -h
echo ""

echo "Disk Usage:"
df -h /
echo ""

# 检查服务状态
echo "=== Service Status ==="
check_service nginx
check_service supervisor

echo ""
echo "=== Port Status ==="
check_port 80 "HTTP"
check_port 5409 "Backend API"

echo ""
echo "=== Backend Process ==="
sudo supervisorctl status sau-backend
EOF
    
    # 创建备份脚本
    sudo tee "$PROJECT_DIR/backup.sh" > /dev/null <<EOF
#!/bin/bash
BACKUP_DIR="/var/backups/social-auto-upload"
DATE=\$(date +%Y%m%d_%H%M%S)
DB_FILE="$PROJECT_DIR/db/database.db"

sudo mkdir -p \$BACKUP_DIR
sudo cp \$DB_FILE "\$BACKUP_DIR/database_\$DATE.db"

# 只保留最近30天的备份
sudo find \$BACKUP_DIR -name "database_*.db" -mtime +30 -delete

echo "✅ Database backup completed: \$BACKUP_DIR/database_\$DATE.db"
EOF
    
    # 设置执行权限
    sudo chmod +x "$PROJECT_DIR/monitor.sh"
    sudo chmod +x "$PROJECT_DIR/backup.sh"
    
    log_success "维护脚本创建完成"
}

# 设置定时任务
setup_cron() {
    log_info "设置定时任务..."
    
    # 创建cron任务文件
    cat > /tmp/social-auto-upload-cron <<EOF
# 每天凌晨2点备份数据库
0 2 * * * $PROJECT_DIR/backup.sh >> /var/log/sau-backup.log 2>&1

# 每小时检查系统状态
0 * * * * $PROJECT_DIR/monitor.sh >> /var/log/sau-monitor.log 2>&1
EOF
    
    # 安装cron任务
    sudo crontab /tmp/social-auto-upload-cron
    rm /tmp/social-auto-upload-cron
    
    log_success "定时任务设置完成"
}

# 验证部署
verify_deployment() {
    log_info "验证部署状态..."
    
    # 检查服务状态
    if sudo supervisorctl status sau-backend | grep -q "RUNNING"; then
        log_success "后端服务运行正常"
    else
        log_error "后端服务未运行"
        sudo supervisorctl status sau-backend
    fi
    
    # 检查Nginx状态
    if systemctl is-active --quiet nginx; then
        log_success "Nginx服务运行正常"
    else
        log_error "Nginx服务未运行"
    fi
    
    # 检查端口
    if netstat -tlnp | grep -q ":80 "; then
        log_success "HTTP端口(80)已开放"
    else
        log_error "HTTP端口(80)未开放"
    fi
    
    if netstat -tlnp | grep -q ":5409 "; then
        log_success "后端API端口(5409)已开放"
    else
        log_error "后端API端口(5409)未开放"
    fi
    
    log_success "部署验证完成"
}

# 显示部署结果
show_result() {
    echo ""
    log_success "🎉 部署完成！"
    echo ""
    echo "访问信息："
    echo "  前端地址: http://$DOMAIN"
    echo "  后端API: http://$DOMAIN/api/"
    echo ""
    echo "管理命令："
    echo "  查看后端状态: sudo supervisorctl status sau-backend"
    echo "  重启后端服务: sudo supervisorctl restart sau-backend"
    echo "  查看后端日志: sudo tail -f /var/log/sau-backend.log"
    echo "  重启Nginx: sudo systemctl reload nginx"
    echo "  系统监控: $PROJECT_DIR/monitor.sh"
    echo "  数据库备份: $PROJECT_DIR/backup.sh"
    echo ""
    echo "如需配置HTTPS，请运行："
    echo "  sudo apt install certbot python3-certbot-nginx -y"
    echo "  sudo certbot --nginx -d $DOMAIN"
    echo ""
}

# 主函数
main() {
    echo "🚀 开始部署 Social Auto Upload 项目"
    echo ""
    
    # 检查环境变量
    if [ -z "$REPO_URL" ]; then
        log_error "请先设置项目仓库地址："
        echo "export REPO_URL=https://github.com/your-username/social-auto-upload.git"
        echo "然后重新运行此脚本"
        exit 1
    fi
    
    check_root
    update_system
    install_dependencies
    setup_project
    setup_python_env
    setup_frontend
    setup_services
    setup_nginx
    setup_firewall
    create_maintenance_scripts
    setup_cron
    verify_deployment
    show_result
}

# 运行主函数
main "$@" 