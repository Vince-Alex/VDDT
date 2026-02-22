"""
VDDT Utils Module
工具函数模块 - 提供通用的工具函数

改进点：
1. 添加完整的类型提示
2. 更细化的异常处理
3. 自定义异常类
4. 集成日志系统
"""

import re
import os
import sys
import time
import urllib.parse
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any, Callable
from pathlib import Path

import colorama
from colorama import Fore, Style

from logger import get_logger

# 初始化 colorama
colorama.init(autoreset=True)


# ========== 自定义异常 ==========

class VDDTError(Exception):
    """VDDT 基础异常"""
    pass


class NetworkError(VDDTError):
    """网络相关错误"""
    pass


class CookieError(VDDTError):
    """Cookie 处理错误"""
    pass


class FormatError(VDDTError):
    """格式相关错误"""
    pass


class DownloadError(VDDTError):
    """下载相关错误"""
    pass


class TranscodeError(VDDTError):
    """转码相关错误"""
    pass


class ConfigError(VDDTError):
    """配置相关错误"""
    pass


# ========== 用户交互工具 ==========

def ask(prompt: str, default: bool = False) -> bool:
    """询问用户是/否问题并返回布尔值
    
    Args:
        prompt: 提示信息
        default: 默认值（用户直接回车时使用）
    
    Returns:
        用户选择的布尔值
    """
    default_hint = "Y/n" if default else "y/N"
    
    while True:
        try:
            response = input(f"{prompt} ({default_hint}): ").strip().lower()
            
            if not response:
                return default
            
            if response in ['y', 'yes', '是']:
                return True
            elif response in ['n', 'no', '否']:
                return False
            else:
                print(f"{Fore.RED}无效输入，请输入 'y' 或 'n'{Style.RESET_ALL}")
                
        except EOFError:
            # 处理非交互环境
            return default
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}用户取消操作{Style.RESET_ALL}")
            raise


def input_with_default(prompt: str, default: str = "") -> str:
    """带默认值的输入
    
    Args:
        prompt: 提示信息
        default: 默认值
    
    Returns:
        用户输入或默认值
    """
    hint = f" [{default}]" if default else ""
    
    try:
        response = input(f"{prompt}{hint}: ").strip()
        return response if response else default
    except EOFError:
        return default
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}用户取消操作{Style.RESET_ALL}")
        raise


def select_from_list(options: List[str], prompt: str = "请选择", 
                     allow_cancel: bool = True) -> Optional[int]:
    """从列表中选择一个选项
    
    Args:
        options: 选项列表
        prompt: 提示信息
        allow_cancel: 是否允许取消
    
    Returns:
        选择的索引（从0开始），取消返回None
    """
    if not options:
        return None
    
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    
    if allow_cancel:
        print(f"  0. 取消")
    
    while True:
        try:
            choice = input(f"{prompt} (0-{len(options)}): ").strip()
            idx = int(choice)
            
            if idx == 0 and allow_cancel:
                return None
            elif 1 <= idx <= len(options):
                return idx - 1
            else:
                print(f"{Fore.RED}无效选择，请重试{Style.RESET_ALL}")
                
        except ValueError:
            print(f"{Fore.RED}请输入数字{Style.RESET_ALL}")
        except EOFError:
            return None
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}用户取消操作{Style.RESET_ALL}")
            raise


# ========== 文件名处理 ==========

# Windows 非法文件名字符
ILLEGAL_FILENAME_CHARS = r'[\/:*?"<>|]'
# 额外的控制字符
ILLEGAL_CONTROL_CHARS = r'[\x00-\x1f\x7f]'


def sanitize_filename(name: str, replacement: str = "_", max_length: int = 200) -> str:
    """清理文件名中的非法字符
    
    Args:
        name: 原始文件名
        replacement: 替换字符
        max_length: 最大长度限制
    
    Returns:
        清理后的安全文件名
    """
    if not name:
        return "unnamed"
    
    # 移除非法字符
    name = re.sub(ILLEGAL_FILENAME_CHARS, replacement, name)
    name = re.sub(ILLEGAL_CONTROL_CHARS, '', name)
    
    # 移除首尾空白和点
    name = name.strip('. ')
    
    # 限制长度
    if len(name) > max_length:
        name = name[:max_length].rstrip()
    
    # 如果清理后为空，使用默认名
    if not name:
        name = "unnamed"
    
    return name


