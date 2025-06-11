#!/bin/bash

# 快速启动脚本
echo "🚀 启动 Social Auto Upload 项目..."

# 停止可能存在的服务
pkill -f "sau_backend.py" 2>/dev/null || true
pkill -f "vite.*sau_frontend" 2>/dev/null || true

# 创建日志目录
mkdir -p logs

echo "📦 启动后端服务..."
nohup python sau_backend.py > logs/backend.log 2>&1 &
sleep 3

echo "🎨 启动前端服务..."
cd sau_frontend
nohup npm run dev > ../logs/frontend.log 2>&1 &
cd ..
sleep 5

echo ""
echo "✅ 项目启动完成！"
echo ""
echo "📍 访问地址:"
echo "  前端: http://localhost:5173"
echo "  后端: http://localhost:5409"
echo ""
echo "📋 查看日志:"
echo "  后端: tail -f logs/backend.log"
echo "  前端: tail -f logs/frontend.log"
echo ""
echo "🛑 停止服务:"
echo "  ./start_project.sh stop"
echo "" 