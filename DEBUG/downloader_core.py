"""
VDDT Downloader Core Module
下载核心模块 - 提供视频下载的核心功能

改进点：
1. 集成日志系统
2. 集成配置管理
3. 完整的类型提示
4. 更细化的异常处理
5. 支持自定义回调
"""

import os
import time
import urllib.parse
from typing import Optional, Dict, List, Any, Tuple, Callable
from dataclasses import dataclass

import yt_dlp
from colorama import Fore, Style

from logger import get_logger, VDDTLogger
from config import VDDTConfig, get_config, ConfigManager
from utils import (
    sanitize_filename, progress_hook, format_filesize,
    extract_domain, convert_to_netscape_cookie, parse_upload_date,
    DownloadError, FormatError, CookieError, retry_on_error
)


@dataclass
class FormatInfo:
    """格式信息"""
    index: int
    format_id: str
    extension: str
    resolution: str
    video_codec: str
    audio_codec: str
    filesize: Optional[int]
    
    @property
    def filesize_str(self) -> str:
        return format_filesize(self.filesize)
    
    @property
    def is_video_only(self) -> bool:
        return self.video_codec != '-' and self.audio_codec == '-'
    
    @property
    def is_audio_only(self) -> bool:
        return self.video_codec == '-' and self.audio_codec != '-'
    
    @property
    def has_video(self) -> bool:
        return self.video_codec != '-'


@dataclass
class VideoInfo:
    """视频信息"""
    title: str
    uploader: str
    upload_date: str
    duration: int
    description: str
    formats: List[FormatInfo]
    raw_info: Dict[str, Any]
    
    @classmethod
    def from_ytdlp(cls, info: Dict[str, Any]) -> 'VideoInfo':
        """从 yt-dlp 信息创建"""
        formats = []
        for i, f in enumerate(info.get('formats', [])):
            vcodec = f.get('vcodec', 'none')
            acodec = f.get('acodec', 'none')
            
            resolution = f.get('resolution')
            if not resolution:
                if vcodec != 'none' and f.get('height'):
                    resolution = f"{f.get('height')}p"
                else:
                    resolution = '仅音频'
            
            formats.append(FormatInfo(
                index=i + 1,
                format_id=f.get('format_id', '-'),
                extension=f.get('ext', '-'),
                resolution=resolution,
                video_codec=vcodec.replace('none', '-'),
                audio_codec=acodec.replace('none', '-'),
                filesize=f.get('filesize') or f.get('filesize_approx')
            ))
        
        return cls(
            title=info.get('title', '未知标题'),
            uploader=info.get('uploader', '未知上传者'),
            upload_date=parse_upload_date(info.get('upload_date')),
            duration=info.get('duration', 0),
            description=info.get('description', ''),
            formats=formats,
            raw_info=info
        )