def get_unique_filepath(directory: str, filename: str) -> str:
    """获取唯一的文件路径（避免覆盖）
    
    Args:
        directory: 目录路径
        filename: 文件名
    
    Returns:
        唯一的完整文件路径
    """
    filepath = os.path.join(directory, filename)
    
    if not os.path.exists(filepath):
        return filepath
    
    # 文件已存在，添加序号
    name, ext = os.path.splitext(filename)
    counter = 1
    
    while os.path.exists(filepath):
        new_name = f"{name}_{counter}{ext}"
        filepath = os.path.join(directory, new_name)
        counter += 1
    
    return filepath


def format_filesize(size_bytes: Optional[int]) -> str:
    """格式化文件大小
    
    Args:
        size_bytes: 字节数
    
    Returns:
        格式化的大小字符串
    """
    if size_bytes is None or size_bytes < 0:
        return "未知"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    
    for unit in units[:-1]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    
    return f"{size:.2f} {units[-1]}"


# ========== Cookie 处理 ==========

def convert_to_netscape_cookie(cookie_str: str, output_file: str, 
                                domain: str = "www.example.com") -> bool:
    """将原始 cookie 字符串转换为 Netscape 格式
    
    Args:
        cookie_str: 原始 cookie 字符串
        output_file: 输出文件路径
        domain: 关联的域名
    
    Returns:
        是否成功
    """
    logger = get_logger()
    
    if not cookie_str or not cookie_str.strip():
        logger.warning("Cookie 字符串为空")
        return False
    
    try:
        cookie_lines = ["# Netscape HTTP Cookie File"]
        
        for part in cookie_str.split(';'):
            part = part.strip()
            if '=' in part:
                key, value = part.split('=', 1)
                cookie_lines.append(
                    f"{domain}\tTRUE\t/\tFALSE\t0\t{key.strip()}\t{value.strip()}"
                )
        
        if len(cookie_lines) == 1:
            logger.warning("Cookie 字符串格式无效，未找到有效的键值对")
            return False
        
        # 确保目录存在
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(cookie_lines))
        
        logger.info(f"Cookie 文件已保存: {output_file}")
        return True
        
    except IOError as e:
        logger.error(f"写入 Cookie 文件失败: {e}")
        return False
    except Exception as e:
        logger.exception(f"转换 Cookie 时发生未知错误: {e}")
        return False


def extract_domain(url: str) -> Optional[str]:
    """从 URL 中提取主域名
    
    Args:
        url: 完整的 URL
    
    Returns:
        主域名，如 "bilibili.com"
    """
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc
        
        # 移除端口
        if ':' in domain:
            domain = domain.split(':')[0]
        
        # 移除 www. 前缀
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # 提取主域名（如 www.bilibili.com -> bilibili.com）
        parts = domain.split('.')
        if len(parts) > 2:
            # 处理特殊情况，如 .co.uk
            if len(parts) >= 3 and parts[-2] in ['co', 'com', 'org', 'net', 'edu', 'gov']:
                domain = '.'.join(parts[-3:])
            else:
                domain = '.'.join(parts[-2:])
        
        return domain if domain else None
        
    except Exception:
        return None


# ========== 进度显示 ==========

class ProgressBar:
    """进度条类"""
    
    def __init__(self, total: int = 100, length: int = 40,
                 prefix: str = "", suffix: str = ""):
        """
        Args:
            total: 总进度
            length: 进度条长度
            prefix: 前缀文本
            suffix: 后缀文本
        """
        self.total = total
        self.length = length
        self.prefix = prefix
        self.suffix = suffix
        self.current = 0
    
    def update(self, current: int, desc: str = "") -> None:
        """更新进度
        
        Args:
            current: 当前进度
            desc: 额外描述
        """
        self.current = min(current, self.total)
        percent = self.current / self.total * 100
        
        filled = int(self.length * self.current / self.total)
        bar = '█' * filled + '-' * (self.length - filled)
        
        line = f"\r{Fore.CYAN}{self.prefix}{Style.RESET_ALL} "
        line += f"[{Fore.GREEN}{bar}{Style.RESET_ALL}] "
        line += f"{percent:5.1f}%"
        
        if desc:
            line += f" {desc}"
        
        sys.stdout.write(line)
        sys.stdout.flush()
    
    def finish(self, message: str = "完成") -> None:
        """完成进度条"""
        self.update(self.total, message)
        print()


