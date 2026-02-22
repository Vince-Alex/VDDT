#!/usr/bin/env python3
"""
VDDT 下载器核心模块
提供视频格式获取、下载和 Cookie 处理功能
"""
import yt_dlp
import colorama
from colorama import Fore, Style
import os
import sys
import time
import datetime
import urllib.parse
from utils import sanitize_filename, progress_hook

# 常量定义
COOKIES_DIR = 'cookies'
NETSCAPE_COOKIE_HEADER = "# Netscape HTTP Cookie File\n"
DEFAULT_COOKIE_FILES = ["common.ck"]


def suggest_best_quality(formats):
    """
    基于高度建议最佳可用视频质量的格式 ID

    Args:
        formats: yt-dlp 返回的格式列表

    Returns:
        最佳视频格式的 format_id，如果没有视频格式则返回 None
    """
    video_formats = [f for f in formats if f.get("vcodec") != "none" and f.get("height")]
    if not video_formats:
        return None
    sorted_formats = sorted(video_formats, key=lambda f: f.get("height", 0), reverse=True)
    return sorted_formats[0].get("format_id")


def format_filesize(size_bytes):
    """
    格式化文件大小显示

    Args:
        size_bytes: 文件大小（字节）

    Returns:
        格式化后的文件大小字符串
    """
    if not size_bytes:
        return "-"
    return f"{size_bytes / (1024*1024):.2f} MB"


def get_format_lists(url, ydl_opts):
    """
    获取并列出给定 URL 的可用格式

    Args:
        url: 视频 URL
        ydl_opts: yt-dlp 配置选项

    Returns:
        tuple: (info_dict, formats, format_list_display)
            - info_dict: 视频信息字典
            - formats: 格式列表
            - format_list_display: 用于显示的格式列表
    """
    print(f"\n{Fore.CYAN}正在获取视频信息...{Style.RESET_ALL}")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])

            format_list = []
            for i, f in enumerate(formats):
                filesize = f.get('filesize') or f.get('filesize_approx')
                format_list.append((
                    i + 1,
                    f.get('format_id', '-'),
                    f.get('ext', '-'),
                    f.get('resolution') or f'{f.get("height", "N/A")}p' if f.get("vcodec") != "none" else '仅音频',
                    f.get('vcodec', '-').replace('none', '-'),
                    f.get('acodec', '-').replace('none', '-'),
                    filesize
                ))

            print(f"\n{Fore.CYAN}可用格式:{Style.RESET_ALL}")
            print(f"{'序号':<5} {'格式ID':<10} {'扩展名':<8} {'分辨率':<15} {'视频编码':<15} {'音频编码':<15} {'大小':<15}")
            print(f"{Fore.CYAN}-" * 83 + Style.RESET_ALL)

            for item in format_list:
                size_str = format_filesize(item[6])
                print(f"{item[0]:<5} {item[1]:<10} {item[2]:<8} {item[3]:<15} {item[4]:<15} {item[5]:<15} {size_str:<15}")

            print(f"{Fore.CYAN}-" * 83 + Style.RESET_ALL)
            return info, formats, format_list

        except yt_dlp.utils.DownloadError as e:
            print(f"\n{Fore.RED}[错误]{Style.RESET_ALL} 获取格式失败: {e}")
            print("请检查链接是否有效，或网络连接/代理设置。")
        except Exception as e:
            print(f"\n{Fore.RED}[错误]{Style.RESET_ALL} 获取格式时发生未知错误: {e}")

    return None, [], []


def generate_filename_template(info_dict, output_dir):
    """
    根据视频信息生成文件名模板

    Args:
        info_dict: 视频信息字典
        output_dir: 输出目录

    Returns:
        完整的输出路径模板
    """
    title = sanitize_filename(info_dict.get('title', 'video'))
    author = sanitize_filename(info_dict.get('uploader', 'channel'))
    upload_date_str = info_dict.get('upload_date', '')

    if upload_date_str:
        try:
            date_str = datetime.datetime.strptime(upload_date_str, '%Y%m%d').strftime('%Y-%m-%d')
        except ValueError:
            date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    else:
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')

    filename_template = f"{date_str}_{author}_{title}.%(ext)s"
    return os.path.join(output_dir, filename_template)