class DownloaderCore:
    """下载器核心类"""
    
    def __init__(self, config: Optional[VDDTConfig] = None):
        """
        Args:
            config: 配置对象，如果为 None 则使用全局配置
        """
        self.config = config or get_config()
        self.logger = get_logger()
        self._progress_callback: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable[[Dict], None]) -> None:
        """设置进度回调函数
        
        Args:
            callback: 回调函数，接收进度信息字典
        """
        self._progress_callback = callback
    
    def _get_base_opts(self) -> Dict[str, Any]:
        """获取基础 yt-dlp 选项"""
        return {
            'user_agent': self.config.network.user_agent,
            'quiet': not self.config.ui.verbose,
            'no_warnings': not self.config.ui.verbose,
            'ignoreerrors': True,
            'nocheckcertificate': True,
            'socket_timeout': self.config.network.timeout,
        }
    
    def suggest_best_quality(self, formats: List[FormatInfo]) -> Optional[str]:
        """基于高度建议最佳视频质量
        
        Args:
            formats: 格式列表
        
        Returns:
            最佳格式的 ID，如果没有视频格式则返回 None
        """
        video_formats = [
            f for f in formats 
            if f.has_video and f.resolution != '仅音频'
        ]
        
        if not video_formats:
            return None
        
        # 按分辨率排序
        def get_height(f: FormatInfo) -> int:
            res = f.resolution
            if res and res.endswith('p'):
                try:
                    return int(res[:-1])
                except ValueError:
                    pass
            return 0
        
        sorted_formats = sorted(video_formats, key=get_height, reverse=True)
        return sorted_formats[0].format_id
    
    def get_format_lists(self, url: str, 
                         ydl_opts: Optional[Dict] = None) -> Tuple[Optional[VideoInfo], List[FormatInfo]]:
        """获取并列出给定 URL 的可用格式
        
        Args:
            url: 视频 URL
            ydl_opts: 额外的 yt-dlp 选项
        
        Returns:
            (VideoInfo, 格式列表) 元组，失败时返回 (None, [])
        """
        opts = self._get_base_opts()
        if ydl_opts:
            opts.update(ydl_opts)
        
        self.logger.info(f"正在获取视频信息: {url}")
        print(f"\n{Fore.CYAN}正在获取视频信息...{Style.RESET_ALL}")
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    self.logger.error("无法获取视频信息")
                    return None, []
                
                video_info = VideoInfo.from_ytdlp(info)
                formats = video_info.formats
                
                # 显示格式列表
                self._display_formats(formats)
                
                self.logger.info(f"获取到 {len(formats)} 个格式")
                return video_info, formats
                
        except yt_dlp.utils.DownloadError as e:
            self.logger.error(f"获取格式失败: {e}")
            print(f"\n{Fore.RED}[错误]{Style.RESET_ALL} 获取格式失败: {e}")
            print("请检查链接是否有效，或网络连接/代理设置。")
            return None, []
            
        except yt_dlp.utils.ExtractorError as e:
            self.logger.error(f"视频提取错误: {e}")
            print(f"\n{Fore.RED}[错误]{Style.RESET_ALL} 无法解析该视频链接")
            return None, []
            
        except Exception as e:
            self.logger.exception(f"获取格式时发生未知错误: {e}")
            print(f"\n{Fore.RED}[错误]{Style.RESET_ALL} 获取格式时发生未知错误: {e}")
            return None, []
    
    def _display_formats(self, formats: List[FormatInfo]) -> None:
        """显示格式列表"""
        print(f"\n{Fore.CYAN}可用格式:{Style.RESET_ALL}")
        print(f"{'序号':<5} {'格式ID':<10} {'扩展名':<8} {'分辨率':<15} {'视频编码':<15} {'音频编码':<15} {'大小':<15}")
        print(f"{Fore.CYAN}-" * 83 + Style.RESET_ALL)
        
        for f in formats:
            print(f"{f.index:<5} {f.format_id:<10} {f.extension:<8} "
                  f"{f.resolution:<15} {f.video_codec:<15} {f.audio_codec:<15} "
                  f"{f.filesize_str:<15}")
        
        print(f"{Fore.CYAN}-" * 83 + Style.RESET_ALL)
    
    def download(self, url: str, format_id: str, output_dir: str,
                 ydl_opts: Optional[Dict] = None,
                 info_dict: Optional[Dict] = None) -> bool:
        """执行下载
        
        Args:
            url: 视频 URL
            format_id: 格式 ID
            output_dir: 输出目录
            ydl_opts: 额外的 yt-dlp 选项
            info_dict: 视频信息字典（用于命名）
        
        Returns:
            是否成功
        """
        # 构建选项
        opts = self._get_base_opts()
        if ydl_opts:
            opts.update(ydl_opts)
        
        # 设置文件名模板
        if info_dict:
            title = sanitize_filename(info_dict.get('title', 'video'))
            author = sanitize_filename(info_dict.get('uploader', 'channel'))
            date_str = parse_upload_date(info_dict.get('upload_date'))
            
            filename_template = f"{date_str}_{author}_{title}.%(ext)s"
            opts['outtmpl'] = os.path.join(output_dir, filename_template)
        else:
            opts['outtmpl'] = os.path.join(output_dir, '%(title)s.%(ext)s')
        
        # 设置下载选项
        opts['format'] = format_id
        opts['progress_hooks'] = [self._progress_callback or progress_hook]
        opts['concurrent_fragment_downloads'] = self.config.download.concurrent_downloads
        opts['fragment_retries'] = self.config.download.max_retries
        opts['retries'] = self.config.download.max_retries
        
        self.logger.info(f"准备下载: {url}")
        self.logger.debug(f"格式: {format_id}, 输出目录: {output_dir}")
        
        print(f"\n{Fore.CYAN}准备下载...{Style.RESET_ALL}")
        print(f"{Fore.CYAN}输出模板: {opts['outtmpl']}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}选择格式: {format_id}{Style.RESET_ALL}")
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            
            # 短暂等待确保文件系统更新
            time.sleep(0.5)
            
            self.logger.info(f"下载完成，文件保存到: {output_dir}")
            print(f"{Fore.GREEN}[成功]{Style.RESET_ALL} 文件已保存到目录: {os.path.abspath(output_dir)}")
            return True
            
        except yt_dlp.utils.DownloadError as e:
            self.logger.error(f"下载失败: {e}")
            print(f"\n{Fore.RED}[错误]{Style.RESET_ALL} 下载失败: {e}")
            print("可能原因：网络问题、格式不可用、需要登录或受地理限制。")
            return False
            
        except yt_dlp.utils.PostProcessingError as e:
            self.logger.error(f"后处理失败: {e}")
            print(f"\n{Fore.RED}[错误]{Style.RESET_ALL} 后处理失败: {e}")
            return False
            
        except KeyboardInterrupt:
            self.logger.warning("用户中断下载")
            print(f"\n{Fore.YELLOW}[中断]{Style.RESET_ALL} 下载被用户取消")
            return False
            
        except Exception as e:
            self.logger.exception(f"下载过程中发生未知错误: {e}")
            print(f"\n{Fore.RED}[错误]{Style.RESET_ALL} 下载过程中发生未知错误: {e}")
            return False
    
    def prepare_cookies_netscape(self, target_url: str) -> Optional[str]:
        """准备 Cookie 文件
        
        Args:
            target_url: 目标 URL
        
        Returns:
            Cookie 文件路径，如果不需要或失败则返回 None
        """
        cookies_dir = os.path.join(os.getcwd(), 'cookies')
        
        if not os.path.isdir(cookies_dir):
            self.logger.debug("cookies 目录不存在")
            return None
        
        # 提取域名
        domain = extract_domain(target_url)
        if not domain:
            self.logger.warning(f"无法从 URL 提取域名: {target_url}")
            return None
        
        # 可能的 cookie 文件名列表（按优先级）
        possible_files = [
            f"{domain}.ck",                          # bilibili.com.ck
            f"{domain.replace('.', '_')}.ck",        # bilibili_com.ck
            "common.ck"                              # 通用 cookie
        ]
        
        # 检查 cookie 文件是否存在
        for filename in possible_files:
            ck_path = os.path.join(cookies_dir, filename)
            
            if os.path.exists(ck_path):
                try:
                    # 读取原始 cookie
                    with open(ck_path, 'r', encoding='utf-8') as f:
                        raw_cookie = f.read().strip()
                    
                    # 检查是否已经是 Netscape 格式
                    if raw_cookie.startswith('# Netscape'):
                        self.logger.info(f"Cookie 已是 Netscape 格式: {ck_path}")
                        print(f"{Fore.GREEN}[成功]{Style.RESET_ALL} 已加载 Cookie: {ck_path}")
                        return ck_path
                    
                    # 转换为 Netscape 格式
                    cookie_lines = ["# Netscape HTTP Cookie File"]
                    for part in raw_cookie.split(';'):
                        part = part.strip()
                        if '=' in part:
                            name, value = part.split('=', 1)
                            cookie_lines.append(
                                f".{domain}\tTRUE\t/\tFALSE\t0\t{name.strip()}\t{value.strip()}"
                            )
                    
                    if len(cookie_lines) > 1:
                        # 保存转换后的 cookie
                        with open(ck_path, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(cookie_lines))
                        
                        self.logger.info(f"Cookie 已转换并保存: {ck_path}")
                        print(f"{Fore.GREEN}[成功]{Style.RESET_ALL} 已加载并转换 Cookie: {ck_path}")
                        return ck_path
                        
                except IOError as e:
                    self.logger.error(f"Cookie 文件处理失败: {e}")
                    print(f"{Fore.RED}[错误]{Style.RESET_ALL} Cookie 文件处理失败: {e}")
                    
                except Exception as e:
                    self.logger.exception(f"Cookie 处理异常: {e}")
        
        self.logger.debug(f"未找到 {domain} 的 Cookie 文件")
        return None


