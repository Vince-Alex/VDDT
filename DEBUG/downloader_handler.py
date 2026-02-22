"""
VDDT Downloader Handler Module
下载处理模块 - 处理用户交互和下载流程

改进点：
1. 集成日志系统
2. 集成配置管理
3. 更清晰的代码结构
4. 支持配置预设
5. 更好的错误处理
"""

import os
from typing import Optional, Dict, List, Any, Tuple
from enum import IntEnum

from colorama import Fore, Style

from logger import get_logger
from config import VDDTConfig, get_config
from downloader_core import DownloaderCore, FormatInfo, VideoInfo
from utils import (
    ask, input_with_default, select_from_list,
    sanitize_filename, format_filesize,
    DownloadError, FormatError
)


class DownloadMode(IntEnum):
    """下载模式枚举"""
    VIDEO_AUDIO = 1      # 视频+音频（自动合并最高画质）
    VIDEO_ONLY = 2       # 仅视频
    AUDIO_ONLY = 3       # 仅音频
    MANUAL_SELECT = 4    # 手动选择格式


class TranscodePreset(IntEnum):
    """转码预设枚举"""
    P720 = 1       # 720p MP4
    P1080 = 2      # 1080p MP4
    MP3 = 3        # 仅音频 MP3
    B1500K = 4     # 1500k 码率
    CUSTOM = 5     # 自定义


# 转码预设配置
TRANSCODE_PRESETS: Dict[int, Dict[str, Any]] = {
    TranscodePreset.P720: {
        'name': '720p MP4 (推荐)',
        'args': ['-vf', 'scale=-2:720', '-c:v', 'libx264', '-crf', '23', 
                 '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k'],
        'format': 'mp4'
    },
    TranscodePreset.P1080: {
        'name': '1080p MP4',
        'args': ['-vf', 'scale=-2:1080', '-c:v', 'libx264', '-crf', '22', 
                 '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k'],
        'format': 'mp4'
    },
    TranscodePreset.MP3: {
        'name': '仅音频 MP3 (192kbps)',
        'audio_only': True,
        'format': 'mp3'
    },
    TranscodePreset.B1500K: {
        'name': '1500k 码率 MP4',
        'args': ['-b:v', '1500k', '-c:v', 'libx264', '-preset', 'medium', 
                 '-c:a', 'aac', '-b:a', '128k'],
        'format': 'mp4'
    },
    TranscodePreset.CUSTOM: {
        'name': '自定义分辨率或码率',
        'custom': True
    }
}


