#!/usr/bin/env python3
"""
VDDT 工具模块
提供通用工具函数
"""
import re
import sys
import colorama
from colorama import Fore, Style

# 初始化 colorama
colorama.init(autoreset=True)

# 常量定义
FILENAME_INVALID_CHARS = r'[\/ :*?"<>|]'
PROGRESS_BAR_LENGTH = 40
PROGRESS_BAR_FILLED = '█'
PROGRESS_BAR_EMPTY = '-'


def ask(prompt):
    """
    询问用户是/否问题并返回布尔值

    Args:
        prompt: 提示信息

    Returns:
        True 表示用户选择 'y'，False 表示用户选择 'n'
    """
    while True:
        response = input(prompt + " (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print(f"{Fore.RED}无效输入，请输入 'y' 或 'n'{Style.RESET_ALL}")


def sanitize_filename(name):
    """
    移除文件名中的非法字符（Windows 兼容）

    Args:
        name: 原始文件名

    Returns:
        清理后的文件名
    """
    return re.sub(FILENAME_INVALID_CHARS, '_', name)


def format_progress_bar(percent):
    """
    格式化进度条

    Args:
        percent: 进度百分比 (0-100)

    Returns:
        格式化后的进度条字符串
    """
    downloaded_percent = percent / 100.0
    filled_length = int(round(PROGRESS_BAR_LENGTH * downloaded_percent))
    bar = PROGRESS_BAR_FILLED * filled_length + PROGRESS_BAR_EMPTY * (PROGRESS_BAR_LENGTH - filled_length)
    return f"{Fore.GREEN}{bar}{Style.RESET_ALL}"


def progress_hook(d):
    """
    yt-dlp 下载进度的回调函数，带有可视化加载条

    Args:
        d: yt-dlp 传递的进度字典
    """
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', 'N/A')
        eta = d.get('_eta_str', 'N/A')
        downloaded = d.get('_downloaded_bytes_str', 'N/A')
        total = d.get('_total_bytes_str') or d.get('_total_bytes_estimate_str', '未知')

        # 获取进度百分比
        percent_value = d.get('_percent', 0)

        # 格式化进度条
        bar = format_progress_bar(percent_value)

        # 显示进度信息
        sys.stdout.write(
            f"\r{Fore.CYAN}[下载中]{Style.RESET_ALL} {percent:<5} [{bar}] "
            f"{downloaded} / {total}  ETA: {eta:<8}"
        )
        sys.stdout.flush()

    elif d['status'] == 'finished':
        print(f"\r{Fore.GREEN}[完成]{Style.RESET_ALL} 100% [{'█' * PROGRESS_BAR_LENGTH}] 文件已下载")

    elif d['status'] == 'error':
        print(f"\n{Fore.RED}[错误]{Style.RESET_ALL} 下载过程中发生错误")


def convert_to_netscape_cookie(cookie_str, output_file):
    """
    将原始 cookie 字符串转换为 Netscape 格式

    Args:
        cookie_str: 原始 cookie 字符串
        output_file: 输出文件路径

    Returns:
        转换成功返回 True，失败返回 False
    """
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


def format_bytes(bytes_value):
    """
    格式化字节数为人类可读格式

    Args:
        bytes_value: 字节数

    Returns:
        格式化后的字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def validate_url(url):
    """
    验证 URL 是否为有效的 HTTP/HTTPS 链接

    Args:
        url: 待验证的 URL

    Returns:
        有效返回 True，无效返回 False
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None


def truncate_string(text, max_length=60, suffix='...'):
    """
    截断字符串到指定长度

    Args:
        text: 原始字符串
        max_length: 最大长度
        suffix: 截断后添加的后缀

    Returns:
        截断后的字符串
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
