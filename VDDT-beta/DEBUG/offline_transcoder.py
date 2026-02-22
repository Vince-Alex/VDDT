#!/usr/bin/env python3
"""
VDDT 离线转码模块
支持 AMV 和通用格式的视频转码
"""
import os
import subprocess
import sys
from ffmpeg_progress_yield import FfmpegProgress
from tqdm import tqdm
from colorama import Fore, Style

# 常量定义
SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.m4v', '.ts', '.webm']

# AMV 转码参数
AMV_RESOLUTION = "160x112"
AMV_FRAME_RATE = "30"
AMV_VIDEO_CODEC = "amv"
AMV_AUDIO_CODEC = "adpcm_ima_amv"
AMV_BLOCK_SIZE = "735"
AMV_AUDIO_CHANNELS = "1"
AMV_AUDIO_RATE = "22050"

# 通用格式选项
GENERAL_FORMATS = {
    "1": "mp4",
    "2": "mkv",
    "3": "avi",
    "4": "mov",
    "5": "flv",
    "6": "custom"
}

# 视频编码参数
VIDEO_CODEC = "libx264"
VIDEO_PRESET = "medium"
AUDIO_CODEC = "aac"


def parse_resolution(s):
    """
    解析分辨率字符串

    Args:
        s: 分辨率字符串（如 "1920*1080", "720p"）

    Returns:
        FFmpeg scale 参数字符串，解析失败返回 None
    """
    s = s.strip().lower()

    # 处理 "1920*1080" 格式
    if "*" in s:
        w, h = s.split("*", 1)
        if w.isdigit() and h.isdigit():
            return f"{w}:{h}"

    # 处理 "1920x1080" 格式
    if "x" in s:
        w, h = s.split("x", 1)
        if w.isdigit() and h.isdigit():
            return f"{w}:{h}"

    # 处理 "720p" 格式
    if s.endswith("p") and s[:-1].isdigit():
        return f"-2:{s[:-1]}"

    return None


def get_video_files(folder):
    """
    获取文件夹中的所有视频文件

    Args:
        folder: 文件夹路径

    Returns:
        排序后的视频文件路径列表
    """
    return sorted([
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in SUPPORTED_VIDEO_EXTENSIONS
    ])


def print_video_files(files):
    """
    打印视频文件列表

    Args:
        files: 视频文件路径列表
    """
    print("找到视频：")
    for i, fp in enumerate(files, 1):
        print(f"{i}. {os.path.basename(fp)}")


def select_files(files):
    """
    让用户选择要转码的文件

    Args:
        files: 可用视频文件列表

    Returns:
        选择的文件路径列表
    """
    if not files:
        return []

    print_video_files(files)

    sel = input("编号（空格分隔，0=全部）：").strip()

    if sel == "0":
        return files

    try:
        idxs = [int(x) - 1 for x in sel.split()]
        return [files[i] for i in idxs if 0 <= i < len(files)]
    except (ValueError, IndexError):
        print("选择无效")
        return []


def select_transcode_mode():
    """
    选择转码模式

    Returns:
        模式编号字符串
    """
    modes = {"1": "AMV", "2": "通用格式"}
    print("\n选择转码模式：")
    for k, v in modes.items():
        print(f"{k}. {v}")

    mode = input("请选择编号：").strip()
    return mode if mode in modes else None


def get_amv_codec_args():
    """
    获取 AMV 转码的 FFmpeg 参数

    Returns:
        FFmpeg 参数列表
    """
    return [
        "-s", AMV_RESOLUTION,
        "-r", AMV_FRAME_RATE,
        "-c:v", AMV_VIDEO_CODEC,
        "-c:a", AMV_AUDIO_CODEC,
        "-block_size", AMV_BLOCK_SIZE,
        "-ac", AMV_AUDIO_CHANNELS,
        "-ar", AMV_AUDIO_RATE
    ]


def get_general_format():
    """
    获取通用格式选择

    Returns:
        格式扩展名字符串
    """
    print("\n可选通用格式：", " ".join(f"{k}={v}" for k, v in GENERAL_FORMATS.items()))
    choice = input("选择编号或扩展名：").strip()

    ext = GENERAL_FORMATS.get(choice) if choice in GENERAL_FORMATS and choice != "6" else choice.lstrip('.')

    if not ext:
        print("扩展名不能为空")
        return None

    return ext


def get_general_codec_args(resolution):
    """
    获取通用格式转码的 FFmpeg 参数

    Args:
        resolution: 分辨率字符串

    Returns:
        FFmpeg 参数列表
    """
    parsed_resolution = parse_resolution(resolution)

    if parsed_resolution:
        return [
            "-vf", f"scale={parsed_resolution}",
            "-c:v", VIDEO_CODEC,
            "-preset", VIDEO_PRESET,
            "-c:a", AUDIO_CODEC
        ]
    else:
        return ["-c", "copy"]


def get_resolution_input():
    """
    获取用户输入的分辨率

    Returns:
        分辨率字符串
    """
    return input("分辨率（如 1920*1080、720p，留空原分辨率）：").strip()


def build_ffmpeg_command(input_file, output_file, codec_args):
    """
    构建 FFmpeg 命令

    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
        codec_args: 编码参数列表

    Returns:
        FFmpeg 命令列表
    """
    return ["ffmpeg", "-i", input_file] + codec_args + [output_file, "-y"]


def run_transcode(input_file, output_file, codec_args):
    """
    执行转码操作

    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
        codec_args: 编码参数列表

    Returns:
        转码成功返回 True，失败返回 False
    """
    cmd = build_ffmpeg_command(input_file, output_file, codec_args)

    print(Fore.CYAN + f"\n转码：{os.path.basename(input_file)} → {os.path.basename(output_file)}" + Style.RESET_ALL)

    try:
        progress = FfmpegProgress(cmd)
        with tqdm(total=100, desc="Progress", unit="%", ncols=80) as bar:
            for percent in progress.run_command_with_progress():
                bar.n = percent
                bar.refresh()

        print(Fore.GREEN + "[完成] ✓" + Style.RESET_ALL)
        return True

    except Exception as e:
        print(Fore.RED + f"[错误] 转码失败: {e}" + Style.RESET_ALL)
        return False


def run_offline_transcoder():
    """
    运行离线转码工具的主流程
    """
    print("=== 离线转码工具（支持 AMV & 通用）===\n")

    # 获取路径
    path = input("请输入文件或文件夹路径：").strip()

    if not os.path.exists(path):
        print(Fore.RED + "路径不存在！" + Style.RESET_ALL)
        return

    # 选择文件
    if os.path.isfile(path):
        selected = [path]
    else:
        files = get_video_files(path)
        if not files:
            print(Fore.YELLOW + "未找到视频文件。" + Style.RESET_ALL)
            return

        selected = select_files(files)
        if not selected:
            return

    # 选择模式
    mode = select_transcode_mode()
    if not mode:
        print("无效选择")
        return

    # 根据模式处理
    if mode == "1":
        # AMV 模式
        ext = "amv"
        codec_args = get_amv_codec_args()

    else:
        # 通用格式模式
        ext = get_general_format()
        if not ext:
            return

        res = get_resolution_input()
        codec_args = get_general_codec_args(res)

    # 执行转码
    for fp in selected:
        out = f"{os.path.splitext(fp)[0]}_converted.{ext}"
        run_transcode(fp, out, codec_args)


if __name__ == "__main__":
    try:
        run_offline_transcoder()
    except KeyboardInterrupt:
        print("\n用户中断")
