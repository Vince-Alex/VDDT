"""
VDDT Dependencies Checker Module
依赖检查模块 - 检查并安装所需的依赖库

改进点：
1. 集成日志系统
2. 更好的错误处理
3. 类型提示
4. 支持可选依赖
5. 更友好的提示信息
"""

import sys
import subprocess
import importlib
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from colorama import Fore, Style


class DependencyLevel(Enum):
    """依赖级别"""
    REQUIRED = "required"      # 必需
    RECOMMENDED = "recommended"  # 推荐
    OPTIONAL = "optional"      # 可选


@dataclass
class Dependency:
    """依赖信息"""
    name: str              # pip 包名
    module: str            # 导入模块名
    description: str       # 描述
    level: DependencyLevel  # 依赖级别
    min_version: Optional[str] = None  # 最低版本


# 依赖列表
DEPENDENCIES: Dict[str, Dependency] = {
    'yt_dlp': Dependency(
        name='yt-dlp',
        module='yt_dlp',
        description='核心下载引擎',
        level=DependencyLevel.REQUIRED
    ),
    'colorama': Dependency(
        name='colorama',
        module='colorama',
        description='终端彩色输出',
        level=DependencyLevel.REQUIRED
    ),
    'ffmpeg_progress_yield': Dependency(
        name='ffmpeg-progress-yield',
        module='ffmpeg_progress_yield',
        description='FFmpeg 进度显示',
        level=DependencyLevel.RECOMMENDED
    ),
    'tqdm': Dependency(
        name='tqdm',
        module='tqdm',
        description='进度条美化',
        level=DependencyLevel.RECOMMENDED
    ),
    'requests': Dependency(
        name='requests',
        module='requests',
        description='网络请求库',
        level=DependencyLevel.OPTIONAL
    ),
    'urwid': Dependency(
        name='urwid',
        module='urwid',
        description='TUI 图形界面',
        level=DependencyLevel.OPTIONAL
    ),
}


class DependencyChecker:
    """依赖检查器"""
    
    def __init__(self, verbose: bool = False):
        """
        Args:
            verbose: 是否显示详细信息
        """
        self.verbose = verbose
        self.missing_required: List[Dependency] = []
        self.missing_recommended: List[Dependency] = []
        self.missing_optional: List[Dependency] = []
    
    def check_module(self, module_name: str) -> bool:
        """检查模块是否可用
        
        Args:
            module_name: 模块名
        
        Returns:
            是否可用
        """
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False
    
    def get_module_version(self, module_name: str) -> Optional[str]:
        """获取模块版本
        
        Args:
            module_name: 模块名
        
        Returns:
            版本字符串，如果无法获取则返回 None
        """
        try:
            module = importlib.import_module(module_name)
            return getattr(module, '__version__', None)
        except ImportError:
            return None
    
    def check_all(self) -> Tuple[bool, bool]:
        """检查所有依赖
        
        Returns:
            (是否满足必需依赖, 是否有推荐的缺失)
        """
        self.missing_required = []
        self.missing_recommended = []
        self.missing_optional = []
        
        if self.verbose:
            print(f"\n{Fore.CYAN}检查依赖...{Style.RESET_ALL}\n")
        
        for dep in DEPENDENCIES.values():
            available = self.check_module(dep.module)
            
            if available:
                version = self.get_module_version(dep.module)
                if self.verbose:
                    version_str = f" v{version}" if version else ""
                    print(f"  {Fore.GREEN}✓{Style.RESET_ALL} {dep.name}{version_str} - {dep.description}")
            else:
                if dep.level == DependencyLevel.REQUIRED:
                    self.missing_required.append(dep)
                elif dep.level == DependencyLevel.RECOMMENDED:
                    self.missing_recommended.append(dep)
                else:
                    self.missing_optional.append(dep)
                
                if self.verbose:
                    level_color = {
                        DependencyLevel.REQUIRED: Fore.RED,
                        DependencyLevel.RECOMMENDED: Fore.YELLOW,
                        DependencyLevel.OPTIONAL: Fore.CYAN
                    }.get(dep.level, Fore.WHITE)
                    
                    print(f"  {level_color}✗{Style.RESET_ALL} {dep.name} - {dep.description} ({dep.level.value})")
        
        return (
            len(self.missing_required) == 0,
            len(self.missing_recommended) > 0
        )
    
    def install_package(self, package_name: str) -> bool:
        """安装包
        
        Args:
            package_name: 包名
        
        Returns:
            是否成功
        """
        try:
            print(f"{Fore.CYAN}正在安装 {package_name}...{Style.RESET_ALL}")
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package_name],
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                print(f"{Fore.GREEN}✓{Style.RESET_ALL} {package_name} 安装成功")
                return True
            else:
                print(f"{Fore.RED}✗{Style.RESET_ALL} {package_name} 安装失败")
                if self.verbose and result.stderr:
                    print(f"  错误: {result.stderr[:200]}")
                return False
        
        except subprocess.TimeoutExpired:
            print(f"{Fore.RED}✗{Style.RESET_ALL} {package_name} 安装超时")
            return False
        except Exception as e:
            print(f"{Fore.RED}✗{Style.RESET_ALL} {package_name} 安装错误: {e}")
            return False
    
    def install_missing(self, include_optional: bool = False) -> bool:
        """安装缺失的依赖
        
        Args:
            include_optional: 是否包含可选依赖
        
        Returns:
            是否所有必需依赖都成功安装
        """
        to_install: List[Dependency] = []
        to_install.extend(self.missing_required)
        to_install.extend(self.missing_recommended)
        
        if include_optional:
            to_install.extend(self.missing_optional)
        
        if not to_install:
            return True
        
        print(f"\n{Fore.YELLOW}需要安装以下依赖:{Style.RESET_ALL}")
        for dep in to_install:
            print(f"  - {dep.name}: {dep.description}")
        
        # 询问是否安装
        try:
            response = input("\n是否自动安装? (Y/n): ").strip().lower()
            if response in ['n', 'no']:
                return False
        except EOFError:
            # 非交互环境，默认安装
            pass
        
        # 安装
        success = True
        for dep in to_install:
            if not self.install_package(dep.name):
                if dep.level == DependencyLevel.REQUIRED:
                    success = False
        
        return success
    
    def check_external_tools(self) -> Dict[str, bool]:
        """检查外部工具
        
        Returns:
            工具名 -> 是否可用的字典
        """
        tools = {}
        
        # FFmpeg
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                timeout=5
            )
            tools['ffmpeg'] = result.returncode == 0
        except Exception:
            tools['ffmpeg'] = False
        
        # ffprobe
        try:
            result = subprocess.run(
                ['ffprobe', '-version'],
                capture_output=True,
                timeout=5
            )
            tools['ffprobe'] = result.returncode == 0
        except Exception:
            tools['ffprobe'] = False
        
        return tools


