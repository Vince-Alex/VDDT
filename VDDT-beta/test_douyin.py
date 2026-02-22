#!/usr/bin/env python3
import yt_dlp
import os

# 抖音视频URL
url = 'https://www.douyin.com/video/7598940666043425769'
cookie_file = '/storage/emulated/0/CODE/Vince-Alex/VDDT/VDDT-beta/douyin_cookies.txt'

# 检查Cookie文件
if not os.path.exists(cookie_file):
    print('Cookie文件不存在:', cookie_file)
    exit(1)

print('Cookie文件内容前100字符:')
with open(cookie_file, 'r') as f:
    print(f.read(100))

# yt-dlp选项
ydl_opts = {
    'cookiefile': cookie_file,
    'quiet': False,
    'no_warnings': False,
    'ignoreerrors': True,
    'nocheckcertificate': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

print('\n尝试获取视频信息...')
try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # 先尝试获取信息
        info = ydl.extract_info(url, download=False)
        print('成功获取视频信息!')
        print('标题:', info.get('title', '未知'))
        print('上传者:', info.get('uploader', '未知'))
        print('时长:', info.get('duration', '未知'), '秒')
        
        # 尝试下载
        print('\n开始下载...')
        ydl.download([url])
        print('下载完成!')
except Exception as e:
    print('错误:', e)
    print('错误类型:', type(e).__name__)