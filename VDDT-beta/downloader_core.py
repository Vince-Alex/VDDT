import yt_dlp
import colorama
from colorama import Fore, Style
import os
import sys
import datetime
import urllib.parse
from utils import ask, sanitize_filename, progress_hook, convert_to_netscape_cookie

def suggest_best_quality(formats):
    """
    基于高度建议最佳可用视频质量的格式 ID
    """
    video_formats = [f for f in formats if f.get("vcodec") != "none" and f.get("height")]
    if not video_formats:
        return None
    sorted_formats = sorted(video_formats, key=lambda f: f.get("height", 0), reverse=True)
    return sorted_formats[0].get("format_id")

def get_format_lists(url, ydl_opts):
    """
    获取并列出给定 URL 的可用格式
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
                size_str = "-" if not item[6] else f"{item[6] / (1024*1024):.2f} MB"
                print(f"{item[0]:<5} {item[1]:<10} {item[2]:<8} {item[3]:<15} {item[4]:<15} {item[5]:<15} {size_str:<15}")
            print(f"{Fore.CYAN}-" * 83 + Style.RESET_ALL)
            return info, formats, format_list
        except yt_dlp.utils.DownloadError as e:
            print(f"\n{Fore.RED}[错误]{Style.RESET_ALL} 获取格式失败: {e}")
            print("请检查链接是否有效，或网络连接/代理设置。")
        except Exception as e:
            print(f"\n{Fore.RED}[错误]{Style.RESET_ALL} 获取格式时发生未知错误: {e}")
        return None, [], []

def download(url, format_id, output_dir, ydl_opts, info_dict=None):
    if info_dict:
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
        ydl_opts['outtmpl'] = os.path.join(output_dir, filename_template)
    else:
        ydl_opts['outtmpl'] = os.path.join(output_dir, '%(title)s.%(ext)s')

    ydl_opts_download = ydl_opts.copy()
    ydl_opts_download.update({
        'format': format_id,
        'progress_hooks': [progress_hook],
        'concurrent_fragment_downloads': 5,
        'fragment_retries': 10,
        'retries': 10,
        'postprocessors': ydl_opts.get('postprocessors', []),
    })

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

def prepare_cookies_netscape(target_url):
    cookies_dir = os.path.join(os.getcwd(), 'cookies')
    if not os.path.isdir(cookies_dir):
        return None
    
    # 从URL中提取主域名
    domain = None
    try:
        parsed_url = urllib.parse.urlparse(target_url)
        domain = parsed_url.netloc
        # 移除端口号
        if ':' in domain:
            domain = domain.split(':')[0]
        # 提取主域名（如 www.bilibili.com -> bilibili.com）
        domain_parts = domain.split('.')
        if len(domain_parts) > 2:
            domain = '.'.join(domain_parts[-2:])
    except Exception:
        pass
    
    if not domain:
        return None
    
    # 可能的cookie文件名列表（按优先级）
    possible_files = [
        f"{domain}.ck",                 # 完整域名 cookie (如 bilibili.com.ck)
        f"{domain.replace('.', '_')}.ck",  # 带下划线的域名 (如 bilibili_com.ck)
        "common.ck"                     # 通用cookie文件
    ]
    
    # 检查cookie文件是否存在
    for filename in possible_files:
        ck_path = os.path.join(cookies_dir, filename)
        if os.path.exists(ck_path):
            try:
                # 转换为Netscape格式
                with open(ck_path, 'r', encoding='utf-8') as f:
                    raw_cookie = f.read().strip()
                
                cookie_lines = []
                for part in raw_cookie.split(';'):
                    part = part.strip()
                    if '=' in part:
                        name, value = part.split('=', 1)
                        # 使用提取的域名
                        cookie_lines.append(f"{domain}\tTRUE\t/\tFALSE\t0\t{name}\t{value}")
                
                if cookie_lines:
                    # 覆盖原文件为Netscape格式
                    with open(ck_path, 'w', encoding='utf-8') as f:
                        f.write("# Netscape HTTP Cookie File\n")
                        f.write("\n".join(cookie_lines))
                    
                    print(f"{Fore.GREEN}[成功]{Style.RESET_ALL} 已加载并转换 Cookie: {ck_path}")
                    return ck_path
            except Exception as e:
                print(f"{Fore.RED}[错误]{Style.RESET_ALL} Cookie 文件处理失败: {e}")
    
    return None