def progress_hook(d: Dict[str, Any]) -> None:
    """yt-dlp 下载进度的回调函数
    
    Args:
        d: yt-dlp 传递的进度信息字典
    """
    logger = get_logger()
    
    status = d.get('status', '')
    
    if status == 'downloading':
        try:
            percent_str = d.get('_percent_str', 'N/A')
            eta_str = d.get('_eta_str', '?')
            downloaded_str = d.get('_downloaded_bytes_str', '?')
            total_str = d.get('_total_bytes_str') or d.get('_total_bytes_estimate_str') or '未知'
            
            percent = d.get('_percent', 0)
            bar_length = 40
            filled = int(round(bar_length * percent / 100.0))
            bar = '█' * filled + '-' * (bar_length - filled)
            
            line = f"\r{Fore.CYAN}[下载中]{Style.RESET_ALL} {percent_str:<6} "
            line += f"[{Fore.GREEN}{bar}{Style.RESET_ALL}] "
            line += f"{downloaded_str} / {total_str}  "
            line += f"ETA: {eta_str:<8}"
            
            sys.stdout.write(line)
            sys.stdout.flush()
            
        except Exception as e:
            logger.debug(f"进度显示错误: {e}")
    
    elif status == 'finished':
        print(f"\n{Fore.GREEN}[完成]{Style.RESET_ALL} 100% [{'█' * 40}] 文件已下载")
        logger.info("下载完成")
    
    elif status == 'error':
        print(f"\n{Fore.RED}[错误]{Style.RESET_ALL} 下载过程中发生错误")
        logger.error("下载过程中发生错误")


# ========== 时间处理 ==========

def parse_upload_date(date_str: Optional[str]) -> str:
    """解析上传日期
    
    Args:
        date_str: yt-dlp 返回的日期字符串 (YYYYMMDD 格式)
    
    Returns:
        格式化的日期字符串 (YYYY-MM-DD)
    """
    if not date_str:
        return datetime.now().strftime('%Y-%m-%d')
    
    try:
        return datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
    except ValueError:
        logger = get_logger()
        logger.debug(f"无法解析日期: {date_str}")
        return datetime.now().strftime('%Y-%m-%d')


def format_duration(seconds: int) -> str:
    """格式化时长
    
    Args:
        seconds: 秒数
    
    Returns:
        格式化的时长字符串 (HH:MM:SS 或 MM:SS)
    """
    if seconds < 0:
        return "00:00"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


# ========== 装饰器 ==========

def retry_on_error(max_retries: int = 3, delay: float = 1.0,
                   exceptions: Tuple = (Exception,)):
    """重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
        exceptions: 需要重试的异常类型
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            logger = get_logger()
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} 重试次数用尽")
            
            raise last_exception
        return wrapper
    return decorator


# ========== 测试 ==========

if __name__ == '__main__':
    # 测试工具函数
    print("=== 文件名清理测试 ===")
    test_names = [
        "视频标题/测试:视频",
        '文件名含"引号"',
        "正常文件名.mp4",
        "",
        "   ",
        "a" * 300,
    ]
    for name in test_names:
        print(f"  '{name}' -> '{sanitize_filename(name)}'")
    
    print("\n=== 域名提取测试 ===")
    test_urls = [
        "https://www.bilibili.com/video/BV1xx",
        "https://youtube.com/watch?v=xxx",
        "https://v.qq.com/x/cover/xyz",
        "https://www.example.co.uk/page",
    ]
    for url in test_urls:
        print(f"  {url} -> {extract_domain(url)}")
    
    print("\n=== 文件大小格式化测试 ===")
    sizes = [0, 1023, 1024, 1048576, 1073741824, 1099511627776]
    for size in sizes:
        print(f"  {size} bytes -> {format_filesize(size)}")
    
    print("\n=== 日期解析测试 ===")
    dates = ["20250115", "invalid", None]
    for date in dates:
        print(f"  {date} -> {parse_upload_date(date)}")
    
    print("\n=== 时长格式化测试 ===")
    durations = [0, 65, 3661, 7325]
    for sec in durations:
        print(f"  {sec} 秒 -> {format_duration(sec)}")
