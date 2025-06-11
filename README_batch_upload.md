# 📹 批量视频上传脚本使用文档

## 📖 概述

`batch_upload_by_date.py` 是一个功能强大的多平台视频批量上传工具，支持抖音、快手、小红书、视频号等主流平台的自动化视频发布。

### ✨ 核心特性

- 🎯 **多平台支持**：抖音、快手、小红书、视频号
- 🤖 **智能账号匹配**：自动识别`cookiesFile`目录中的账号文件
- ⏰ **灵活发布模式**：支持定时发布和立即发布
- 📅 **批量处理**：按日期目录组织和批量上传视频
- 🔧 **可配置参数**：丰富的命令行参数支持各种发布场景

## 🚀 快速开始

### 1. 环境准备

确保您已经安装了所需的依赖：

```bash
pip install -r requirements.txt
```

### 2. 目录结构

```
social-auto-upload/
├── videoFile/                    # 视频文件目录
│   └── 2025-06-11/              # 按日期组织的视频目录
│       ├── 测试1.mp4            # 视频文件
│       ├── 测试1.txt            # 视频描述文件（可选）
│       └── 测试2.mp4
├── cookiesFile/                  # 账号登录信息目录
│   ├── a7b72f5a-xxx.json        # 快手账号文件
│   ├── ebd39c7e-xxx.json        # 小红书账号文件
│   ├── e107cfb8-xxx.json        # 抖音账号文件
│   └── 4ba49f6a-xxx.json        # 视频号账号文件
└── batch_upload_by_date.py      # 批量上传脚本
```

### 3. 第一次使用

```bash
# 查看帮助信息
python batch_upload_by_date.py --help

# 简单上传示例（立即发布到小红书）
python batch_upload_by_date.py --platform xiaohongshu --date 2025-06-11 --daily-times ""
```

## 🛠️ 命令参数详解

### 基础参数

| 参数 | 简写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--platform` | `-p` | string | `all` | 目标平台：`douyin`、`kuaishou`、`xiaohongshu`、`tencent`、`all` |
| `--date` | `-d` | string | 今天 | 视频目录日期，格式：YYYY-MM-DD |

### 发布模式参数

| 参数 | 简写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--schedule` | `--enable-schedule` | flag | `True` | 启用定时发布 |
| `--no-schedule` | `--immediate` | flag | `False` | 强制立即发布，禁用定时发布 |
| `--daily-times` | `--times` | string | 空 | 发布时间点，格式：HH:MM（多个用逗号分隔） |

### 定时发布参数

| 参数 | 简写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--videos-per-day` | `--vpd` | int | `1` | 每天发布视频数量 |
| `--start-days` | `--delay` | int | `0` | 延迟开始天数（0=明天，1=后天...） |

## 📋 使用示例

### 🟢 基础使用

#### 查看帮助
```bash
python batch_upload_by_date.py --help
```

#### 上传到单个平台
```bash
# 上传到小红书（使用默认设置）
python batch_upload_by_date.py --platform xiaohongshu --date 2025-06-11

# 上传到抖音
python batch_upload_by_date.py --platform douyin --date 2025-06-11

# 上传到快手
python batch_upload_by_date.py --platform kuaishou --date 2025-06-11

# 上传到视频号
python batch_upload_by_date.py --platform tencent --date 2025-06-11
```

#### 上传到所有平台
```bash
python batch_upload_by_date.py --platform all --date 2025-06-11
```

### 🔴 立即发布模式

#### 方式1：使用 --no-schedule 参数
```bash
python batch_upload_by_date.py --platform xiaohongshu --date 2025-06-11 --no-schedule
```

#### 方式2：不设置发布时间（推荐）
```bash
python batch_upload_by_date.py --platform xiaohongshu --date 2025-06-11 --daily-times ""
```

#### 方式3：使用 --immediate 参数
```bash
python batch_upload_by_date.py --platform douyin --date 2025-06-11 --immediate
```

### 🟡 定时发布配置

#### 单个时间点发布
```bash
# 每天晚上7点发布
python batch_upload_by_date.py --platform xiaohongshu --date 2025-06-11 --daily-times "19:00"

# 每天下午4点发布
python batch_upload_by_date.py --platform douyin --date 2025-06-11 --daily-times "16:00"

# 每天上午10点半发布
python batch_upload_by_date.py --platform kuaishou --date 2025-06-11 --daily-times "10:30"
```

#### 多个时间点发布
```bash
# 每天3个时间点发布，需要3个视频
python batch_upload_by_date.py --platform xiaohongshu --date 2025-06-11 \
  --daily-times "10:00,15:00,20:00" \
  --videos-per-day 3

# 每天2个时间点发布
python batch_upload_by_date.py --platform all --date 2025-06-11 \
  --daily-times "12:00,18:00" \
  --videos-per-day 2
```

#### 延迟发布
```bash
# 后天开始发布
python batch_upload_by_date.py --platform douyin --date 2025-06-11 \
  --daily-times "16:00" \
  --start-days 1

# 大后天开始发布
python batch_upload_by_date.py --platform xiaohongshu --date 2025-06-11 \
  --daily-times "19:00" \
  --start-days 2
