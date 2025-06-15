# 今日头条文章自动发布工具

## 功能特点

✅ **完整自动化发布流程**
- 自动填充文章标题和内容
- 智能添加文章标签
- 自动生成精美封面图片
- 支持立即发布和定时发布

✅ **智能弹窗处理**
- 自动检测并关闭AI助手弹窗
- 多种关闭方式：按钮点击、ESC键、点击外部
- 确保发布流程不被中断

✅ **封面自动生成**
- 基于文章标题自动生成精美封面
- 支持中文字体和智能换行
- 16:9标准比例，适配今日头条要求

## 快速开始

### 1. 安装依赖

```bash
pip install playwright Pillow
playwright install chromium
```

### 2. 登录账号

```bash
python examples/login_toutiao.py
```

### 3. 发布文章

```bash
python examples/upload_article_to_toutiao_final.py
```

## 使用示例

```python
from uploader.toutiao_uploader.main import TouTiaoArticle
from utils.files_times import get_absolute_path

# 账号文件路径
account_file = get_absolute_path("cookies/toutiao_uploader/account.json", "toutiao_uploader")

# 创建文章对象
article = TouTiaoArticle(
    title="文章标题",
    content="文章内容...",
    tags=["标签1", "标签2"],
    publish_date=0,  # 0表示立即发布
    account_file=account_file,
    cover_path=None  # None表示自动生成封面
)

# 发布文章
await article.main()
```

## 文件结构

```
uploader/toutiao_uploader/
├── main.py                    # 核心发布类
└── __init__.py

examples/
├── upload_article_to_toutiao_final.py  # 发布示例
└── login_toutiao.py                    # 登录脚本

articles/                      # 示例文章
images/                       # 生成的封面图片
cookies/toutiao_uploader/     # 登录状态文件
```

## 核心功能

### TouTiaoArticle 类

主要方法：
- `navigate_to_publish_page()` - 导航到发布页面
- `fill_title()` - 填写文章标题
- `fill_content()` - 填写文章内容
- `add_tags()` - 添加文章标签
- `upload_cover()` - 上传封面图片
- `publish_article()` - 发布文章

### 智能功能

1. **AI助手弹窗处理** - 自动检测并关闭干扰弹窗
2. **默认封面生成** - 基于标题自动生成精美封面
3. **多重上传方式** - 支持多种封面上传方法
4. **保存按钮处理** - 智能处理封面上传后的保存操作

## 注意事项

1. 首次使用需要手动登录今日头条账号
2. 确保网络连接稳定
3. 建议在发布前预览文章内容
4. 封面图片会自动保存到 `images/` 目录

## 故障排除

**问题**: Cookie过期
**解决**: 运行登录脚本重新获取Cookie

**问题**: 封面上传失败
**解决**: 检查PIL库是否正确安装

**问题**: 页面元素找不到
**解决**: 今日头条页面可能更新，需要更新选择器

## 技术支持

如遇问题，请检查：
1. 网络连接是否正常
2. 浏览器是否正确安装
3. 依赖库是否完整安装
4. 账号登录状态是否有效 