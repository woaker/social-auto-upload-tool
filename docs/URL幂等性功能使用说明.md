# URL幂等性功能使用说明

## 功能概述

本系统新增了URL幂等性功能，用于防止重复处理相同的URL，确保每个URL只被处理一次。该功能通过数据库记录已处理的URL，并在处理前进行检查。

## 数据库表结构

### tb_unquie 表
```sql
CREATE TABLE tb_unquie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,                    -- URL地址
    type TEXT NOT NULL,                   -- 处理类型 (youtube/juejin)
    task_id TEXT,                         -- 任务ID
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(url, type)                     -- URL和type的唯一性约束
)
```

## 功能特性

### 🔄 幂等性保证
- **唯一性约束**: URL + type 组合确保唯一性
- **自动跳过**: 已处理的URL自动跳过，避免重复处理
- **任务关联**: 记录处理该URL的任务ID

### 📊 统计功能
- **处理统计**: 按类型统计处理数量
- **时间统计**: 今日新增、历史总数
- **查询功能**: 支持按类型、任务ID查询

### 🛡️ 错误处理
- **数据库异常**: 完善的错误处理和日志记录
- **并发安全**: 使用数据库事务确保数据一致性

## 支持的接口

### 1. YouTube视频下载接口
**接口**: `POST /api/youtube/download`

**幂等性规则**:
- 当视频在抖音平台发送成功时，记录URL到数据库
- type固定为 `youtube`
- 记录对应的task_id

**示例**:
```bash
curl --request POST \
  --url http://localhost:8000/api/youtube/download \
  --header 'Content-Type: application/json' \
  --data '{
    "url": ["https://www.youtube.com/watch?v=UoD69nMbUsA"],
    "platforms": ["douyin"]
  }'
```

### 2. 头条文章转发接口
**接口**: `POST /api/toutiao/forward`

**幂等性规则**:
- 当文章转发成功时，记录URL到数据库
- type固定为 `juejin`
- 记录对应的task_id

**示例**:
```bash
curl --request POST \
  --url http://localhost:8000/api/toutiao/forward \
  --header 'Content-Type: application/json' \
  --data '{
    "urls": ["https://juejin.cn/post/123456"],
    "save_file": true,
    "use_ai": false
  }'
```

## 查询接口

### 1. 幂等性统计信息
**接口**: `GET /api/idempotency/stats`

**返回示例**:
```json
{
  "success": true,
  "data": {
    "total_count": 10,
    "type_stats": {
      "youtube": 6,
      "juejin": 4
    },
    "today_count": 3
  }
}
```

### 2. 已处理URL列表
**接口**: `GET /api/idempotency/urls?type=youtube&limit=100`

**参数说明**:
- `type`: 可选，过滤特定类型 (youtube/juejin)
- `limit`: 可选，限制返回数量，默认100

**返回示例**:
```json
{
  "success": true,
  "data": {
    "total": 6,
    "urls": [
      {
        "id": 1,
        "url": "https://www.youtube.com/watch?v=UoD69nMbUsA",
        "type": "youtube",
        "task_id": "ae1e3aea-12a3-4e71-b7be-727bed12e711",
        "create_time": "2025-07-19 14:48:16",
        "update_time": "2025-07-19 14:48:16"
      }
    ]
  }
}
```

### 3. 检查URL是否已处理
**接口**: `GET /api/idempotency/check/{url}?type=youtube`

**返回示例**:
```json
{
  "success": true,
  "data": {
    "url": "https://www.youtube.com/watch?v=UoD69nMbUsA",
    "type": "youtube",
    "is_processed": true
  }
}
```

### 4. 根据任务ID查询URL记录
**接口**: `GET /api/idempotency/task/{task_id}`

**返回示例**:
```json
{
  "success": true,
  "data": {
    "task_id": "ae1e3aea-12a3-4e71-b7be-727bed12e711",
    "total": 1,
    "records": [
      {
        "id": 1,
        "url": "https://www.youtube.com/watch?v=UoD69nMbUsA",
        "type": "youtube",
        "task_id": "ae1e3aea-12a3-4e71-b7be-727bed12e711",
        "create_time": "2025-07-19 14:48:16",
        "update_time": "2025-07-19 14:48:16"
      }
    ]
  }
}
```

## 处理流程

### YouTube视频处理流程
1. **接收请求**: 接收YouTube下载请求
2. **幂等性检查**: 检查URL是否已处理过
3. **跳过处理**: 如果已处理，返回"已跳过"状态
4. **正常处理**: 如果未处理，执行下载和上传
5. **记录成功**: 抖音上传成功后，记录URL到数据库

### 头条文章处理流程
1. **接收请求**: 接收头条转发请求
2. **幂等性检查**: 检查URL是否已处理过
3. **跳过处理**: 如果已处理，返回"已跳过"状态
4. **正常处理**: 如果未处理，执行文章转发
5. **记录成功**: 转发成功后，记录URL到数据库

## 日志示例

### 成功处理
```
🔍 开始处理视频: https://www.youtube.com/watch?v=UoD69nMbUsA
🆕 URL未处理过: https://www.youtube.com/watch?v=UoD69nMbUsA (type: youtube)
✅ YouTube视频抖音上传成功，已记录到数据库: https://www.youtube.com/watch?v=UoD69nMbUsA
```

### 跳过重复处理
```
🔍 开始处理视频: https://www.youtube.com/watch?v=UoD69nMbUsA
⏭️ 跳过已处理的URL: https://www.youtube.com/watch?v=UoD69nMbUsA
```

## 注意事项

1. **数据库文件**: 幂等性数据存储在 `./database.db` 文件中
2. **唯一性约束**: URL + type 组合必须唯一，相同URL的不同类型可以分别处理
3. **任务关联**: task_id 用于关联具体的处理任务，便于追踪和查询
4. **性能考虑**: 大量URL处理时，建议定期清理历史数据
5. **备份建议**: 定期备份数据库文件，防止数据丢失

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库文件权限
   - 确保磁盘空间充足

2. **唯一性约束冲突**
   - 检查URL格式是否一致
   - 确认type字段值正确

3. **查询结果异常**
   - 检查数据库表结构是否正确
   - 验证查询参数格式

### 调试命令

```bash
# 测试幂等性功能
python test_idempotency.py

# 重新创建数据库表
python db/createTable_tb_unquie.py

# 查看数据库内容
sqlite3 database.db "SELECT * FROM tb_unquie;"
``` 