# ========== 便捷函数（保持向后兼容）==========

def suggest_best_quality(formats: List) -> Optional[str]:
    """建议最佳质量（向后兼容函数）"""
    core = DownloaderCore()
    if formats and isinstance(formats[0], FormatInfo):
        return core.suggest_best_quality(formats)
    
    # 处理原始格式列表
    video_formats = [f for f in formats if f.get("vcodec") != "none" and f.get("height")]
    if not video_formats:
        return None
    sorted_formats = sorted(video_formats, key=lambda f: f.get("height", 0), reverse=True)
    return sorted_formats[0].get("format_id")


def get_format_lists(url: str, ydl_opts: Dict) -> Tuple[Optional[Dict], List, List]:
    """获取格式列表（向后兼容函数）"""
    core = DownloaderCore()
    video_info, formats = core.get_format_lists(url, ydl_opts)
    
    if video_info:
        # 转换为旧的返回格式
        format_list = [
            (f.index, f.format_id, f.extension, f.resolution,
             f.video_codec, f.audio_codec, f.filesize)
            for f in formats
        ]
        return video_info.raw_info, [f.__dict__ for f in formats], format_list
    
    return None, [], []


def download(url: str, format_id: str, output_dir: str,
             ydl_opts: Dict, info_dict: Optional[Dict] = None) -> None:
    """下载（向后兼容函数）"""
    core = DownloaderCore()
    core.download(url, format_id, output_dir, ydl_opts, info_dict)


def prepare_cookies_netscape(target_url: str) -> Optional[str]:
    """准备 Cookie（向后兼容函数）"""
    core = DownloaderCore()
    return core.prepare_cookies_netscape(target_url)


# ========== 测试 ==========

if __name__ == '__main__':
    # 测试核心功能
    print("=== 测试 DownloaderCore ===")
    
    core = DownloaderCore()
    
    # 测试域名提取
    print("\n域名提取测试:")
    urls = [
        "https://www.bilibili.com/video/BV1xx",
        "https://youtube.com/watch?v=test",
    ]
    for url in urls:
        print(f"  {url} -> {extract_domain(url)}")
    
    print("\n核心模块加载成功！")
