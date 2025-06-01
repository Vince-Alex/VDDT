import yt_dlp
import os
import re
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
                size_str = "-"
                if item[6]:
                    filesize = item[6]
                    if filesize > 1024 * 1024 * 1024:
                        size_str = f"{filesize / (1024 * 1024 * 1024):.2f} GB"
                    elif filesize > 1024 * 1024:
                        size_str = f"{filesize / (1024 * 1024):.2f} MB"
                    elif filesize > 1024:
                        size_str = f"{filesize / 1024:.2f} KB"
                    else:
                        size_str = f"{filesize} B"
                else:
                    size_str = "-"

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
                date_str = datetime.strptime(upload_date_str, '%Y%m%d').strftime('%Y-%m-%d')
            except ValueError:
                date_str = datetime.now().strftime('%Y-%m-%d')
        else:
            date_str = datetime.now().strftime('%Y-%m-%d')

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

def handle_single_download(url, base_ydl_opts, output_dir):
    """
    处理单个 URL 的下载过程
    """
    current_ydl_opts = base_ydl_opts.copy()
    current_ydl_opts['postprocessors'] = []

    print("\n请选择下载模式：")
    print("1. 视频+音频 (自动合并最高画质)")
    print("2. 仅视频 (选择格式, 无音频)")
    print("3. 仅音频 (MP3格式)")
    print("4. 手动选择视频+音频格式")

    mode = input("输入编号 (1-4): ").strip()

    info_dict = None
    formats = []
    format_list_display = []

    if mode in ['1', '2', '4']:
        info_dict, formats, format_list_display = get_format_lists(url, current_ydl_opts)
        if not formats:
            print(f"{Fore.RED}[错误]{Style.RESET_ALL} 无法获取视频信息，跳过此链接。")
            return

    chosen_format_id = None
    if mode == '1':
        best_video_format = suggest_best_quality(formats)
        if best_video_format:
            chosen_format_id = f"{best_video_format}+bestaudio/best"
            print(f"{Fore.CYAN}[自动]{Style.RESET_ALL} 选择最佳视频格式 ({best_video_format}) + 最佳音频，将合并。")
            current_ydl_opts['merge_output_format'] = 'mp4'
        else:
            print(f"{Fore.YELLOW}[警告]{Style.RESET_ALL} 未找到合适的视频格式，尝试下载最佳格式。")
            chosen_format_id = 'best'

    elif mode == '2':
        print("\n请选择仅视频格式:")
        video_only_formats = [(i, f_id, ext, res, vc, ac, size) for i, f_id, ext, res, vc, ac, size in format_list_display if vc != '-']
        if not video_only_formats:
            print(f"{Fore.RED}[错误]{Style.RESET_ALL} 未找到仅视频格式。")
            return

        for item in video_only_formats:
            size_str = "-" if not item[6] else f"{item[6] / (1024*1024):.2f} MB"
            print(f"{item[0]:<5} {item[1]:<10} {item[2]:<8} {item[3]:<15} {item[4]:<15} {item[5]:<15} {size_str:<15}")

        while True:
            try:
                choice_idx = int(input("请输入格式序号: ").strip())
                chosen_format_tuple = next((f for f in format_list_display if f[0] == choice_idx), None)
                if chosen_format_tuple and chosen_format_tuple[4] != '-':
                    chosen_format_id = chosen_format_tuple[1]
                    current_ydl_opts['format'] = chosen_format_id
                    print(f"{Fore.CYAN}[选择]{Style.RESET_ALL} 格式: {chosen_format_id} (仅视频)")
                    break
                else:
                    print(f"{Fore.RED}无效序号或非视频格式，请重试。{Style.RESET_ALL}")
            except (ValueError, IndexError):
                print(f"{Fore.RED}无效输入，请输入数字序号。{Style.RESET_ALL}")

    elif mode == '3':
        print(f"{Fore.CYAN}[提示]{Style.RESET_ALL} 正在准备音频下载...")
        chosen_format_id = 'bestaudio'
        current_ydl_opts['postprocessors'].append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        })
        info_dict_audio, _, _ = get_format_lists(url, current_ydl_opts)
        if not info_dict_audio:
            print(f"{Fore.YELLOW}[警告]{Style.RESET_ALL} 无法获取视频信息，将使用默认命名。")
            info_dict = None
        else:
            info_dict = info_dict_audio
        print(f"{Fore.CYAN}[选择]{Style.RESET_ALL} 仅音频 (将转换为 MP3 192kbps)")

    elif mode == '4':
        print(f"{Fore.CYAN}[提示]{Style.RESET_ALL} 选择纯视频格式将自动合并最佳音频")
        while True:
            try:
                choice_idx = int(input("请输入格式序号 (视频+音频将自动合并): ").strip())
                chosen_format_tuple = next((f for f in format_list_display if f[0] == choice_idx), None)
                if chosen_format_tuple:
                    chosen_format_id = chosen_format_tuple[1]
                    selected_format_info = next((f for f in formats if f.get('format_id') == chosen_format_id), None)
                    if selected_format_info and selected_format_info.get('vcodec') != 'none' and selected_format_info.get('acodec') == 'none':
                        chosen_format_id = f"{chosen_format_id}+bestaudio/best"
                        current_ydl_opts['merge_output_format'] = 'mp4'
                    elif selected_format_info and selected_format_info.get('vcodec') == 'none':
                        print(f"{Fore.CYAN}[信息]{Style.RESET_ALL} 选择的是纯音频格式。")
                    else:
                        print(f"{Fore.CYAN}[信息]{Style.RESET_ALL} 选择的格式包含视频和音频。")
                    print(f"{Fore.CYAN}[选择]{Style.RESET_ALL} 格式: {chosen_format_id}")
                    break
                else:
                    print(f"{Fore.RED}无效序号，请从列表选择。{Style.RESET_ALL}")
            except (ValueError, IndexError):
                print(f"{Fore.RED}无效输入，请输入数字序号。{Style.RESET_ALL}")

    else:
        print(f"{Fore.RED}[错误]{Style.RESET_ALL} 无效模式选择。")
        return

    if chosen_format_id is None:
        print(f"{Fore.RED}[错误]{Style.RESET_ALL} 未选择有效的下载格式。")
        return

    if ask("是否使用自定义文件名模板?"):
        print("可用变量:")
        print("  - %(title)s: 视频标题")
        print("  - %(uploader)s: 上传者名称")
        print("  - %(upload_date)s: 上传日期 (格式: YYYYMMDD)")
        print("  - %(ext)s: 文件扩展名")
        print("  - %(id)s: 视频 ID")
        print("  - %(resolution)s: 分辨率")
        print("示例模板:")
        print("  - %(title)s.%(ext)s")
        print("  - %(upload_date)s_%(title)s.%(ext)s")
        print("  - %(uploader)s_%(title)s.%(ext)s")
        custom_template = input("请输入自定义文件名模板: ").strip()
        if custom_template:
            current_ydl_opts['outtmpl'] = os.path.join(output_dir, custom_template)
        else:
            print(f"{Fore.RED}[错误]{Style.RESET_ALL} 模板为空，使用默认模板。")

    if chosen_format_id:
        if ask("是否下载字幕 (若可用)?"):
            current_ydl_opts['writesubtitles'] = True
            current_ydl_opts['writeautomaticsub'] = True
            current_ydl_opts['subtitleslangs'] = ['zh-Hans', 'zh-CN', 'en', 'all']
            current_ydl_opts['subtitlesformat'] = 'srt/vtt'

        if ask("是否下载并嵌入视频封面?"):
            current_ydl_opts['writethumbnail'] = True
            current_ydl_opts['postprocessors'].append({
                'key': 'EmbedThumbnail',
                'already_have_thumbnail': False
            })
            current_ydl_opts['postprocessors'].append({'key': 'FFmpegMetadata'})

        if 'bilibili.com' in url.lower() and ask("是否尝试下载弹幕 (B站)?"):
            current_ydl_opts['writecomments'] = True

        if ask("是否在下载后进行转码或调整分辨率?"):
            print("\n请选择预设分辨率/码率 (或输入 '自定义'):")
            presets = {
                '1': '720p MP4 (推荐)',
                '2': '1080p MP4',
                '3': '仅音频 MP3 (192kbps)',
                '4': '1500k 码率 MP4',
                '5': '自定义分辨率或码率'
            }
            for key, value in presets.items():
                print(f"{key}. {value}")

            while True:
                preset_choice = input("输入选项编号: ").strip().lower()
                pp_args = []

                if preset_choice == '1':
                    pp_args.extend(['-vf', 'scale=-2:720', '-c:v', 'libx264', '-crf', '23', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k'])
                    current_ydl_opts['merge_output_format'] = 'mp4'
                    print(f"{Fore.CYAN}[转码]{Style.RESET_ALL} 选择预设: 720p MP4")
                    break
                elif preset_choice == '2':
                    pp_args.extend(['-vf', 'scale=-2:1080', '-c:v', 'libx264', '-crf', '22', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k'])
                    current_ydl_opts['merge_output_format'] = 'mp4'
                    print(f"{Fore.CYAN}[转码]{Style.RESET_ALL} 选择预设: 1080p MP4")
                    break
                elif preset_choice == '3':
                    chosen_format_id = 'bestaudio'
                    current_ydl_opts['postprocessors'].append({
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192'
                    })
                    print(f"{Fore.CYAN}[转码]{Style.RESET_ALL} 选择预设: 仅音频 MP3 (将跳过视频下载)")
                    break
                elif preset_choice == '4':
                    pp_args.extend(['-b:v', '1500k', '-c:v', 'libx264', '-preset', 'medium', '-c:a', 'aac', '-b:a', '128k'])
                    current_ydl_opts['merge_output_format'] = 'mp4'
                    print(f"{Fore.CYAN}[转码]{Style.RESET_ALL} 选择预设: 1500k 码率 MP4")
                    break
                elif preset_choice == '5':
                    res = input("请输入目标分辨率高度 (如 720) 或 视频码率 (如 1500k): ").strip().lower()
                    if res.isdigit() or res.endswith('p'):
                        height = res.replace('p', '')
                        if height.isdigit():
                            pp_args.extend(['-vf', f'scale=-2:{height}'])
                            print(f"{Fore.CYAN}[转码]{Style.RESET_ALL} 设置分辨率高度: {height}p")
                            break
                        else:
                            print(f"{Fore.RED}[警告]{Style.RESET_ALL} 无效分辨率输入，请重试。")
                    elif res.endswith('k'):
                        bitrate = res
                        pp_args.extend(['-b:v', bitrate])
                        print(f"{Fore.CYAN}[转码]{Style.RESET_ALL} 设置视频码率: {bitrate}")
                        break
                    else:
                        print(f"{Fore.RED}[警告]{Style.RESET_ALL} 无效输入，请输入数字高度 (如 720) 或码率 (如 1500k)。")
                else:
                    print(f"{Fore.RED}无效选项，请重新输入。{Style.RESET_ALL}")

            if pp_args and preset_choice not in ['3']:
                current_ydl_opts['postprocessors'].append({
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                })
                current_ydl_opts['postprocessor_args'] = pp_args
                current_ydl_opts['postprocessors'].append({'key': 'FFmpegMetadata'})

        download(url, chosen_format_id, output_dir, current_ydl_opts, info_dict)

    else:
        print(f"{Fore.YELLOW}[信息]{Style.RESET_ALL} 未选择格式，跳过下载。")

# 在 prepare_cookies_netscape 函数中做如下修改
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

def main():
    """
    运行下载器脚本的主函数
    """
    print("=" * 40)
    print(f"{Fore.CYAN}欢迎使用 VDDT 多功能下载器{Style.RESET_ALL}")
    print(f"{Fore.CYAN}作者: Alex (基于 yt-dlp){Style.RESET_ALL}")
    print(f"{Fore.CYAN}版本: 1.2.0{Style.RESET_ALL}")
    print("=" * 40)
    print("确保已安装 yt-dlp (`pip install yt-dlp`)")
    print("以及 ffmpeg (用于合并、转码、嵌入封面等)")
    print("-" * 40)

    cookie_file = None
    output_dir = 'VDDT_Downloads'
    os.makedirs(output_dir, exist_ok=True)
    print(f"{Fore.CYAN}下载目录:{Style.RESET_ALL} {os.path.abspath(output_dir)}")

    ydl_opts = {
        'cookiefile': cookie_file if cookie_file and os.path.exists(cookie_file) else None,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'quiet': False,
        'no_warnings': True,
        'ignoreerrors': True,
        'nocheckcertificate': True,
        'http_headers': {'Referer': 'https://www.bilibili.com/'}
    }

    if ydl_opts['cookiefile']:
        print(f"{Fore.CYAN}使用 Cookie 文件:{Style.RESET_ALL} {cookie_file}")
    else:
        print(f"{Fore.YELLOW}[提示]{Style.RESET_ALL} 未找到 Cookie 文件 。某些视频可能需要登录才能下载。")

    print("\n请选择操作：")
    print("0. 退出脚本")
    print("1. 下载单个视频/链接")
    print("2. 批量下载 (从文本文件读取链接)")

    while True:
        choice = input("输入编号 (0-2): ").strip()
        if choice == '0':
            print(f"{Fore.CYAN}感谢使用 VDDT 下载器，再见！{Style.RESET_ALL}")
            sys.exit(0)
        elif choice == '1':
            url = input("请输入视频链接: ").strip()
            cookie_file = prepare_cookies_netscape(url)
            if not url:
                print(f"{Fore.RED}[错误]{Style.RESET_ALL} 未输入链接。")
            else:
                handle_single_download(url, ydl_opts, output_dir)
            break
        elif choice == '2':
            default_batch_file = 'download_list.txt'
            file_path_prompt = f"请输入包含链接的文本文件路径 (默认为: {default_batch_file}): "
            file_path = input(file_path_prompt).strip()
            if not file_path:
                file_path = default_batch_file

            if not os.path.exists(file_path):
                print(f"{Fore.RED}[错误]{Style.RESET_ALL} 文件 '{file_path}' 不存在。请创建该文件并将视频链接放入其中，每行一个。")
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        pass
                    print(f"{Fore.CYAN}[信息]{Style.RESET_ALL} 已创建空文件 '{file_path}'。请在其中添加链接后重新运行。")
                except IOError as e:
                    print(f"{Fore.RED}[错误]{Style.RESET_ALL} 无法创建文件 '{file_path}': {e}")
                return

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    links = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                if not links:
                    print(f"{Fore.RED}[错误]{Style.RESET_ALL} 文件 '{file_path}' 为空或只包含注释。")
                    return

                print(f"\n{Fore.CYAN}批量处理{Style.RESET_ALL} 找到 {len(links)} 个有效链接")
                for i, url in enumerate(links):
                    print(f"\n{Fore.YELLOW}{'-'*40}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}[任务 {i+1}/{len(links)}]{Style.RESET_ALL} 链接: {url[:60]}{'...' if len(url) > 60 else ''}")
                    handle_single_download(url, ydl_opts.copy(), output_dir)
                    print(f"{Fore.YELLOW}{'-'*40}{Style.RESET_ALL}")

            except IOError as e:
                print(f"{Fore.RED}[错误]{Style.RESET_ALL} 读取文件 '{file_path}' 时出错: {e}")
            except Exception as e:
                print(f"{Fore.RED}[错误]{Style.RESET_ALL} 处理批量下载时发生未知错误: {e}")
            break
        else:
            print(f"{Fore.RED}无效选择，请输入 0, 1 或 2。{Style.RESET_ALL}")

    print("\n" + "=" * 40)
    print(f"{Fore.CYAN}所有任务已完成。{Style.RESET_ALL}")
    print("=" * 40)

if __name__ == '__main__':
    main()
