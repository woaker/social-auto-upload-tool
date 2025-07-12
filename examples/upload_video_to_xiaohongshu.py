import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conf import BASE_DIR
from uploader.xiaohongshu_uploader.main import xiaohongshu_setup, XiaoHongShuVideo
from utils.files_times import generate_schedule_time_next_day, get_title_and_hashtags


if __name__ == '__main__':
    # 设置视频目录路径
    filepath = Path(BASE_DIR) / "videos"
    
    # 设置账户文件路径，确保目录存在
    cookies_dir = Path(BASE_DIR) / "cookies" / "xiaohongshu_uploader"
    cookies_dir.mkdir(exist_ok=True, parents=True)
    account_file = cookies_dir / "xhs_cookie.json"
    
    # 获取视频目录
    folder_path = Path(filepath)
    # 获取文件夹中的所有MP4文件
    files = list(folder_path.glob("*.mp4"))
    file_num = len(files)
    
    if file_num == 0:
        print("未找到任何视频文件，请确认视频目录中有.mp4文件")
        sys.exit(1)
        
    # 生成发布时间表，设置为每天下午4点发布
    publish_datetimes = generate_schedule_time_next_day(file_num, 1, daily_times=[16])
    
    # 设置小红书账户
    cookie_setup = asyncio.run(xiaohongshu_setup(account_file, handle=True))
    if not cookie_setup:
        print("小红书账户设置失败，请检查登录状态")
        sys.exit(1)
    
    print(f"找到{file_num}个视频文件，准备上传到小红书")
    
    # 循环处理每个视频文件
    for index, file in enumerate(files):
        try:
            # 获取视频标题和标签
            title, tags = get_title_and_hashtags(str(file))
            thumbnail_path = file.with_suffix('.png')
            
            # 打印视频文件名、标题和标签
            print(f"\n处理第 {index+1}/{file_num} 个视频:")
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"标签：{tags}")
            print(f"计划发布时间：{publish_datetimes[index]}")
            
            # 创建小红书视频上传对象
            if thumbnail_path.exists():
                print(f"使用自定义封面：{thumbnail_path}")
                app = XiaoHongShuVideo(title, file, tags, publish_datetimes[index], account_file, thumbnail_path=thumbnail_path)
            else:
                print("使用默认封面")
                app = XiaoHongShuVideo(title, file, tags, publish_datetimes[index], account_file)
            
            # 执行上传
            asyncio.run(app.main())
            print(f"视频 {index+1}/{file_num} 上传完成")
            
        except FileNotFoundError as e:
            print(f"错误：{e}")
            print(f"跳过视频文件：{file}")
            continue
        except Exception as e:
            print(f"上传视频时发生错误：{e}")
            print(f"跳过视频文件：{file}")
            continue