```

### 🔵 高级配置示例

#### 内容创作者日常发布
```bash
# 每天晚上7点发布一个视频到小红书
python batch_upload_by_date.py --platform xiaohongshu --date 2025-06-11 \
  --daily-times "19:00" \
  --videos-per-day 1
```

#### 企业多平台分发
```bash
# 同时发布到所有平台，每天下午4点
python batch_upload_by_date.py --platform all --date 2025-06-11 \
  --daily-times "16:00" \
  --videos-per-day 1
```

#### 营销活动批量发布
```bash
# 大量视频分散发布，每天3次，从明天开始
python batch_upload_by_date.py --platform all --date 2025-06-11 \
  --daily-times "09:00,15:00,21:00" \
  --videos-per-day 3 \
  --start-days 0
```

#### 错峰发布策略
```bash
# 工作日发布：上午10点和下午6点
python batch_upload_by_date.py --platform xiaohongshu --date 2025-06-11 \
  --daily-times "10:00,18:00" \
  --videos-per-day 2

# 晚高峰发布
python batch_upload_by_date.py --platform douyin --date 2025-06-11 \
  --daily-times "20:30" \
  --videos-per-day 1
```

## 📊 平台状态与功能支持

| 平台 | 状态 | 定时发布 | 立即发布 | 地理位置 | 备注 |
|------|------|----------|----------|----------|------|
| **小红书** | ✅ 完全可用 | ✅ | ✅ | ✅ | 推荐使用，功能最稳定 |
| **抖音** | ✅ 可用 | ✅ | ✅ | 🔧 固定北京 | 地理位置可选设置 |
| **快手** | ⚠️ 部分问题 | ✅ | ✅ | ❓ | 引导教程遮挡问题 |
| **视频号** | ❌ 需修复 | ❓ | ❓ | ❓ | Cookie失效需重新登录 |

## ⚙️ 配置说明

### 时间格式

支持以下时间格式：

- **HH:MM 格式**（推荐）：`"10:00"`、`"14:30"`、`"19:00"`
- **数字格式**（兼容）：`"10"`、`"14"`、`"19"`
- **多个时间点**：`"10:00,14:30,19:00"`

### 视频文件要求

- **格式**：支持 `.mp4` 格式
- **描述文件**：可选的 `.txt` 文件，包含标题和标签信息
- **命名**：视频文件名和描述文件名保持一致（除扩展名）

### 账号文件

- **位置**：`cookiesFile/` 目录
- **格式**：JSON 格式的登录信息文件
- **命名**：UUID 格式（脚本自动匹配平台）

## ⚠️ 注意事项

### 使用限制

1. **账号文件**：确保 `cookiesFile` 目录中有对应平台的有效登录信息
2. **视频数量**：每天发布数量不能超过设置的时间点数量
3. **时间验证**：小时必须在 0-23 之间，分钟必须在 0-59 之间
4. **目录结构**：视频文件必须按日期目录组织

### 常见问题

**Q: 如何设置立即发布？**
A: 使用 `--daily-times ""` 或 `--no-schedule` 参数

**Q: 多个视频如何分配时间？**
A: 使用 `--videos-per-day` 设置每天发布数量，时间点数量必须 ≥ 发布数量

**Q: 如何延迟发布？**
A: 使用 `--start-days` 参数，0=明天，1=后天，以此类推

**Q: 账号文件如何获取？**
A: 需要先运行对应平台的 cookie 获取脚本

## 🔧 故障排除

### 常见错误

1. **"日期目录不存在"**
   ```bash
   # 创建目录
   mkdir -p videoFile/2025-06-11
   ```

2. **"未找到匹配的账号文件"**
   ```bash
   # 检查账号文件
   ls cookiesFile/
   ```

3. **"每天发布数量超过时间点数量"**
   ```bash
   # 调整参数
   --daily-times "10:00,14:00,18:00" --videos-per-day 3
   ```

### 调试方法

```bash
# 查看详细帮助
python batch_upload_by_date.py --help

# 测试配置（不实际上传）
python batch_upload_by_date.py --platform xiaohongshu --date 2025-06-11 --daily-times "19:00" --help
```

## 📈 最佳实践

### 推荐配置

1. **新手用户**：
   ```bash
   python batch_upload_by_date.py --platform xiaohongshu --date 2025-06-11 --daily-times "19:00"
   ```

2. **专业用户**：
   ```bash
   python batch_upload_by_date.py --platform all --date 2025-06-11 \
     --daily-times "10:00,15:00,20:00" \
     --videos-per-day 3 \
     --start-days 1
   ```

3. **测试环境**：
   ```bash
   python batch_upload_by_date.py --platform xiaohongshu --date 2025-06-11 --daily-times ""
   ```

### 发布时间建议

- **小红书**：19:00-21:00（晚高峰）
- **抖音**：12:00-14:00、19:00-22:00
- **快手**：18:00-22:00
- **视频号**：12:00-14:00、20:00-22:00

---

## 📞 技术支持

如果您在使用过程中遇到问题，请：

1. 检查本文档的常见问题部分
2. 确认环境配置和依赖安装
3. 验证视频文件和账号文件的完整性

**最后更新时间**：2025-06-11  
**脚本版本**：支持定时发布配置版本 