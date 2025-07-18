# 统一API服务接口文档

本服务整合了头条文章转发、YouTube视频下载等多平台API接口，统一监听一个端口，支持串行队列、任务状态查询等功能。

---

## 1. 服务启动

请使用如下命令启动服务：

```bash
./start_api.sh start
```

**服务信息：**
- 本地端口：**8000**
- 远程访问：**http://54.226.20.77:5500**
- 服务名称：统一API服务

---

## 2. 主要接口

### 2.1 服务信息接口

- **接口地址**：`GET /`
- **功能**：获取服务基本信息

**响应示例：**
```json
{
    "name": "统一API服务",
    "version": "1.0.0",
    "description": "整合头条文章转发、YouTube视频下载等多平台API接口",
    "docs_url": "/docs",
    "redoc_url": "/redoc"
}
```

### 2.2 头条文章转发接口

- **接口地址**：`POST /api/toutiao/forward`
- **功能**：将一篇文章URL转发到今日头条（单次仅支持1个URL）

#### 请求参数（JSON）
| 字段           | 类型         | 必填 | 说明                                   | 默认值                      |
|----------------|--------------|------|----------------------------------------|-----------------------------|
| urls           | List[str]    | 是   | 文章URL列表（仅支持1个）               | -                           |
| save_file      | bool         | 否   | 是否保存文章到本地文件                 | false                       |
| account_file   | str          | 否   | 头条账号cookie文件路径                  | cookiesFile/toutiao_cookie.json |
| use_ai         | bool         | 否   | 是否使用AI美化内容和标签               | false                       |
| default_tags   | List[str]    | 否   | 默认标签列表                          | ["AI", "互联网", "自动化"]   |

#### 响应参数
| 字段     | 类型 | 说明                           |
|----------|------|--------------------------------|
| task_id  | str  | 任务ID，用于查询状态           |
| status   | str  | 任务状态（queued/processing/completed/error） |
| message  | str  | 状态描述信息                   |

#### 调用示例

**curl示例：**
```bash
curl -X POST "http://54.226.20.77:5500/api/toutiao/forward" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com/article"],
    "save_file": true,
    "use_ai": true,
    "default_tags": ["AI", "技术", "创新"]
  }'
```

**Python示例：**
```python
import requests

url = "http://54.226.20.77:5500/api/toutiao/forward"
data = {
    "urls": ["https://example.com/article"],
    "save_file": True,
    "use_ai": True,
    "default_tags": ["AI", "技术", "创新"]
}

response = requests.post(url, json=data)
result = response.json()
print(f"任务ID: {result['task_id']}")
print(f"状态: {result['status']}")
```

### 2.3 头条账号获取接口

- **接口地址**：`GET /api/toutiao/accounts`
- **功能**：获取可用的头条账号列表

**响应示例：**
```json
{
    "accounts": [
        {
            "file": "toutiao_cookie.json",
            "path": "cookiesFile/toutiao_cookie.json",
            "name": "未命名账号"
        }
    ]
}
```

### 2.4 YouTube视频下载接口

- **接口地址**：`POST /api/youtube/download`
- **功能**：下载YouTube视频

#### 请求参数（JSON）
| 字段        | 类型 | 必填 | 说明           | 默认值   |
|-------------|------|------|----------------|----------|
| url         | str  | 是   | YouTube视频URL | -        |
| quality     | str  | 否   | 视频质量       | "best"   |
| output_dir  | str  | 否   | 输出目录       | "videos" |

#### 调用示例

**curl示例：**
```bash
curl -X POST "http://54.226.20.77:5500/api/youtube/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=example",
    "quality": "best",
    "output_dir": "videos"
  }'
```

### 2.5 任务状态查询接口

- **接口地址**：`GET /api/task/{task_id}`
- **功能**：查询任务执行状态

#### 响应参数
| 字段     | 类型                | 说明                           |
|----------|---------------------|--------------------------------|
| task_id  | str                 | 任务ID                         |
| status   | str                 | 任务状态                       |
| message  | str                 | 状态描述信息                   |
| result   | Dict[str, Any]      | 任务结果（可选）               |

**状态说明：**
- `queued`: 已加入队列
- `processing`: 正在处理
- `completed`: 处理完成
- `error`: 处理失败

#### 调用示例

**curl示例：**
```bash
curl -X GET "http://54.226.20.77:5500/api/task/your-task-id" \
  -H "Content-Type: application/json"
```

**Python示例：**
```python
import requests
import time

# 提交任务
forward_response = requests.post("http://54.226.20.77:5500/api/toutiao/forward", json={
    "urls": ["https://example.com/article"]
})
task_id = forward_response.json()["task_id"]

# 轮询任务状态
while True:
    status_response = requests.get(f"http://54.226.20.77:5500/api/task/{task_id}")
    status_data = status_response.json()
    
    print(f"任务状态: {status_data['status']}")
    print(f"状态信息: {status_data['message']}")
    
    if status_data['status'] in ['completed', 'error']:
        break
    
    time.sleep(2)  # 等待2秒后再次查询
```

---

## 3. 服务管理

### 3.1 启动服务
```bash
./start_api.sh start
```

### 3.2 停止服务
```bash
./start_api.sh stop
```

### 3.3 重启服务
```bash
./start_api.sh restart
```

### 3.4 查看服务状态
```bash
./start_api.sh status
```

---

## 4. 常见问题

### 4.1 接口返回"队列已满"
- **原因**：当前任务队列已达到最大容量（100个任务）
- **解决**：等待一段时间后重试，或查询现有任务状态

### 4.2 任务处理超时
- **头条转发**：默认超时时间3分钟
- **YouTube下载**：默认超时时间5分钟
- **解决**：检查网络连接和目标资源可用性

### 4.3 远程访问失败
- **检查**：确认frp内网穿透服务正常运行
- **验证**：访问 `http://54.226.20.77:5500/` 查看服务状态

### 4.4 账号认证失败
- **检查**：确认cookie文件存在且有效
- **解决**：重新登录获取最新cookie

---

## 5. 技术特性

- **统一端口**：所有API接口统一监听8000端口
- **串行队列**：任务按顺序处理，避免并发冲突
- **状态跟踪**：支持任务状态实时查询
- **超时控制**：防止任务无限期阻塞
- **错误处理**：完善的异常捕获和错误反馈
- **内网穿透**：支持远程访问

---

## 6. 开发说明

- **框架**：FastAPI
- **异步处理**：asyncio + 后台worker
- **任务队列**：asyncio.Queue
- **子进程调用**：subprocess调用现有脚本
- **日志记录**：详细的操作日志和错误日志 