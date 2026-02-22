"""
VDDT Main Module (TUI ONLY DEBUG VERSION)
主入口模块 - 仅保留 TUI 图形界面
"""

import os
import sys
from colorama import Fore, Style, init

# 初始化 colorama
init(autoreset=True)

# 导入必要模块
from logger import get_logger
from config import ConfigManager
from check_deps import check_and_install
from tui import run_tui, check_tui_support


def show_banner() -> None:
    """显示程序横幅"""
    print("=" * 50)
    print(f"{Fore.CYAN}   ╔═════════════════════════════════════════╗")
    print(f"   ║     VDDT 多功能视频下载器 TUI 模式        ║")
    print(f"   ╚═════════════════════════════════════════╝{Style.RESET_ALL}")
    print("=" * 50)


def main() -> None:
    """主函数"""
    # 初始化日志
    logger = get_logger()
    
    # 检查依赖
    if not check_and_install():
        print(f"{Fore.RED}[错误]{Style.RESET_ALL} 依赖检查失败，请手动安装缺失依赖。")
        sys.exit(1)
    
    # 加载配置
    config_manager = ConfigManager()
    config = config_manager.load()
    
    # 检查 TUI 支持
    supported, error = check_tui_support()
    if not supported:
        show_banner()
        print(f"{Fore.RED}[错误] 无法启动 TUI 模式: {error}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}提示: TUI 模式需要交互式终端环境。{Style.RESET_ALL}")
        sys.exit(1)

    # 启动 TUI 界面
    try:
        run_tui(config)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}用户中断退出{Style.RESET_ALL}")
    except Exception as e:
        logger.exception(f"程序运行崩溃: {e}")
        print(f"{Fore.RED}[崩溃] 发生未知错误: {e}{Style.RESET_ALL}")
    finally:
        # 保存配置
        config_manager.save()
        logger.info("程序退出并保存配置")


if __name__ == '__main__':
    main()
