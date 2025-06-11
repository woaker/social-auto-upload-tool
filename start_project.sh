#!/bin/bash

# Social Auto Upload 项目启动脚本
# 同时启动 Python 后端和 Vue 前端服务

# 项目根目录
PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BACKEND_DIR="$PROJECT_ROOT"
FRONTEND_DIR="$PROJECT_ROOT/sau_frontend"

# 日志目录
LOG_DIR="$PROJECT_ROOT/logs"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
PID_DIR="$PROJECT_ROOT/.pids"

# 创建必要的目录
mkdir -p "$LOG_DIR" "$PID_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 输出带颜色的消息
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

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 0  # 端口被占用
    else
        return 1  # 端口空闲
    fi
}

# 启动后端服务
start_backend() {
    log_info "正在启动 Python 后端服务..."
    
    # 检查 5409 端口
    if check_port 5409; then
        log_warning "端口 5409 已被占用，尝试停止现有服务..."
        pkill -f "sau_backend.py" 2>/dev/null || true
        sleep 2
    fi
    
    cd "$BACKEND_DIR"
    
    # 启动后端服务
    nohup python sau_backend.py > "$BACKEND_LOG" 2>&1 &
    local backend_pid=$!
    echo $backend_pid > "$PID_DIR/backend.pid"
    
    # 等待服务启动
    sleep 3
    
    # 检查服务是否启动成功
    if check_port 5409; then
        log_success "后端服务启动成功 (PID: $backend_pid, Port: 5409)"
        log_info "后端日志: $BACKEND_LOG"
    else
        log_error "后端服务启动失败，请检查日志: $BACKEND_LOG"
        return 1
    fi
}

# 启动前端服务
start_frontend() {
    log_info "正在启动 Vue 前端服务..."
    
    # 检查 5173 端口
    if check_port 5173; then
        log_warning "端口 5173 已被占用，尝试停止现有服务..."
        pkill -f "vite" 2>/dev/null || true
        sleep 2
    fi
    
    cd "$FRONTEND_DIR"
    
    # 检查是否安装了依赖
    if [ ! -d "node_modules" ]; then
        log_info "正在安装前端依赖..."
        npm install
    fi
    
    # 启动前端服务
    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
    local frontend_pid=$!
    echo $frontend_pid > "$PID_DIR/frontend.pid"
    
    # 等待服务启动
    sleep 5
    
    # 检查服务是否启动成功
    if check_port 5173; then
        log_success "前端服务启动成功 (PID: $frontend_pid, Port: 5173)"
        log_info "前端日志: $FRONTEND_LOG"
    else
        log_error "前端服务启动失败，请检查日志: $FRONTEND_LOG"
        return 1
    fi
}

# 停止服务
stop_services() {
    log_info "正在停止所有服务..."
    
    # 停止后端
    if [ -f "$PID_DIR/backend.pid" ]; then
        local backend_pid=$(cat "$PID_DIR/backend.pid")
        if kill -0 "$backend_pid" 2>/dev/null; then
            kill "$backend_pid"
            log_success "后端服务已停止 (PID: $backend_pid)"
        fi
        rm -f "$PID_DIR/backend.pid"
    fi
    
    # 停止前端
    if [ -f "$PID_DIR/frontend.pid" ]; then
        local frontend_pid=$(cat "$PID_DIR/frontend.pid")
        if kill -0 "$frontend_pid" 2>/dev/null; then
            kill "$frontend_pid"
            log_success "前端服务已停止 (PID: $frontend_pid)"
        fi
        rm -f "$PID_DIR/frontend.pid"
    fi
    
    # 强制清理
    pkill -f "sau_backend.py" 2>/dev/null || true
    pkill -f "vite.*sau_frontend" 2>/dev/null || true
    
    log_success "所有服务已停止"
}

# 检查服务状态
check_status() {
    log_info "检查服务状态..."
    
    # 检查后端
    if check_port 5409; then
        log_success "后端服务正在运行 (端口: 5409)"
        curl -s http://localhost:5409/ > /dev/null && log_success "后端 API 响应正常" || log_warning "后端 API 响应异常"
    else
        log_error "后端服务未运行"
    fi
    
    # 检查前端
    if check_port 5173; then
        log_success "前端服务正在运行 (端口: 5173)"
    else
        log_error "前端服务未运行"
    fi
    
    # 显示进程信息
    echo ""
    log_info "相关进程信息:"
    ps aux | grep -E "(sau_backend|vite)" | grep -v grep || echo "没有找到相关进程"
}

# 查看日志
show_logs() {
    local service=$1
    case $service in
        "backend"|"b")
            log_info "后端日志 (最后50行):"
            tail -n 50 "$BACKEND_LOG" 2>/dev/null || log_error "无法读取后端日志"
            ;;
        "frontend"|"f")
            log_info "前端日志 (最后50行):"
            tail -n 50 "$FRONTEND_LOG" 2>/dev/null || log_error "无法读取前端日志"
            ;;
        "all"|"")
            echo "=== 后端日志 ==="
            tail -n 25 "$BACKEND_LOG" 2>/dev/null || log_error "无法读取后端日志"
            echo ""
            echo "=== 前端日志 ==="
            tail -n 25 "$FRONTEND_LOG" 2>/dev/null || log_error "无法读取前端日志"
            ;;
        *)
            log_error "未知的服务: $service"
            echo "使用: $0 logs [backend|frontend|all]"
            ;;
    esac
}

# 重启服务
restart_services() {
    log_info "重启所有服务..."
    stop_services
    sleep 2
    start_backend
    start_frontend
}

# 显示帮助信息
show_help() {
    echo "Social Auto Upload 项目管理脚本"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start          启动所有服务 (默认)"
    echo "  stop           停止所有服务"
    echo "  restart        重启所有服务"
    echo "  status         检查服务状态"
    echo "  logs [service] 查看日志 (backend/frontend/all)"
    echo "  help           显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0              # 启动所有服务"
    echo "  $0 start        # 启动所有服务"
    echo "  $0 stop         # 停止所有服务"
    echo "  $0 status       # 检查状态"
    echo "  $0 logs         # 查看所有日志"
    echo "  $0 logs backend # 查看后端日志"
    echo ""
    echo "服务地址:"
    echo "  后端: http://localhost:5409"
    echo "  前端: http://localhost:5173"
}

# 主逻辑
main() {
    case "${1:-start}" in
        "start")
            log_info "启动 Social Auto Upload 项目..."
            start_backend
            start_frontend
            echo ""
            log_success "项目启动完成！"
            echo ""
            echo "访问地址:"
            echo "  前端管理界面: http://localhost:5173"
            echo "  后端 API: http://localhost:5409"
            echo ""
            echo "常用命令:"
            echo "  查看状态: $0 status"
            echo "  查看日志: $0 logs"
            echo "  停止服务: $0 stop"
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            restart_services
            ;;
        "status")
            check_status
            ;;
        "logs")
            show_logs "$2"
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 检查依赖
check_dependencies() {
    # 检查 Python
    if ! command -v python &> /dev/null; then
        log_error "Python 未安装或不在 PATH 中"
        exit 1
    fi
    
    # 检查 Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js 未安装或不在 PATH 中"
        exit 1
    fi
    
    # 检查 npm
    if ! command -v npm &> /dev/null; then
        log_error "npm 未安装或不在 PATH 中"
        exit 1
    fi
}

# 脚本入口
echo "========================================"
echo "    Social Auto Upload 项目管理工具"
echo "========================================"
echo ""

check_dependencies
main "$@" 