def check_and_install(verbose: bool = True) -> bool:
    """检查并安装依赖
    
    Args:
        verbose: 是否显示详细信息
    
    Returns:
        是否满足所有必需依赖
    """
    checker = DependencyChecker(verbose=verbose)
    
    # 检查 Python 库
    required_ok, _ = checker.check_all()
    
    if not required_ok:
        if not checker.install_missing():
            print(f"\n{Fore.RED}[错误]{Style.RESET_ALL} 部分必需依赖未安装")
            print("请手动安装:")
            for dep in checker.missing_required:
                print(f"  pip install {dep.name}")
            return False
    
    # 检查外部工具
    if verbose:
        print(f"\n{Fore.CYAN}检查外部工具...{Style.RESET_ALL}\n")
    
    tools = checker.check_external_tools()
    
    if tools.get('ffmpeg'):
        if verbose:
            print(f"  {Fore.GREEN}✓{Style.RESET_ALL} FFmpeg 已安装")
    else:
        if verbose:
            print(f"  {Fore.YELLOW}!{Style.RESET_ALL} FFmpeg 未安装（转码功能将不可用）")
    
    if tools.get('ffprobe'):
        if verbose:
            print(f"  {Fore.GREEN}✓{Style.RESET_ALL} FFprobe 已安装")
    else:
        if verbose:
            print(f"  {Fore.YELLOW}!{Style.RESET_ALL} FFprobe 未安装")
    
    if verbose:
        if not tools.get('ffmpeg'):
            print(f"\n{Fore.YELLOW}[提示]{Style.RESET_ALL} 请安装 FFmpeg 以启用转码功能:")
            print("  Windows: https://www.gyan.dev/ffmpeg/builds/")
            print("  macOS:   brew install ffmpeg")
            print("  Linux:   sudo apt install ffmpeg")
    
    if verbose:
        print(f"\n{Fore.GREEN}[✓] 依赖检查完成{Style.RESET_ALL}")
    
    return True


# 向后兼容的别名
DEPS = {name: dep.description for name, dep in DEPENDENCIES.items()}


if __name__ == '__main__':
    print("=== VDDT 依赖检查器 ===\n")
    
    checker = DependencyChecker(verbose=True)
    checker.check_all()
    
    print("\n--- 外部工具 ---")
    tools = checker.check_external_tools()
    for tool, available in tools.items():
        status = f"{Fore.GREEN}✓{Style.RESET_ALL}" if available else f"{Fore.RED}✗{Style.RESET_ALL}"
        print(f"  {status} {tool}")
