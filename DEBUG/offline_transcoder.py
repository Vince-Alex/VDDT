"""
VDDT Offline Transcoder Module
离线转码模块 - 提供视频文件的离线转码功能

改进点：
1. 集成日志系统
2. 更好的错误处理
3. 类型提示
4. 支持 AMV 和多种通用格式
5. 进度显示优化
"""

import os
import sys
import subprocess
from typing import Optional, List, Tuple, Dict, Any
from enum import IntEnum
from pathlib import Path

from colorama import Fore, Style

from logger import get_logger
from config import get_config
from utils import (
    ask, input_with_default, select_from_list,
    format_filesize, format_duration,
    TranscodeError, VDDTError
)


# ========== 常量定义 ==========

SUPPORTED_VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.flv', 
    '.wmv', '.m4v', '.ts', '.webm', '.mpg', '.mpeg'
}

AMV_PRESET = {
    'name': 'AMV (MP4 播放器专用)',
    'args': [
        '-s', '160x112',
        '-r', '30',
        '-c:v', 'amv',
        '-c:a', 'adpcm_ima_amv',
        '-block_size', '735',
        '-ac', '1',
        '-ar', '22050'
    ],
    'ext': 'amv'
}

TRANSCODE_FORMATS = {
    '1': {'name': 'MP4 (H.264)', 'ext': 'mp4', 'vcodec': 'libx264', 'acodec': 'aac'},
    '2': {'name': 'MKV', 'ext': 'mkv', 'vcodec': 'libx264', 'acodec': 'aac'},
    '3': {'name': 'AVI', 'ext': 'avi', 'vcodec': 'libx264', 'acodec': 'mp3'},
    '4': {'name': 'MOV', 'ext': 'mov', 'vcodec': 'libx264', 'acodec': 'aac'},
    '5': {'name': 'FLV', 'ext': 'flv', 'vcodec': 'libx264', 'acodec': 'aac'},
    '6': {'name': '自定义', 'ext': None},
}


class TranscodeMode(IntEnum):
    """转码模式"""
    AMV = 1
    GENERAL = 2


