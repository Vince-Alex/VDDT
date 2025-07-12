import os
import colorama
from colorama import Fore, Style
from downloader_core import suggest_best_quality, get_format_lists, download, prepare_cookies_netscape
from utils import ask, sanitize_filename

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


        download(url, chosen_format_id, output_dir, current_ydl_opts, info_dict)

    else:
        print(f"{Fore.YELLOW}[信息]{Style.RESET_ALL} 未选择格式，跳过下载。")

