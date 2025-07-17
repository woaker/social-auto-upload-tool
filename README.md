# YouTube视频下载与多平台转发API

本项目提供YouTube视频下载与多平台转发功能，支持通过内网穿透将本地服务暴露到公网。

## 功能特点

- 下载YouTube视频
- 转发视频到多个社交媒体平台（抖音、B站、快手、小红书等）
- 支持定时发布
- 提供RESTful API接口
- 内网穿透功能，可远程访问

## 内网穿透配置

项目使用frp实现内网穿透，配置如下：

### 服务端配置 (frps.ini)

```ini
[common]
bind_port = 5001
token = frp-315bfe284c994403ab2e5178eec44d3c
dashboard_port = 5002
dashboard_user = admin
dashboard_pwd = 1234567890
```

### 客户端配置 (frpc.ini)

```ini
[common]
server_addr = 54.226.20.77
server_port = 5001
authentication_method = token
token = frp-315bfe284c994403ab2e5178eec44d3c

[youtube_api]
type = tcp
local_ip = 127.0.0.1
local_port = 8000
remote_port = 5500
```

## 快速启动

运行以下命令启动服务：

```bash
bash start_youtube_api.sh
```

启动后，API服务将在以下地址可用：

- 本地访问：http://localhost:8000
- 远程访问：http://54.226.20.77:5500

## API文档

- 本地文档：http://localhost:8000/docs
- 远程文档：http://54.226.20.77:5500/docs

## 使用示例

### 下载并转发YouTube视频

```bash
curl -X POST "http://54.226.20.77:5500/api/youtube/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=example",
    "platforms": ["douyin", "bilibili"],
    "title": "示例视频",
    "tags": ["示例", "测试"]
  }'
```

### 查询任务状态

```bash
curl "http://54.226.20.77:5500/api/youtube/status/{task_id}"
```

## 注意事项

- 确保服务器已开放5000-6000端口
- 内网穿透服务依赖于frp，请确保frp服务端正常运行
- 如需修改配置，请编辑start_youtube_api.sh文件 