class DownloadHandler:
    """下载处理器类"""
    
    def __init__(self, config: Optional[VDDTConfig] = None):
        """
        Args:
            config: 配置对象，如果为 None 则使用全局配置
        """
        self.config = config or get_config()
        self.logger = get_logger()
        self.core = DownloaderCore(self.config)
    
    def handle_single_download(self, url: str, base_ydl_opts: Dict[str, Any],
                                output_dir: str, mode: Optional[int] = None) -> bool:
        """处理单个 URL 的下载过程
        
        Args:
            url: 视频 URL
            base_ydl_opts: 基础 yt-dlp 选项
            output_dir: 输出目录
            mode: 预设下载模式
        
        Returns:
            是否成功
        """
        self.logger.info(f"开始处理下载: {url}")
        
        current_ydl_opts = base_ydl_opts.copy()
        current_ydl_opts['postprocessors'] = []
        
        # 1. 选择下载模式
        if mode is not None and mode in DownloadMode:
            mode = DownloadMode(mode)
        else:
            mode = self._select_download_mode()
        
        if mode is None:
            return False
        
        # 2. 获取视频信息和格式
        video_info, formats = self._get_video_info(url, mode, current_ydl_opts)
        if mode != DownloadMode.AUDIO_ONLY and not formats:
            return False
        
        # 3. 选择格式
        chosen_format = self._select_format(mode, formats, current_ydl_opts)
        if chosen_format is None:
            return False
        
        # 4. 配置文件名
        self._configure_filename(current_ydl_opts, output_dir, video_info)
        
        # 5. 配置附加选项
        self._configure_extras(url, current_ydl_opts, video_info)
        
        # 6. 配置转码
        self._configure_transcode(chosen_format, current_ydl_opts, formats)
        
        # 7. 执行下载
        info_dict = video_info.raw_info if video_info else None
        return self.core.download(url, chosen_format, output_dir, current_ydl_opts, info_dict)
    
    def _select_download_mode(self) -> Optional[DownloadMode]:
        """选择下载模式"""
        print("\n请选择下载模式：")
        print("1. 视频+音频 (自动合并最高画质)")
        print("2. 仅视频 (选择格式, 无音频)")
        print("3. 仅音频 (MP3格式)")
        print("4. 手动选择视频+音频格式")
        
        while True:
            try:
                choice = input("输入编号 (1-4): ").strip()
                mode = int(choice)
                
                if mode in DownloadMode:
                    self.logger.debug(f"选择下载模式: {mode}")
                    return DownloadMode(mode)
                else:
                    print(f"{Fore.RED}无效选择，请输入 1-4{Style.RESET_ALL}")
                    
            except ValueError:
                print(f"{Fore.RED}请输入数字{Style.RESET_ALL}")
            except (EOFError, KeyboardInterrupt):
                self.logger.info("用户取消选择")
                return None
    
    def _get_video_info(self, url: str, mode: DownloadMode,
                         ydl_opts: Dict) -> Tuple[Optional[VideoInfo], List[FormatInfo]]:
        """获取视频信息"""
        if mode == DownloadMode.AUDIO_ONLY:
            # 音频模式也需要获取信息用于命名
            video_info, formats = self.core.get_format_lists(url, ydl_opts)
            if not video_info:
                print(f"{Fore.YELLOW}[警告]{Style.RESET_ALL} 无法获取视频信息，将使用默认命名。")
            return video_info, []
        
        video_info, formats = self.core.get_format_lists(url, ydl_opts)
        if not formats:
            print(f"{Fore.RED}[错误]{Style.RESET_ALL} 无法获取视频信息，跳过此链接。")
            return None, []
        
        return video_info, formats
    
    def _select_format(self, mode: DownloadMode, formats: List[FormatInfo],
                        ydl_opts: Dict) -> Optional[str]:
        """选择下载格式"""
        if mode == DownloadMode.VIDEO_AUDIO:
            return self._auto_select_best(formats, ydl_opts)
        elif mode == DownloadMode.VIDEO_ONLY:
            return self._select_video_only_format(formats)
        elif mode == DownloadMode.AUDIO_ONLY:
            return self._select_audio_format(ydl_opts)
        elif mode == DownloadMode.MANUAL_SELECT:
            return self._manual_select_format(formats, ydl_opts)
        
        return None
    
    def _auto_select_best(self, formats: List[FormatInfo],
                           ydl_opts: Dict) -> str:
        """自动选择最佳格式"""
        best_video = self.core.suggest_best_quality(formats)
        
        if best_video:
            format_id = f"{best_video}+bestaudio/best"
            ydl_opts['merge_output_format'] = 'mp4'
            print(f"{Fore.CYAN}[自动]{Style.RESET_ALL} 选择最佳视频格式 ({best_video}) + 最佳音频，将合并。")
            self.logger.info(f"自动选择格式: {format_id}")
            return format_id
        else:
            print(f"{Fore.YELLOW}[警告]{Style.RESET_ALL} 未找到合适的视频格式，尝试下载最佳格式。")
            return 'best'
    
    def _select_video_only_format(self, formats: List[FormatInfo]) -> Optional[str]:
        """选择仅视频格式"""
        video_formats = [f for f in formats if f.is_video_only]
        
        if not video_formats:
            print(f"{Fore.RED}[错误]{Style.RESET_ALL} 未找到仅视频格式。")
            return None
        
        print("\n请选择仅视频格式:")
        for f in video_formats:
            print(f"{f.index:<5} {f.format_id:<10} {f.extension:<8} "
                  f"{f.resolution:<15} {f.video_codec:<15} {f.filesize_str:<15}")
        
        while True:
            try:
                choice = int(input("请输入格式序号: ").strip())
                selected = next((f for f in formats if f.index == choice), None)
                
                if selected and selected.is_video_only:
                    self.logger.info(f"选择仅视频格式: {selected.format_id}")
                    return selected.format_id
                else:
                    print(f"{Fore.RED}无效序号或非视频格式，请重试。{Style.RESET_ALL}")
                    
            except ValueError:
                print(f"{Fore.RED}请输入数字序号。{Style.RESET_ALL}")
            except (EOFError, KeyboardInterrupt):
                return None
    
    def _select_audio_format(self, ydl_opts: Dict) -> str:
        """选择音频格式"""
        print(f"{Fore.CYAN}[提示]{Style.RESET_ALL} 正在准备音频下载...")
        
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        })
        
        print(f"{Fore.CYAN}[选择]{Style.RESET_ALL} 仅音频 (将转换为 MP3 192kbps)")
        self.logger.info("选择音频格式: bestaudio -> MP3")
        
        return 'bestaudio'
    
    def _manual_select_format(self, formats: List[FormatInfo],
                               ydl_opts: Dict) -> Optional[str]:
        """手动选择格式"""
        print(f"{Fore.CYAN}[提示]{Style.RESET_ALL} 选择纯视频格式将自动合并最佳音频")
        
        while True:
            try:
                choice = int(input("请输入格式序号 (视频+音频将自动合并): ").strip())
                selected = next((f for f in formats if f.index == choice), None)
                
                if not selected:
                    print(f"{Fore.RED}无效序号，请从列表选择。{Style.RESET_ALL}")
                    continue
                
                format_id = selected.format_id
                
                # 检查是否需要合并音频
                if selected.is_video_only:
                    format_id = f"{format_id}+bestaudio/best"
                    ydl_opts['merge_output_format'] = 'mp4'
                    print(f"{Fore.CYAN}[信息]{Style.RESET_ALL} 纯视频格式，将自动合并最佳音频。")
                elif selected.is_audio_only:
                    print(f"{Fore.CYAN}[信息]{Style.RESET_ALL} 选择的是纯音频格式。")
                else:
                    print(f"{Fore.CYAN}[信息]{Style.RESET_ALL} 选择的格式包含视频和音频。")
                
                print(f"{Fore.CYAN}[选择]{Style.RESET_ALL} 格式: {format_id}")
                self.logger.info(f"手动选择格式: {format_id}")
                return format_id
                
            except ValueError:
                print(f"{Fore.RED}请输入数字序号。{Style.RESET_ALL}")
            except (EOFError, KeyboardInterrupt):
                return None
    
    def _configure_filename(self, ydl_opts: Dict, output_dir: str,
                            video_info: Optional[VideoInfo]) -> None:
        """配置文件名"""
        if not ask("是否使用自定义文件名模板?", default=False):
            # 使用默认模板
            template = self.config.download.filename_template
            if template:
                ydl_opts['outtmpl'] = os.path.join(output_dir, template)
            return
        
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
        
        custom = input("请输入自定义文件名模板: ").strip()
        if custom:
            ydl_opts['outtmpl'] = os.path.join(output_dir, custom)
            self.logger.info(f"使用自定义文件名模板: {custom}")
        else:
            print(f"{Fore.RED}[错误]{Style.RESET_ALL} 模板为空，使用默认模板。")
    
    def _configure_extras(self, url: str, ydl_opts: Dict,
                          video_info: Optional[VideoInfo]) -> None:
        """配置附加选项（字幕、封面、弹幕）"""
        # 字幕
        if ask("是否下载字幕 (若可用)?", default=self.config.download.download_subtitles):
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = self.config.download.subtitle_languages
            ydl_opts['subtitlesformat'] = 'srt/vtt'
            self.logger.info("启用字幕下载")
        
        # 封面
        if ask("是否下载并嵌入视频封面?", default=self.config.download.embed_thumbnail):
            ydl_opts['writethumbnail'] = True
            ydl_opts['postprocessors'].append({
                'key': 'EmbedThumbnail',
                'already_have_thumbnail': False
            })
            ydl_opts['postprocessors'].append({'key': 'FFmpegMetadata'})
            self.logger.info("启用封面嵌入")
        
        # 弹幕（仅 B 站）
        if 'bilibili.com' in url.lower():
            if ask("是否尝试下载弹幕 (B站)?", default=self.config.download.download_danmaku):
                ydl_opts['writecomments'] = True
                self.logger.info("启用弹幕下载")
    
    def _configure_transcode(self, format_id: str, ydl_opts: Dict,
                              formats: List[FormatInfo]) -> None:
        """配置转码选项"""
        if not ask("是否在下载后进行转码或调整分辨率?", default=False):
            return
        
        print("\n请选择预设分辨率/码率 (或输入 '自定义'):")
        for key, preset in TRANSCODE_PRESETS.items():
            print(f"{key}. {preset['name']}")
        
        while True:
            choice = input("输入选项编号: ").strip().lower()
            
            try:
                preset_id = int(choice)
                
                if preset_id == TranscodePreset.CUSTOM:
                    self._configure_custom_transcode(ydl_opts)
                    break
                elif preset_id in TRANSCODE_PRESETS:
                    preset = TRANSCODE_PRESETS[preset_id]
                    
                    if preset.get('audio_only'):
                        # 仅音频预设
                        format_id = 'bestaudio'
                        ydl_opts['postprocessors'].append({
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192'
                        })
                    else:
                        # 视频预设
                        ydl_opts['merge_output_format'] = preset.get('format', 'mp4')
                        ydl_opts['postprocessors'].append({
                            'key': 'FFmpegVideoConvertor',
                            'preferedformat': preset.get('format', 'mp4'),
                        })
                        ydl_opts['postprocessor_args'] = preset['args']
                        ydl_opts['postprocessors'].append({'key': 'FFmpegMetadata'})
                    
                    print(f"{Fore.CYAN}[转码]{Style.RESET_ALL} 选择预设: {preset['name']}")
                    self.logger.info(f"转码预设: {preset['name']}")
                    break
                else:
                    print(f"{Fore.RED}无效选项，请重新输入。{Style.RESET_ALL}")
                    
            except ValueError:
                print(f"{Fore.RED}请输入数字。{Style.RESET_ALL}")
    
    def _configure_custom_transcode(self, ydl_opts: Dict) -> None:
        """配置自定义转码"""
        res = input("请输入目标分辨率高度 (如 720) 或 视频码率 (如 1500k): ").strip().lower()
        
        pp_args = []
        
        if res.isdigit() or res.endswith('p'):
            height = res.replace('p', '')
            if height.isdigit():
                pp_args = ['-vf', f'scale=-2:{height}', '-c:v', 'libx264', 
                          '-crf', '23', '-preset', 'medium', 
                          '-c:a', 'aac', '-b:a', '192k']
                print(f"{Fore.CYAN}[转码]{Style.RESET_ALL} 设置分辨率高度: {height}p")
                self.logger.info(f"自定义转码分辨率: {height}p")
        elif res.endswith('k'):
            pp_args = ['-b:v', res, '-c:v', 'libx264', '-preset', 'medium',
                      '-c:a', 'aac', '-b:a', '128k']
            print(f"{Fore.CYAN}[转码]{Style.RESET_ALL} 设置视频码率: {res}")
            self.logger.info(f"自定义转码码率: {res}")
        else:
            print(f"{Fore.RED}[警告]{Style.RESET_ALL} 无效输入，跳过转码。")
            return
        
        if pp_args:
            ydl_opts['merge_output_format'] = 'mp4'
            ydl_opts['postprocessors'].append({
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            })
            ydl_opts['postprocessor_args'] = pp_args
            ydl_opts['postprocessors'].append({'key': 'FFmpegMetadata'})


# ========== 向后兼容函数 ==========

def handle_single_download(url: str, base_ydl_opts: Dict, output_dir: str) -> None:
    """处理单个下载（向后兼容函数）"""
    handler = DownloadHandler()
    handler.handle_single_download(url, base_ydl_opts, output_dir)


# ========== 测试 ==========

if __name__ == '__main__':
    print("=== DownloadHandler 测试 ===")
    
    handler = DownloadHandler()
    
    print(f"配置加载成功:")
    print(f"  - 输出目录: {handler.config.download.output_dir}")
    print(f"  - 并发数: {handler.config.download.concurrent_downloads}")
    print(f"  - 重试次数: {handler.config.download.max_retries}")
    
    print("\n转码预设:")
    for key, preset in TRANSCODE_PRESETS.items():
        print(f"  {key}. {preset['name']}")
    
    print("\n模块加载成功！")
