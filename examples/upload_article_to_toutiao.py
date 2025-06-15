import asyncio
import re
from pathlib import Path

from conf import BASE_DIR
from uploader.toutiao_uploader.main import toutiao_setup, TouTiaoArticle
from utils.files_times import generate_schedule_time_next_day


def get_article_content(file_path):
    """读取文章内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"读取文章内容失败: {e}")
        return ""


def get_article_title_and_tags(file_path):
    """从文章文件中提取标题和标签"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取标题
        title = Path(file_path).stem  # 默认使用文件名作为标题
        
        # 如果是 Markdown 文件，尝试提取第一个 # 标题
        if file_path.endswith('.md'):
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('# ') and not line.startswith('## '):
                    title = line[2:].strip()  # 去掉 "# " 前缀
                    break
        
        # 提取标签（查找 #标签 格式）
        tags = []
        # 使用正则表达式查找所有 #标签 格式的内容
        tag_pattern = r'#([^\s#]+)'
        matches = re.findall(tag_pattern, content)
        
        # 过滤掉 Markdown 标题（通常在行首）
        for match in matches:
            # 检查这个标签是否在行首（可能是 Markdown 标题）
            tag_with_hash = f'#{match}'
            lines = content.split('\n')
            is_title = False
            for line in lines:
                line_stripped = line.strip()
                if line_stripped.startswith('#') and tag_with_hash in line_stripped:
                    # 如果这行以多个#开头，可能是标题
                    if line_stripped.startswith('##') or line_stripped.startswith('# '):
                        is_title = True
                        break
            
            if not is_title and match not in tags:
                tags.append(match)
        
        return title, tags
        
    except Exception as e:
        print(f"提取标题和标签失败: {e}")
        return Path(file_path).stem, []


if __name__ == '__main__':
    articles_dir = Path(BASE_DIR) / "articles"
    account_file = Path(BASE_DIR / "cookies" / "toutiao_uploader" / "account.json")
    
    # 获取文章目录
    folder_path = Path(articles_dir)
    
    # 获取文件夹中的所有文章文件（支持多种格式）
    files = []
    for pattern in ["*.md", "*.txt", "*.html"]:
        files.extend(list(folder_path.glob(pattern)))
    
    file_num = len(files)
    if file_num == 0:
        print(f"在 {articles_dir} 目录下未找到任何文章文件（支持格式：.md, .txt, .html）")
        exit(1)
    
    # 生成发布时间计划（每天16点发布）
    publish_datetimes = generate_schedule_time_next_day(file_num, 1, daily_times=[16])
    
    # 设置账号cookie
    cookie_setup = asyncio.run(toutiao_setup(account_file, handle=False))
    
    for index, file in enumerate(files):
        # 获取标题和标签
        title, tags = get_article_title_and_tags(str(file))
        
        # 读取文章内容
        content = get_article_content(file)
        if not content:
            print(f"跳过空文件: {file}")
            continue
        
        # 查找封面图片（与文章同名的图片文件）
        cover_path = None
        for ext in ['.jpg', '.jpeg', '.png', '.webp']:
            potential_cover = file.with_suffix(ext)
            if potential_cover.exists():
                cover_path = potential_cover
                break
        
        # 打印文章信息
        print(f"文章文件名：{file}")
        print(f"标题：{title}")
        print(f"标签：{tags}")
        print(f"内容长度：{len(content)} 字符")
        if cover_path:
            print(f"封面图片：{cover_path}")
        else:
            print("封面图片：无")
        print("-" * 50)
        
        # 创建文章发布实例
        app = TouTiaoArticle(
            title=title,
            content=content,
            tags=tags,
            publish_date=publish_datetimes[index],
            account_file=account_file,
            cover_path=cover_path
        )
        
        # 发布文章
        asyncio.run(app.main(), debug=False) 