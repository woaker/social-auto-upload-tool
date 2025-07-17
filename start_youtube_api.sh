#!/bin/bash

# 设置环境变量
export PYTHONPATH=$(pwd)

# 检查虚拟环境是否存在
if [ -d "venv" ]; then
    echo "激活虚拟环境..."
    source venv/bin/activate
fi

# 检查依赖是否安装
echo "检查依赖..."
pip install -r requirements.txt

# 定义内网穿透函数
start_frp() {
    echo "启动frp内网穿透..."
    if [ ! -d "frp" ]; then
        echo "下载并配置frp..."
        mkdir -p frp
        wget https://github.com/fatedier/frp/releases/download/v0.51.3/frp_0.51.3_darwin_amd64.tar.gz -O frp.tar.gz
        tar -zxvf frp.tar.gz -C frp --strip-components 1
        rm frp.tar.gz
    fi
    
    # 创建frpc.ini配置文件
    cat > frp/frpc.ini << EOF
[common]
server_addr = 54.226.20.77
server_port = 5001
# 确保与服务端配置中的token一致
authentication_method = token
token = frp-315bfe284c994403ab2e5178eec44d3c

[youtube_api]
type = tcp
local_ip = 127.0.0.1
local_port = 8000
remote_port = 5500
EOF
    echo "已创建frp配置文件 frp/frpc.ini"
    
    # 启动frp客户端
    ./frp/frpc -c frp/frpc.ini &
    FRP_PID=$!
    echo "frp客户端已启动，PID: $FRP_PID"
    echo "YouTube API 服务已通过内网穿透暴露在 54.226.20.77:5500"
}

# 检查端口8000是否被占用，如果被占用则杀掉进程
kill_port_process() {
    local port=$1
    echo "检查端口 $port 是否被占用..."
    local pid=$(lsof -ti:$port)
    if [ -n "$pid" ]; then
        echo "端口 $port 被进程 $pid 占用，正在终止..."
        kill -9 $pid
        sleep 1
    fi
}

# 终止占用端口8000的进程
kill_port_process 8000

# 启动API服务
echo "启动YouTube API服务..."
python3 youtube_api.py &
API_PID=$!

# 自动启动内网穿透
echo "正在启动内网穿透服务..."
start_frp

# 捕获Ctrl+C信号，优雅退出
trap 'echo "正在关闭服务..."; kill $API_PID 2>/dev/null; if [ -n "$FRP_PID" ]; then kill $FRP_PID 2>/dev/null; fi; exit 0' INT 

echo "服务已启动，按Ctrl+C退出"
# 保持脚本运行
wait $API_PID 