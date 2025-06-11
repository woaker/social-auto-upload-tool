#!/bin/bash

echo "🛑 停止 Social Auto Upload 项目..."

# 停止所有相关进程
echo "停止后端服务..."
pkill -f "sau_backend.py" 2>/dev/null && echo "✅ 后端服务已停止" || echo "ℹ️ 后端服务未在运行"

echo "停止前端服务..."
pkill -f "vite.*sau_frontend" 2>/dev/null && echo "✅ 前端服务已停止" || echo "ℹ️ 前端服务未在运行"

# 清理 PID 文件
rm -f .pids/backend.pid .pids/frontend.pid 2>/dev/null

echo ""
echo "✅ 所有服务已停止"
echo "" 