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
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        kill $(cat "$PID_FILE")
        rm -f "$PID_FILE"
        echo "[API] 服务已停止"
    else
        echo "[API] 服务未在运行"
    fi
    stop_frp
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