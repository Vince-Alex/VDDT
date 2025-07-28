# check_deps.py
import sys
import subprocess
import importlib
from colorama import Fore, Style

# 需要检查的依赖库及其说明
DEPS = {
    "yt_dlp":        "核心下载引擎（必须）",
    "colorama":      "终端彩色输出（必须）",
    "ffmpeg_progress_yield": "实时显示 FFmpeg 转码进度",
    "tqdm":          "进度条美化",
    "requests":      "网络请求（某些插件可能用到）",
}

def check_and_install():
    missing = []
    for pkg, desc in DEPS.items():
        try:
            importlib.import_module(pkg)
        except ImportError:
            missing.append((pkg, desc))

    if not missing:
        print(f"{Fore.GREEN}[✓] 所有依赖库已就绪{Style.RESET_ALL}")
        return True

    print(f"{Fore.YELLOW}[!] 检测到缺失依赖库:{Style.RESET_ALL}")
    for pkg, desc in missing:
        print(f"  - {pkg}: {desc}")

    if input("是否自动安装缺失库？(y/n): ").strip().lower() in {"y", "yes"}:
        for pkg, _ in missing:
            print(f"{Fore.CYAN}正在安装 {pkg} ...{Style.RESET_ALL}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
        print(f"{Fore.GREEN}[✓] 依赖安装完成{Style.RESET_ALL}")
        return True
    else:
        print(f"{Fore.RED}[×] 部分依赖未安装，程序可能无法正常运行{Style.RESET_ALL}")
        return False

if __name__ == "__main__":
    check_and_install()
