from datetime import timedelta

from datetime import datetime
from pathlib import Path

from conf import BASE_DIR


def get_absolute_path(relative_path: str, base_dir: str = None) -> str:
    # Convert the relative path to an absolute path
    absolute_path = Path(BASE_DIR) / base_dir / relative_path
    return str(absolute_path)


def get_title_and_hashtags(filename):
    """
  获取视频标题和 hashtag

  Args:
    filename: 视频文件名

  Returns:
    视频标题和 hashtag 列表
  """
    import os
    
    # 获取视频文件的目录路径
    video_dir = os.path.dirname(filename)
    
    # 优先查找与视频文件同名的txt文件（视频文件里面的标题）
    tags_file = filename.replace(".mp4", ".txt")
    
    # 如果同名txt文件不存在，则查找同级目录下的"标签.txt"文件
    if not os.path.exists(tags_file):
        tags_file = os.path.join(video_dir, "标签.txt")
    
    # 如果都不存在，抛出异常
    if not os.path.exists(tags_file):
        raise FileNotFoundError(f"未找到标签文件: {tags_file}")

    print(f"正在读取标签文件: {tags_file}")
    
    # 读取 txt 文件
    with open(tags_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 获取标题和 hashtag
    splite_str = content.strip().split("\n")
    title = splite_str[0]
    
    # 处理第二行的标签
    if len(splite_str) > 1:
        # 移除#号并按空格分割，过滤空字符串
        hashtags = [tag.strip() for tag in splite_str[1].replace("#", "").split(" ") if tag.strip()]
    else:
        hashtags = []

    return title, hashtags


def generate_schedule_time_next_day(total_videos, videos_per_day = 1, daily_times=None, timestamps=False, start_days=0):
    """
    Generate a schedule for video uploads, starting from the next day.

    Args:
    - total_videos: Total number of videos to be uploaded.
    - videos_per_day: Number of videos to be uploaded each day.
    - daily_times: Optional list of specific times of the day to publish the videos.
    - timestamps: Boolean to decide whether to return timestamps or datetime objects.
    - start_days: Start from after start_days.

    Returns:
    - A list of scheduling times for the videos, either as timestamps or datetime objects.
    """
    if videos_per_day <= 0:
        raise ValueError("videos_per_day should be a positive integer")

    if daily_times is None:
        # Default times to publish videos if not provided
        daily_times = [6, 11, 14, 16, 22]

    if videos_per_day > len(daily_times):
        raise ValueError("videos_per_day should not exceed the length of daily_times")

    # Generate timestamps
    schedule = []
    current_time = datetime.now()

    for video in range(total_videos):
        day = video // videos_per_day + start_days + 1  # +1 to start from the next day
        daily_video_index = video % videos_per_day

        # Calculate the time for the current video
        hour = daily_times[daily_video_index]
        time_offset = timedelta(days=day, hours=hour - current_time.hour, minutes=-current_time.minute,
                                seconds=-current_time.second, microseconds=-current_time.microsecond)
        timestamp = current_time + time_offset

        schedule.append(timestamp)

    if timestamps:
        schedule = [int(time.timestamp()) for time in schedule]
    return schedule
