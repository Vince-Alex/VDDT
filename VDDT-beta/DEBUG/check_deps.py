#!/usr/bin/env python3
"""
VDDT 依赖检查模块
检查并自动安装项目所需的依赖库
"""
import sys
import subprocess
import importlib
from colorama import Fore, Style

# 需要检查的依赖库及其说明
DEPS = {
    "yt_dlp": "核心下载引擎（必须）",
    "colorama": "终端彩色输出（必须）",
    "ffmpeg_progress_yield": "实时显示 FFmpeg 转码进度",
    "tqdm": "进度条美化",
    "requests": "网络请求（某些插件可能用到）",
}

# 安装命令
INSTALL_COMMAND = [sys.executable, "-m", "pip", "install"]


def check_module(module_name):
    """
    检查模块是否已安装

    Args:
        module_name: 模块名称

    Returns:
        已安装返回 True，否则返回 False
    """
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def get_missing_deps():
    """
    获取缺失的依赖库列表

    Returns:
        缺失的依赖库列表，每个元素为 (包名, 描述) 的元组
    """
    missing = []
    for pkg, desc in DEPS.items():
        if not check_module(pkg):
            missing.append((pkg, desc))
    return missing


def print_missing_deps(missing):
    """
    打印缺失的依赖库信息

    Args:
        missing: 缺失的依赖库列表
    """
    print(f"{Fore.YELLOW}[!] 检测到缺失依赖库:{Style.RESET_ALL}")
    for pkg, desc in missing:
        print(f"  - {pkg}: {desc}")


def install_package(package_name):
    """
    安装指定的 Python 包

    Args:
        package_name: 包名称

    Returns:
        安装成功返回 True，失败返回 False
    """
    try:
        print(f"{Fore.CYAN}正在安装 {package_name} ...{Style.RESET_ALL}")
        subprocess.check_call(INSTALL_COMMAND + [package_name])
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}[错误]{Style.RESET_ALL} 安装 {package_name} 失败: {e}")
        return False
    except Exception as e:
        print(f"{Fore.RED}[错误]{Style.RESET_ALL} 安装 {package_name} 时发生未知错误: {e}")
        return False


def install_missing_deps(missing):
    """
    安装所有缺失的依赖库

    Args:
        missing: 缺失的依赖库列表

    Returns:
        全部安装成功返回 True，否则返回 False
    """
    all_success = True
    for pkg, _ in missing:
        if not install_package(pkg):
            all_success = False
    return all_success


def ask_user_confirmation():
    """
    询问用户是否自动安装缺失的依赖

    Returns:
        用户同意返回 True，否则返回 False
    """
    response = input("是否自动安装缺失库？(y/n): ").strip().lower()
    return response in {"y", "yes"}


def check_and_install():
    """
    检查依赖并自动安装缺失的库

    Returns:
        所有依赖已就绪返回 True，否则返回 False
    """
    # 检查缺失的依赖
    missing = get_missing_deps()

    # 如果没有缺失，直接返回
    if not missing:
        print(f"{Fore.GREEN}[✓] 所有依赖库已就绪{Style.RESET_ALL}")
        return True

    # 打印缺失的依赖
    print_missing_deps(missing)

    # 询问用户是否自动安装
    if ask_user_confirmation():
        if install_missing_deps(missing):
            print(f"{Fore.GREEN}[✓] 依赖安装完成{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}[×] 部分依赖安装失败，程序可能无法正常运行{Style.RESET_ALL}")
            return False
    else:
        print(f"{Fore.RED}[×] 部分依赖未安装，程序可能无法正常运行{Style.RESET_ALL}")
        return False


if __name__ == "__main__":
    check_and_install()