def download(url, format_id, output_dir, ydl_opts, info_dict=None):
    """
    执行视频下载

    Args:
        url: 视频 URL
        format_id: 格式 ID
        output_dir: 输出目录
        ydl_opts: yt-dlp 配置选项
        info_dict: 视频信息字典（可选）
    """
    # 设置输出模板
    if info_dict:
        ydl_opts['outtmpl'] = generate_filename_template(info_dict, output_dir)
    else:
        ydl_opts['outtmpl'] = os.path.join(output_dir, '%(title)s.%(ext)s')

    # 准备下载选项
    ydl_opts_download = ydl_opts.copy()
    ydl_opts_download.update({
        'format': format_id,
        'progress_hooks': [progress_hook],
        'concurrent_fragment_downloads': 5,
        'fragment_retries': 10,
        'retries': 10,
        'postprocessors': ydl_opts.get('postprocessors', []),
    })

    # 执行下载
    with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
        try:
            print(f"\n{Fore.CYAN}准备下载...{Style.RESET_ALL}")
            print(f"{Fore.CYAN}输出模板: {ydl_opts_download['outtmpl']}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}选择格式: {format_id}{Style.RESET_ALL}")
            ydl.download([url])

            time.sleep(0.5)  # 短暂等待确保文件系统更新
            print(f"{Fore.GREEN}[成功]{Style.RESET_ALL} 文件已保存到目录: {os.path.abspath(output_dir)}")

        except yt_dlp.utils.DownloadError as e:
            print(f"\n{Fore.RED}[错误]{Style.RESET_ALL} 下载失败: {e}")
            print("可能原因：网络问题、格式不可用、需要登录或受地理限制。")
        except Exception as e:
            print(f"\n{Fore.RED}[错误]{Style.RESET_ALL} 下载过程中发生未知错误: {e}")


def extract_domain_from_url(url):
    """
    从 URL 中提取主域名

    Args:
        url: 目标 URL

    Returns:
        主域名字符串，提取失败返回 None
    """
    try:
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc

        # 移除端口号
        if ':' in domain:
            domain = domain.split(':')[0]

        # 提取主域名（如 www.bilibili.com -> bilibili.com）
        domain_parts = domain.split('.')
        if len(domain_parts) > 2:
            domain = '.'.join(domain_parts[-2:])

        return domain
    except Exception:
        return None


def get_possible_cookie_files(domain):
    """
    获取可能的 Cookie 文件名列表（按优先级）

    Args:
        domain: 主域名

    Returns:
        可能的 Cookie 文件名列表
    """
    return [
        f"{domain}.ck",                      # 完整域名 cookie (如 bilibili.com.ck)
        f"{domain.replace('.', '_')}.ck",   # 带下划线的域名 (如 bilibili_com.ck)
    ] + DEFAULT_COOKIE_FILES                # 通用 cookie 文件


def convert_cookie_to_netscape(ck_path, domain):
    """
    将原始 Cookie 文件转换为 Netscape 格式

    Args:
        ck_path: Cookie 文件路径
        domain: 域名

    Returns:
        转换成功返回 True，失败返回 False
    """
    try:
        with open(ck_path, 'r', encoding='utf-8') as f:
            raw_cookie = f.read().strip()

        cookie_lines = []
        for part in raw_cookie.split(';'):
            part = part.strip()
            if '=' in part:
                name, value = part.split('=', 1)
                cookie_lines.append(f"{domain}\tTRUE\t/\tFALSE\t0\t{name}\t{value}")

        if cookie_lines:
            # 覆盖原文件为 Netscape 格式
            with open(ck_path, 'w', encoding='utf-8') as f:
                f.write(NETSCAPE_COOKIE_HEADER)
                f.write("\n".join(cookie_lines))

            print(f"{Fore.GREEN}[成功]{Style.RESET_ALL} 已加载并转换 Cookie: {ck_path}")
            return True

    except Exception as e:
        print(f"{Fore.RED}[错误]{Style.RESET_ALL} Cookie 文件处理失败: {e}")

    return False


def prepare_cookies_netscape(target_url):
    """
    准备并转换 Cookie 文件为 Netscape 格式

    Args:
        target_url: 目标 URL

    Returns:
        Cookie 文件路径，如果没有找到或转换失败则返回 None
    """
    cookies_dir = os.path.join(os.getcwd(), COOKIES_DIR)
    if not os.path.isdir(cookies_dir):
        return None

    # 提取域名
    domain = extract_domain_from_url(target_url)
    if not domain:
        return None

    # 获取可能的 Cookie 文件列表
    possible_files = get_possible_cookie_files(domain)

    # 检查 Cookie 文件是否存在并转换
    for filename in possible_files:
        ck_path = os.path.join(cookies_dir, filename)
        if os.path.exists(ck_path):
            if convert_cookie_to_netscape(ck_path, domain):
                return ck_path

    return None