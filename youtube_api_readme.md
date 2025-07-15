# YouTube视频下载与多平台转发API

这是一个基于FastAPI的HTTP接口，支持从YouTube下载视频并异步转发到多个社交媒体平台。

## 功能特点

- 支持从YouTube下载视频
- 支持转发到多个社交媒体平台（抖音、B站、快手、小红书、今日头条等）
- 支持定时发布
- 支持自定义视频标题和标签
- 支持异步处理，不阻塞用户操作
- 支持任务状态查询
- 支持平台列表查询

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动服务

```bash
# 方式1：使用启动脚本
./start_youtube_api.sh

# 方式2：直接启动
python youtube_api.py
```

服务默认在 `http://localhost:8000` 上运行。

## API接口说明

### 1. 下载并转发YouTube视频

**请求：**

```
POST /api/youtube/download
```

**参数：**

```json
{
  "url": "https://www.youtube.com/watch?v=example",
  "platforms": ["douyin", "bilibili"],
  "title": "自定义标题",
  "tags": ["标签1", "标签2"],
  "schedule_time": "2025-07-20 14:30:00"
}
```

**参数说明：**

- `url`：YouTube视频URL（必填）
- `platforms`：要转发的平台列表，支持：douyin, bilibili, kuaishou, xiaohongshu, toutiao（选填，默认为["douyin"]）
- `title`：自定义视频标题（选填，默认使用YouTube标题）
- `tags`：视频标签列表（选填，默认为["YouTube", "转发"]）
- `schedule_time`：定时发布时间，格式：YYYY-MM-DD HH:MM:SS（选填，默认立即发布）

**响应：**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "任务已创建，正在处理中"
}
```

### 2. 查询任务状态

**请求：**

```
GET /api/youtube/status/{task_id}
```

**响应：**

```json
{
  "status": "completed",
  "message": "处理完成",
  "results": {
    "douyin": {
      "status": "success",
      "message": "上传成功"
    },
    "bilibili": {
      "status": "success",
      "message": "上传成功"
    }
  }
}
```

### 3. 获取支持的平台列表

**请求：**

```
GET /api/platforms
```

**响应：**

```json
[
  {
    "id": "douyin",
    "name": "抖音",
    "available": true
  },
  {
    "id": "bilibili",
    "name": "B站",
    "available": true
  },
  {
    "id": "kuaishou",
    "name": "快手",
    "available": false
  }
]
```

## 任务状态说明

- `pending`：任务已创建，等待处理
- `downloading`：正在下载YouTube视频
- `processing`：正在处理视频（转换格式、提取封面等）
- `uploading`：正在上传视频到各平台
- `completed`：处理完成
- `failed`：处理失败

## 注意事项

1. 确保已安装所有依赖，包括yt-dlp和ffmpeg
2. 确保各平台的cookie文件已正确配置
3. 上传大视频可能需要较长时间，请耐心等待
4. 可以通过任务状态API查询任务进度

## 示例

使用curl发送请求：

```bash
curl -X POST "http://localhost:8000/api/youtube/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=example",
    "platforms": ["douyin", "bilibili"],
    "title": "自定义标题",
    "tags": ["标签1", "标签2"]
  }'
```

使用Python发送请求：

```python
import requests

url = "http://localhost:8000/api/youtube/download"
data = {
    "url": "https://www.youtube.com/watch?v=example",
    "platforms": ["douyin", "bilibili"],
    "title": "自定义标题",
    "tags": ["标签1", "标签2"]
}

response = requests.post(url, json=data)
print(response.json())
``` 