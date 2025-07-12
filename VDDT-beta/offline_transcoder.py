import os
import subprocess
import sys
from ffmpeg_progress_yield import FfmpegProgress
from tqdm import tqdm
from colorama import Fore, Style

# ---------- 工具 ----------
def parse_resolution(s: str):
    s = s.strip().lower()
    if "*" in s:
        w, h = s.split("*", 1)
        if w.isdigit() and h.isdigit():
            return f"{w}:{h}"
    if "x" in s:
        w, h = s.split("x", 1)
        if w.isdigit() and h.isdigit():
            return f"{w}:{h}"
    if s.endswith("p") and s[:-1].isdigit():
        return f"-2:{s[:-1]}"
    return None

def get_video_files(folder):
    exts = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.m4v', '.ts', '.webm']
    return sorted([os.path.join(folder, f) for f in os.listdir(folder)
                   if os.path.splitext(f)[1].lower() in exts])

# ---------- 主流程 ----------
def run_offline_transcoder():
    print("=== 离线转码工具（支持 AMV & 通用）===\n")
    path = input("请输入文件或文件夹路径：").strip()
    if not os.path.exists(path):
        print(Fore.RED + "路径不存在！" + Style.RESET_ALL)
        return

    # 自动识别
    # ----- 选择文件 -----
    if os.path.isfile(path):
        selected = [path]
    else:
        files = get_video_files(path)
        if not files:
            print(Fore.YELLOW + "未找到视频文件。" + Style.RESET_ALL)
            return
        print("找到视频：")
        for i, fp in enumerate(files, 1):
            print(f"{i}. {os.path.basename(fp)}")
        sel = input("编号（空格分隔，0=全部）：").strip()
        if sel == "0":
            selected = files
        else:
            try:
                idxs = [int(x) - 1 for x in sel.split()]
                selected = [files[i] for i in idxs]
            except (ValueError, IndexError):
                print("选择无效")
                return

    # ---------- 选择模式 ----------
    modes = {"1": "AMV", "2": "通用格式"}
    print("\n选择转码模式：")
    for k, v in modes.items():
        print(f"{k}. {v}")
    mode = input("请选择编号：").strip()
    if mode not in modes:
        print("无效选择"); return

    # ---------- 输出格式 ----------
    if mode == "1":
        ext = "amv"
        codec_args = [
        "-s", "160x112", "-r", "30",
        "-c:v", "amv",
        "-c:a", "adpcm_ima_amv",
        "-block_size", "735",   # ← 关键
        "-ac", "1", "-ar", "22050"
    ]

    else:
        fmts = {"1": "mp4", "2": "mkv", "3": "avi", "4": "mov", "5": "flv", "6": "自定义"}
        print("\n可选通用格式：", " ".join(f"{k}={v}" for k, v in fmts.items()))
        choice = input("选择编号或扩展名：").strip()
        ext = fmts.get(choice) if choice in fmts and choice != "6" else choice.lstrip('.')
        if not ext:
            print("扩展名不能为空"); return

        # 分辨率
        res = input("分辨率（如 1920*1080、720p，留空原分辨率）：").strip()
        codec_args = (["-vf", f"scale={parse_resolution(res)}", "-c:v", "libx264", "-preset", "medium", "-c:a", "aac"]
                      if res and parse_resolution(res) else ["-c", "copy"])

    # ---------- 开始转码 ----------
    for fp in selected:
        out = f"{os.path.splitext(fp)[0]}_converted.{ext}"
        cmd = ["ffmpeg", "-i", fp] + codec_args + [out, "-y"]

        print(Fore.CYAN + f"\n转码：{os.path.basename(fp)} → {os.path.basename(out)}" + Style.RESET_ALL)
        progress = FfmpegProgress(cmd)
        with tqdm(total=100, desc="Progress", unit="%", ncols=80) as bar:
            for percent in progress.run_command_with_progress():
                bar.n = percent
                bar.refresh()
        print(Fore.GREEN + "[完成] ✓" + Style.RESET_ALL)

if __name__ == "__main__":
    try:
        run_offline_transcoder()
    except KeyboardInterrupt:
        print("\n用户中断")

