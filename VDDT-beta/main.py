from downloader_core import prepare_cookies_netscape
from downloader_handler import handle_single_download
import os
import yt_dlp
import sys
import colorama
from colorama import Fore, Style
from check_deps import check_and_install

if not check_and_install():
    sys.exit(1)


def main():
    print("=" * 40)
    print(f"{Fore.CYAN}欢迎使用 VDDT 多功能下载器{Style.RESET_ALL}")
    print(f"{Fore.CYAN}作者: Alex (基于 yt-dlp){Style.RESET_ALL}")
    print(f"{Fore.CYAN}版本: 2.0.5-beta{Style.RESET_ALL}")
    print("=" * 40)
    print("确保已安装 yt-dlp")
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
    }

    if ydl_opts['cookiefile']:
        print(f"{Fore.CYAN}使用 Cookie 文件:{Style.RESET_ALL} {cookie_file}")
    else:
        print(f"{Fore.YELLOW}[提示]{Style.RESET_ALL} 未找到 Cookie 文件 。某些视频可能需要登录才能下载。")

    print("\n请选择操作：")
    print("0. 退出脚本")
    print("1. 下载单个视频/链接")
    print("2. 批量下载 (从文本文件读取链接)")
    print("3. 离线转码文件夹中的视频文件")

    while True:
        choice = input("输入编号 (0-3): ").strip()
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
        elif choice == '3':
            from offline_transcoder import run_offline_transcoder
            run_offline_transcoder()
            break
        else:
            print(f"{Fore.RED}无效选择，请输入 0, 1, 2 或 3。{Style.RESET_ALL}")

    print("\n" + "=" * 40)
    print(f"{Fore.CYAN}所有任务已完成。{Style.RESET_ALL}")
    print("=" * 40)

if __name__ == '__main__':
    main()

