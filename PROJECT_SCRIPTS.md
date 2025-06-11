# Social Auto Upload 项目管理脚本

本项目提供了多个脚本来简化项目的启动、停止和管理。

## 🚀 快速开始

### 方式1: 使用快速启动脚本（推荐）
```bash
# 启动项目
./quick_start.sh

# 停止项目
./stop_project.sh
```

### 方式2: 使用完整管理脚本
```bash
# 启动项目
./start_project.sh

# 停止项目
./start_project.sh stop

# 查看状态
./start_project.sh status

# 查看日志
./start_project.sh logs

# 重启项目
./start_project.sh restart
```

## 📋 脚本说明

### 1. `quick_start.sh` - 快速启动脚本
- 🎯 **用途**: 一键启动后端和前端服务
- ⚡ **特点**: 简单快速，适合日常开发使用
- 📦 **功能**: 自动停止现有服务，启动新服务

### 2. `start_project.sh` - 完整管理脚本
- 🎯 **用途**: 全功能项目管理工具
- ⚡ **特点**: 功能完整，支持多种操作
- 📦 **功能**: 启动、停止、重启、状态检查、日志查看

#### 可用命令：
```bash
./start_project.sh start          # 启动所有服务 (默认)
./start_project.sh stop           # 停止所有服务
./start_project.sh restart        # 重启所有服务
./start_project.sh status         # 检查服务状态
./start_project.sh logs           # 查看所有日志
./start_project.sh logs backend   # 查看后端日志
./start_project.sh logs frontend  # 查看前端日志
./start_project.sh help           # 显示帮助信息
```

### 3. `stop_project.sh` - 停止服务脚本
- 🎯 **用途**: 快速停止所有服务
- ⚡ **特点**: 简单直接，一键停止
- 📦 **功能**: 停止后端和前端服务，清理PID文件

## 🌐 服务地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端管理界面 | http://localhost:5173 | Vue 3 + Element Plus 管理界面 |
| 后端API | http://localhost:5409 | Flask REST API 服务 |

## 📁 目录结构

```
├── start_project.sh     # 完整管理脚本
├── quick_start.sh       # 快速启动脚本
├── stop_project.sh      # 停止服务脚本
├── logs/                # 日志目录
│   ├── backend.log      # 后端日志
│   └── frontend.log     # 前端日志
├── .pids/               # PID文件目录
│   ├── backend.pid      # 后端进程ID
│   └── frontend.pid     # 前端进程ID
├── sau_backend.py       # Python 后端入口
└── sau_frontend/        # Vue 前端项目
    ├── package.json
    └── ...
```

## 🔧 依赖要求

- **Python 3.x**: 运行后端服务
- **Node.js**: 运行前端服务
- **npm**: 安装前端依赖
- **lsof**: 检查端口占用（macOS/Linux 系统自带）

## 📝 日志查看

### 实时查看日志
```bash
# 查看后端日志
tail -f logs/backend.log

# 查看前端日志
tail -f logs/frontend.log

# 同时查看两个日志
tail -f logs/backend.log logs/frontend.log
```

### 使用脚本查看日志
```bash
# 查看所有日志（最后25行）
./start_project.sh logs

# 查看后端日志（最后50行）
./start_project.sh logs backend

# 查看前端日志（最后50行）
./start_project.sh logs frontend
```

## 🚨 故障排除

### 端口被占用
如果遇到端口被占用的问题，脚本会自动尝试停止现有服务。

手动检查端口占用：
```bash
# 检查后端端口 5409
lsof -i :5409

# 检查前端端口 5173
lsof -i :5173
```

### 服务启动失败
1. 检查日志文件：`logs/backend.log` 和 `logs/frontend.log`
2. 确保所有依赖已安装：
   ```bash
   # Python 依赖
   pip install -r requirements.txt
   
   # Node.js 依赖（在 sau_frontend 目录下）
   cd sau_frontend && npm install
   ```

### 权限问题
如果脚本无法执行，添加执行权限：
```bash
chmod +x start_project.sh
chmod +x quick_start.sh
chmod +x stop_project.sh
```

## 💡 使用建议

1. **日常开发**: 使用 `quick_start.sh` 快速启动
2. **调试问题**: 使用 `start_project.sh logs` 查看详细日志
3. **生产环境**: 使用完整管理脚本进行服务管理
4. **定期清理**: 清理日志文件以释放磁盘空间

## 🔄 更新记录

- **v1.0**: 初始版本，支持基本的启动、停止功能
- **v1.1**: 添加日志查看、状态检查功能
- **v1.2**: 添加颜色输出，改善用户体验 