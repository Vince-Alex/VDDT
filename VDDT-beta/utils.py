import re
import os
from datetime import datetime
import sys
import colorama
from colorama import Fore, Back, Style
import http.cookies
import time
import urllib.parse

# 初始化 colorama
colorama.init(autoreset=True)

def ask(prompt):
    """询问用户是/否问题并返回布尔值"""
    while True:
        response = input(prompt + " (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print(f"{Fore.RED}无效输入，请输入 'y' 或 'n'{Style.RESET_ALL}")

def convert_to_netscape_cookie(cookie_str, output_file):
    """将原始 cookie 字符串转换为 Netscape 格式"""
    try:
        cookie_lines = []
        for part in cookie_str.split(';'):
            part = part.strip()
            if '=' in part:
                key, value = part.split('=', 1)
                cookie_lines.append(f"www.example.com\tFALSE\t/\tFALSE\t0\t{key}\t{value}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("\n".join(cookie_lines))
        
        print(f"{Fore.GREEN}[成功]{Style.RESET_ALL} Cookie 文件已保存为: {output_file}")
        return True
    except Exception as e:
        print(f"{Fore.RED}[错误]{Style.RESET_ALL} 转换 Cookie 失败: {e}")
        return False

def sanitize_filename(name):
    """移除 Windows 文件名中的非法字符"""
    return re.sub(r'[\/:*?"<>|]', '_', name)

def progress_hook(d):
    """
    yt-dlp 下载进度的回调函数，带有可视化加载条
    """
    if d['status'] == 'downloading':
        percent = d['_percent_str']
        eta = d['_eta_str']
        downloaded = d['_downloaded_bytes_str']
        total = d['_total_bytes_str'] or d['_total_bytes_estimate_str']

        bar_length = 40
        downloaded_percent = d['_percent'] / 100.0
        filled_length = int(round(bar_length * downloaded_percent))
        bar = '█' * filled_length + '-' * (bar_length - filled_length)

        sys.stdout.write(f"\r{Fore.CYAN}[下载中]{Style.RESET_ALL} {percent:<5} [{Fore.GREEN}{bar}{Style.RESET_ALL}] {downloaded} / {total if total else '未知'}  ETA: {eta:<8}")
        sys.stdout.flush()

    elif d['status'] == 'finished':
        print(f"\r{Fore.GREEN}[完成]{Style.RESET_ALL} 100% [{'█' * 40}] 文件已下载")
    elif d['status'] == 'error':
        print(f"\n{Fore.RED}[错误]{Style.RESET_ALL} 下载过程中发生错误")

