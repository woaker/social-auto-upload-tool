# 批量视频上传脚本使用指南

## 📖 概述

本项目提供了三个主要脚本，用于按日期目录批量上传视频到各大社交媒体平台：

- `setup_today_videos.py` - 设置今天的视频目录
- `quick_upload.py` - 快速上传脚本（支持抖音、B站）
- `batch_upload_by_date.py` - 完整批量上传脚本（支持所有平台）

## 🚀 快速开始

### 1. 初始化今天的视频目录

```bash
python setup_today_videos.py
```

这个脚本会：
- 创建今天日期的视频目录（如：`videoFile/2025-01-11/`）
- 检查账号配置文件状态
- 提供操作指南和上传命令

### 2. 准备视频文件

将视频文件放入日期目录：

```
videoFile/
└── 2025-01-11/
    ├── 视频1.mp4
    ├── 视频1.txt        # 标题和标签文件
    ├── 视频2.mp4
    └── 视频2.txt
```

**标题文件格式** (`.txt`文件)：
```
第一行：视频标题
第二行：#标签1 #标签2 #标签3
```

示例：
```
我的生活日常分享
#生活 #日常 #分享 #vlog
```

### 3. 获取平台登录信息

在上传前，需要先获取各平台的账号信息：

```bash
# 抖音
python examples/get_douyin_cookie.py

# B站
python examples/get_bilibili_cookie.py

# 快手
python examples/get_kuaishou_cookie.py

# 小红书
python examples/get_xiaohongshu_cookie.py

# TikTok
python examples/get_tk_cookie.py

# 百家号
python examples/get_baijiahao_cookie.py

# 视频号
python examples/get_tencent_cookie.py
```

## 📱 支持的平台

| 平台 | 参数名 | 状态 |
|------|--------|------|
| 抖音 | `douyin` | ✅ |
| B站 | `bilibili` | ✅ |
| 快手 | `kuaishou` | ✅ |
| 小红书 | `xiaohongshu` | ✅ |
| TikTok | `tiktok` | ✅ |
| 百家号 | `baijiahao` | ✅ |
| 视频号 | `tencent` | ✅ |

## 🎯 使用方法

### 快速上传脚本 (推荐)

```bash
# 上传今天目录的视频到抖音
python quick_upload.py

# 上传今天目录的视频到抖音
python quick_upload.py douyin

# 上传今天目录的视频到B站
python quick_upload.py bilibili

# 上传指定日期目录的视频到抖音
python quick_upload.py douyin 2025-01-11

# 上传指定日期目录的视频到B站
python quick_upload.py bilibili 2025-01-11

# 显示帮助信息
python quick_upload.py help
```

### 完整批量上传脚本

```bash
# 上传到所有平台
python batch_upload_by_date.py --platform all --date 2025-01-11

# 上传到指定平台
python batch_upload_by_date.py --platform douyin --date 2025-01-11
python batch_upload_by_date.py --platform bilibili --date 2025-01-11

# 使用今天的日期（默认）
python batch_upload_by_date.py --platform douyin

# 查看帮助
python batch_upload_by_date.py --help
```

## 📁 目录结构

```
project/
├── videoFile/                    # 视频文件根目录
│   ├── 2025-01-11/              # 日期目录
│   │   ├── video1.mp4           # 视频文件
│   │   ├── video1.txt           # 对应的标题文件
│   │   ├── video2.mp4
│   │   └── video2.txt
│   └── 2025-01-12/
│       └── ...
├── cookies/                      # 账号配置目录
│   ├── douyin_uploader/
│   │   └── account.json
│   ├── bilibili_uploader/
│   │   └── account.json
│   └── ...
├── setup_today_videos.py        # 设置脚本
├── quick_upload.py              # 快速上传脚本
└── batch_upload_by_date.py      # 完整批量上传脚本
```

## 🔧 功能特性

### 自动化功能
- ✅ 自动创建日期目录
- ✅ 自动读取视频标题和标签
- ✅ 自动生成默认标题文件
- ✅ 自动设置发布时间（默认下午4点）
- ✅ 防频率限制（平台间自动延时）

### 容错处理
- ✅ 账号配置文件检查
- ✅ 视频文件格式验证
- ✅ 上传失败重试机制
- ✅ 详细的错误日志输出

### 批量操作
- ✅ 单平台批量上传
- ✅ 多平台批量上传
- ✅ 按日期目录管理
- ✅ 进度显示和状态反馈

## ⚠️ 注意事项

1. **视频格式**：建议使用 `.mp4` 格式
2. **标题文件**：必须与视频文件同名，扩展名为 `.txt`
3. **账号登录**：需要先获取各平台的登录信息
4. **上传频率**：建议不要过于频繁，避免被平台限制
5. **网络环境**：确保网络稳定，TikTok等国外平台可能需要代理

## 🐛 常见问题

### Q: 提示账号配置文件不存在？
A: 需要先运行对应的获取cookie脚本，如 `python examples/get_douyin_cookie.py`

### Q: 上传失败怎么办？
A: 检查网络连接、账号状态、视频格式等，查看控制台错误信息

### Q: 如何修改发布时间？
A: 修改脚本中的 `daily_times=[16]` 参数，16表示下午4点

### Q: 支持其他视频格式吗？
A: 目前主要支持 `.mp4` 格式，其他格式可能需要先转换

### Q: 如何批量处理多个日期的视频？
A: 可以编写循环脚本，或者手动指定不同的日期参数

## 📝 示例场景

### 场景1：每日发布routine
```bash
# 1. 创建今天的目录
python setup_today_videos.py

# 2. 手动放入视频文件和标题文件到生成的目录

# 3. 快速上传到抖音
python quick_upload.py douyin
```

### 场景2：多平台同步发布
```bash
# 上传到所有配置好的平台
python batch_upload_by_date.py --platform all --date 2025-01-11
```

### 场景3：指定平台发布
```bash
# 只发布到B站
python quick_upload.py bilibili 2025-01-11
```

## 🔄 更新日志

- v1.0.0: 初始版本，支持基本的批量上传功能
- 后续版本将添加更多平台支持和高级功能

## 💡 提示

- 建议先用测试账号进行测试
- 上传前检查视频内容是否符合平台规范
- 定期备份重要的配置文件
- 关注各平台的API更新和政策变化 