class OfflineTranscoder:
    """离线转码器类"""
    
    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        self.ffmpeg_path = self._find_ffmpeg()
    
    def _find_ffmpeg(self) -> Optional[str]:
        """查找 FFmpeg 可执行文件"""
        try:
            # 尝试直接调用 ffmpeg
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.logger.info("FFmpeg 已找到")
                return 'ffmpeg'
        except FileNotFoundError:
            self.logger.warning("FFmpeg 未找到")
        except subprocess.TimeoutExpired:
            self.logger.warning("FFmpeg 检查超时")
        except Exception as e:
            self.logger.error(f"FFmpeg 检查错误: {e}")
        
        return None
    
    def _check_ffmpeg(self) -> bool:
        """检查 FFmpeg 是否可用"""
        if not self.ffmpeg_path:
            print(f"{Fore.RED}[错误]{Style.RESET_ALL} FFmpeg 未安装或不在 PATH 中")
            print("请先安装 FFmpeg:")
            print("  Windows: https://www.gyan.dev/ffmpeg/builds/")
            print("  macOS: brew install ffmpeg")
            print("  Linux: sudo apt install ffmpeg")
            return False
        return True
    
    def get_video_files(self, folder: str) -> List[str]:
        """获取文件夹中的视频文件
        
        Args:
            folder: 文件夹路径
        
        Returns:
            视频文件路径列表
        """
        files = []
        
        try:
            for item in os.listdir(folder):
                item_path = os.path.join(folder, item)
                
                if os.path.isfile(item_path):
                    ext = os.path.splitext(item)[1].lower()
                    if ext in SUPPORTED_VIDEO_EXTENSIONS:
                        files.append(item_path)
        
        except PermissionError as e:
            self.logger.error(f"无法访问文件夹: {e}")
        except Exception as e:
            self.logger.exception(f"获取视频文件错误: {e}")
        
        return sorted(files)
    
    def parse_resolution(self, res_str: str) -> Optional[str]:
        """解析分辨率字符串
        
        Args:
            res_str: 分辨率字符串，如 "1920*1080", "720p", "1280x720"
        
        Returns:
            FFmpeg scale 过滤器参数
        """
        if not res_str:
            return None
        
        s = res_str.strip().lower()
        
        # 格式: 1920*1080 或 1920x1080
        if '*' in s:
            parts = s.split('*', 1)
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                return f"{parts[0]}:{parts[1]}"
        
        if 'x' in s:
            parts = s.split('x', 1)
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                return f"{parts[0]}:{parts[1]}"
        
        # 格式: 720p
        if s.endswith('p') and s[:-1].isdigit():
            return f"-2:{s[:-1]}"
        
        # 纯数字（高度）
        if s.isdigit():
            return f"-2:{s}"
        
        return None
    
    def get_video_info(self, filepath: str) -> Optional[Dict[str, Any]]:
        """获取视频信息
        
        Args:
            filepath: 视频文件路径
        
        Returns:
            视频信息字典
        """
        if not self._check_ffmpeg():
            return None
        
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format', '-show_streams',
                filepath
            ]
            
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                import json
                return json.loads(result.stdout)
        
        except FileNotFoundError:
            self.logger.warning("ffprobe 未找到")
        except subprocess.TimeoutExpired:
            self.logger.warning(f"获取视频信息超时: {filepath}")
        except Exception as e:
            self.logger.error(f"获取视频信息错误: {e}")
        
        return None
    
    def transcode(self, input_file: str, output_file: str,
                  args: List[str], show_progress: bool = True) -> bool:
        """执行转码
        
        Args:
            input_file: 输入文件
            output_file: 输出文件
            args: FFmpeg 参数列表
            show_progress: 是否显示进度
        
        Returns:
            是否成功
        """
        if not self._check_ffmpeg():
            return False
        
        self.logger.info(f"开始转码: {input_file} -> {output_file}")
        
        cmd = ['ffmpeg', '-i', input_file] + args + [output_file, '-y']
        
        try:
            # 检查是否有 ffmpeg_progress_yield
            try:
                from ffmpeg_progress_yield import FfmpegProgress
                from tqdm import tqdm
                
                if show_progress:
                    progress = FfmpegProgress(cmd)
                    with tqdm(total=100, desc="进度", unit="%", ncols=80) as bar:
                        for percent in progress.run_command_with_progress():
                            bar.n = percent
                            bar.refresh()
                    print(f"{Fore.GREEN}[完成] ✓{Style.RESET_ALL}")
                    return True
            except ImportError:
                pass
            
            # 没有进度显示库，使用普通方式
            print(f"{Fore.CYAN}转码中...{Style.RESET_ALL}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            
            if result.returncode == 0:
                print(f"{Fore.GREEN}[完成] ✓{Style.RESET_ALL}")
                self.logger.info(f"转码完成: {output_file}")
                return True
            else:
                self.logger.error(f"转码失败: {result.stderr}")
                print(f"{Fore.RED}[失败]{Style.RESET_ALL} 转码错误")
                return False
        
        except subprocess.TimeoutExpired:
            self.logger.error("转码超时")
            print(f"{Fore.RED}[超时]{Style.RESET_ALL} 转码时间过长")
            return False
        
        except FileNotFoundError:
            self.logger.error("FFmpeg 未找到")
            print(f"{Fore.RED}[错误]{Style.RESET_ALL} FFmpeg 未找到")
            return False
        
        except Exception as e:
            self.logger.exception(f"转码错误: {e}")
            print(f"{Fore.RED}[错误]{Style.RESET_ALL} {e}")
            return False
    
    def run(self) -> None:
        """运行离线转码器"""
        print(f"\n{Fore.CYAN}=== 离线转码工具（支持 AMV & 通用格式）==={Style.RESET_ALL}\n")
        
        # 检查 FFmpeg
        if not self._check_ffmpeg():
            return
        
        # 获取输入路径
        path = input("请输入文件或文件夹路径：").strip()
        
        if not path:
            print(f"{Fore.RED}[错误]{Style.RESET_ALL} 路径为空")
            return
        
        if not os.path.exists(path):
            print(f"{Fore.RED}[错误]{Style.RESET_ALL} 路径不存在")
            return
        
        # 选择文件
        if os.path.isfile(path):
            selected_files = [path]
        else:
            video_files = self.get_video_files(path)
            
            if not video_files:
                print(f"{Fore.YELLOW}[提示]{Style.RESET_ALL} 未找到视频文件")
                return
            
            print(f"\n找到 {len(video_files)} 个视频文件:")
            for i, fp in enumerate(video_files, 1):
                size = os.path.getsize(fp)
                print(f"  {i}. {os.path.basename(fp)} ({format_filesize(size)})")
            
            sel = input("\n编号（空格分隔，0=全部，回车取消）：").strip()
            
            if not sel:
                return
            
            if sel == '0':
                selected_files = video_files
            else:
                try:
                    indices = [int(x) for x in sel.split()]
                    selected_files = [
                        video_files[i - 1] 
                        for i in indices 
                        if 1 <= i <= len(video_files)
                    ]
                except (ValueError, IndexError):
                    print(f"{Fore.RED}[错误]{Style.RESET_ALL} 选择无效")
                    return
        
        if not selected_files:
            print(f"{Fore.YELLOW}[提示]{Style.RESET_ALL} 没有选中任何文件")
            return
        
        # 选择模式
        print(f"\n{Fore.CYAN}选择转码模式：{Style.RESET_ALL}")
        print(f"  {TranscodeMode.AMV}. AMV (MP4 播放器专用)")
        print(f"  {TranscodeMode.GENERAL}. 通用格式")
        
        mode_choice = input("请选择编号：").strip()
        
        if mode_choice == str(TranscodeMode.AMV):
            self._transcode_amv(selected_files)
        elif mode_choice == str(TranscodeMode.GENERAL):
            self._transcode_general(selected_files)
        else:
            print(f"{Fore.RED}[错误]{Style.RESET_ALL} 无效选择")
    
    def _transcode_amv(self, files: List[str]) -> None:
        """AMV 转码"""
        print(f"\n{Fore.CYAN}AMV 转码设置：{Style.RESET_ALL}")
        print(f"  分辨率: 160x112")
        print(f"  帧率: 30fps")
        print(f"  音频: 22050Hz 单声道")
        
        if not ask("确认开始转码?", default=True):
            return
        
        for fp in files:
            output = f"{os.path.splitext(fp)[0]}.amv"
            print(f"\n{Fore.CYAN}转码：{os.path.basename(fp)} → {os.path.basename(output)}{Style.RESET_ALL}")
            self.transcode(fp, output, AMV_PRESET['args'])
    
    def _transcode_general(self, files: List[str]) -> None:
        """通用格式转码"""
        print(f"\n{Fore.CYAN}可选输出格式：{Style.RESET_ALL}")
        for key, fmt in TRANSCODE_FORMATS.items():
            print(f"  {key}. {fmt['name']}")
        
        fmt_choice = input("\n选择编号：").strip()
        
        if fmt_choice not in TRANSCODE_FORMATS:
            print(f"{Fore.RED}[错误]{Style.RESET_ALL} 无效选择")
            return
        
        format_info = TRANSCODE_FORMATS[fmt_choice]
        
        # 自定义格式
        if format_info['ext'] is None:
            custom_ext = input("请输入输出扩展名（如 mp4）：").strip().lstrip('.')
            if not custom_ext:
                print(f"{Fore.RED}[错误]{Style.RESET_ALL} 扩展名不能为空")
                return
            format_info = {'name': custom_ext, 'ext': custom_ext}
        
        # 分辨率设置
        res = input("分辨率（如 1920*1080、720p，留空保持原分辨率）：").strip()
        
        # 构建 FFmpeg 参数
        if res and self.parse_resolution(res):
            args = [
                '-vf', f"scale={self.parse_resolution(res)}",
                '-c:v', format_info.get('vcodec', 'libx264'),
                '-preset', 'medium',
                '-c:a', format_info.get('acodec', 'aac'),
                '-b:a', '192k'
            ]
        else:
            args = ['-c', 'copy']
        
        # 开始转码
        print(f"\n{Fore.CYAN}输出格式: {format_info['ext'].upper()}{Style.RESET_ALL}")
        
        if not ask("确认开始转码?", default=True):
            return
        
        for fp in files:
            output = f"{os.path.splitext(fp)[0]}_converted.{format_info['ext']}"
            print(f"\n{Fore.CYAN}转码：{os.path.basename(fp)} → {os.path.basename(output)}{Style.RESET_ALL}")
            self.transcode(fp, output, args)


# ========== 向后兼容函数 ==========

def run_offline_transcoder() -> None:
    """运行离线转码器（向后兼容）"""
    transcoder = OfflineTranscoder()
    transcoder.run()


def parse_resolution(s: str) -> Optional[str]:
    """解析分辨率（向后兼容）"""
    transcoder = OfflineTranscoder()
    return transcoder.parse_resolution(s)


def get_video_files(folder: str) -> List[str]:
    """获取视频文件（向后兼容）"""
    transcoder = OfflineTranscoder()
    return transcoder.get_video_files(folder)


# ========== 测试 ==========

if __name__ == '__main__':
    print("=== OfflineTranscoder 测试 ===\n")
    
    transcoder = OfflineTranscoder()
    
    # 测试分辨率解析
    print("分辨率解析测试:")
    test_res = ["1920*1080", "720p", "1280x720", "invalid"]
    for r in test_res:
        result = transcoder.parse_resolution(r)
        print(f"  '{r}' -> {result}")
    
    # 测试 FFmpeg 检测
    print(f"\nFFmpeg 可用: {transcoder._check_ffmpeg()}")
    
    print("\n模块加载成功！")