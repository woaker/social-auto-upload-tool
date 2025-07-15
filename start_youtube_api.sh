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

# 启动API服务
echo "启动YouTube API服务..."
python youtube_api.py

# 捕获Ctrl+C信号，优雅退出
trap 'echo "正在关闭服务..."; exit 0' INT 