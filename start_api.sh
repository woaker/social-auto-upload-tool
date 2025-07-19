#!/bin/bash

SERVICE_NAME="api_service"
PID_FILE="api_service.pid"
LOG_FILE="api_service.log"
CMD="python3 api_service.py"

FRP_DIR="frp"
FRPC_CMD="./frp/frpc -c ./frp/frpc.ini"
FRPC_PID_FILE="frpc.pid"
FRPC_LOG_FILE="frpc.log"

# 启动frp内网穿透
start_frp() {
    echo "[FRP] 启动frp内网穿透..."
    if [ ! -d "$FRP_DIR" ]; then
        echo "[FRP] 未找到frp目录，请手动下载并放置到frp/下。"
        return 1
    fi
    if [ ! -f "$FRP_DIR/frpc.ini" ]; then
        echo "[FRP] 自动生成frpc.ini配置文件..."
        cat > $FRP_DIR/frpc.ini << EOF
[common]
server_addr = 54.226.20.77
server_port = 5001
authentication_method = token
token = frp-315bfe284c994403ab2e5178eec44d3c

[toutiao_api]
type = tcp
local_ip = 127.0.0.1
local_port = 8001
remote_port = 5500
EOF
        echo "[FRP] 已创建frp配置文件 $FRP_DIR/frpc.ini"
    fi
    if [ -f "$FRPC_PID_FILE" ] && kill -0 $(cat "$FRPC_PID_FILE") 2>/dev/null; then
        echo "[FRP] frpc已在运行，PID: $(cat $FRPC_PID_FILE)"
        return 0
    fi
    nohup $FRPC_CMD > $FRPC_LOG_FILE 2>&1 &
    echo $! > $FRPC_PID_FILE
    echo "[FRP] frpc客户端已启动，PID: $(cat $FRPC_PID_FILE)"
    echo "[FRP] 服务已通过内网穿透暴露在 54.226.20.77:5500"
}

stop_frp() {
    if [ -f "$FRPC_PID_FILE" ] && kill -0 $(cat "$FRPC_PID_FILE") 2>/dev/null; then
        kill $(cat "$FRPC_PID_FILE")
        rm -f "$FRPC_PID_FILE"
        echo "[FRP] frpc已停止"
    else
        echo "[FRP] frpc未在运行"
    fi
}

status_frp() {
    if [ -f "$FRPC_PID_FILE" ] && kill -0 $(cat "$FRPC_PID_FILE") 2>/dev/null; then
        echo "[FRP] frpc正在运行，PID: $(cat $FRPC_PID_FILE)"
    else
        echo "[FRP] frpc未在运行"
    fi
}

start() {
    start_frp
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "[API] 服务已在运行，PID: $(cat $PID_FILE)"
        exit 0
    fi
    nohup $CMD > $LOG_FILE 2>&1 &
    echo $! > $PID_FILE
    echo "[API] 服务已启动，PID: $(cat $PID_FILE)"
}

stop() {
    echo "🛑 正在停止所有服务..."
    
    # 停止API服务
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 $PID 2>/dev/null; then
            echo "[API] 正在停止API服务 (PID: $PID)..."
            kill $PID
            sleep 2
            if kill -0 $PID 2>/dev/null; then
                echo "[API] 强制停止API服务..."
                kill -9 $PID
            fi
            echo "[API] ✅ API服务已停止"
        else
            echo "[API] ⚠️ PID文件存在但进程不存在"
        fi
        rm -f "$PID_FILE"
    else
        echo "[API] ℹ️ 未找到API服务PID文件"
    fi
    
    # 停止FRP客户端
    if [ -f "$FRPC_PID_FILE" ]; then
        PID=$(cat "$FRPC_PID_FILE")
        if kill -0 $PID 2>/dev/null; then
            echo "[FRP] 正在停止FRP客户端 (PID: $PID)..."
            kill $PID
            sleep 2
            if kill -0 $PID 2>/dev/null; then
                echo "[FRP] 强制停止FRP客户端..."
                kill -9 $PID
            fi
            echo "[FRP] ✅ FRP客户端已停止"
        else
            echo "[FRP] ⚠️ PID文件存在但进程不存在"
        fi
        rm -f "$FRPC_PID_FILE"
    else
        echo "[FRP] ℹ️ 未找到FRP客户端PID文件"
    fi
    
    # 停止头条API服务
    if [ -f "toutiao_api.pid" ]; then
        PID=$(cat "toutiao_api.pid")
        if kill -0 $PID 2>/dev/null; then
            echo "[TOUTIAO] 正在停止头条API服务 (PID: $PID)..."
            kill $PID
            sleep 2
            if kill -0 $PID 2>/dev/null; then
                echo "[TOUTIAO] 强制停止头条API服务..."
                kill -9 $PID
            fi
            echo "[TOUTIAO] ✅ 头条API服务已停止"
        else
            echo "[TOUTIAO] ⚠️ PID文件存在但进程不存在"
        fi
        rm -f "toutiao_api.pid"
    else
        echo "[TOUTIAO] ℹ️ 未找到头条API服务PID文件"
    fi
    
    # 查找并停止所有相关进程（备用方案）
    echo "🔍 查找并停止所有相关进程..."
    pkill -f "api_service.py" 2>/dev/null && echo "  ✅ 停止api_service.py进程"
    pkill -f "frpc" 2>/dev/null && echo "  ✅ 停止frpc进程"
    pkill -f "toutiao_api" 2>/dev/null && echo "  ✅ 停止toutiao_api进程"
    
    # 清理所有PID文件
    echo "🧹 清理PID文件..."
    rm -f *.pid
    
    echo "🎉 所有服务已停止！"
    
    # 显示当前状态
    echo ""
    echo "📊 当前状态检查："
    ps aux | grep -E "(api_service|toutiao_api|frpc)" | grep -v grep || echo "  ✅ 没有相关进程在运行"
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "[API] 服务正在运行，PID: $(cat $PID_FILE)"
    else
        echo "[API] 服务未在运行"
    fi
    status_frp
}

restart() {
    stop
    sleep 1
    start
}

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) restart ;;
    status) status ;;
    *) echo "用法: $0 {start|stop|restart|status}" ;;
esac 