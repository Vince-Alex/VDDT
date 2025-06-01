# VDDT Downloader - 终极视频下载解决方案

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![Version](https://img.shields.io/badge/Version-1.2-yellow)
![Supported Sites](https://img.shields.io/badge/Supported_Sites-1000+-brightgreen)

**VDDT Downloader** 是一个基于 Python 和 yt-dlp 的全功能视频下载工具，支持从**1000+网站**下载视频、音频和字幕。无论您需要下载 YouTube 教程、Bilibili 番剧、TikTok 短视频，还是其他任何媒体内容，VDDT 都能提供简单高效的解决方案。

## 🌟 核心功能

### 🎥 全能下载
- **智能格式选择**：自动推荐最佳画质或手动选择特定格式
- **多模式下载**：支持视频+音频、仅视频、仅音频三种模式
- **批量处理**：从文本文件读取多个链接进行自动批量下载
- **全面平台支持**：支持所有 yt-dlp 兼容的网站（超过1000个）

### 🛠 专业增强
- **字幕下载**：自动获取中英文字幕（srt/vtt格式）
- **封面嵌入**：下载并嵌入精美视频封面
- **弹幕提取**：独家支持B站弹幕下载
- **高级转码**：提供多种预设转码选项或自定义分辨率/码率
- **文件名定制**：灵活的文件名模板系统

### 🔒 登录支持
- **智能Cookie管理**：自动加载网站专属Cookie
- **通用Cookie支持**：提供跨站点通用Cookie方案
- **自动格式转换**：原始Cookie自动转为Netscape格式

### ✨ 用户体验
- **彩色终端界面**：直观的状态显示和进度条
- **错误恢复机制**：自动重试失败的片段
- **并发下载**：多片段同时下载加速过程

## 📋 支持网站示例

| 平台 | 支持内容 | 需要Cookie |
|------|----------|------------|
| YouTube | 视频/音频/字幕 | 可选 |
| Bilibili | 视频/音频/弹幕/字幕 | 高清必需 |
| TikTok | 视频/音频 | 可选 |
| Twitter | 视频 | 可选 |
| Instagram | 视频/图片 | 必需 |
| 优酷/腾讯/爱奇艺 | 视频 | 必需 |
| 其他1000+站点 | 视频/音频 | 视情况而定 |

> **提示**：国内平台通常需要登录Cookie才能下载高清视频

## 🚀 快速开始

### 安装依赖
```bash
pip install yt-dlp colorama
```

### 安装FFmpeg（必需）
- **Windows**：[下载FFmpeg](https://www.gyan.dev/ffmpeg/builds/) 并添加到系统PATH
- **macOS**：`brew install ffmpeg`
- **Linux**：`sudo apt install ffmpeg`

### 首次运行
```bash
python VDDT-beta.py
```

## 📖 详细使用指南

### 基本使用流程
1. 运行程序并选择下载模式：
   - `1` 下载单个视频
   - `2` 批量下载多个视频
2. 根据提示选择：
   - 下载模式（视频+音频、仅视频、仅音频）
   - 是否下载字幕
   - 是否嵌入封面
   - 是否下载弹幕（B站专属）
   - 是否进行转码
3. 下载完成后，文件将保存在 `VDDT_Downloads` 目录

### 🔐 Cookie设置（登录下载）

1. 创建 `cookies` 文件夹
2. 在文件夹中创建cookie文件：
   - **网站专属cookie**：`[域名].ck` (如 `bilibili.com.ck`, `youtube.com.ck`)
   - **通用cookie**：`common.ck` (所有网站通用)
   
3. 文件内容格式（直接从浏览器复制）：
   ```
   SESSDATA=123456789; DedeUserID=123456; other_cookie=value
   ```

> **自动转换**：脚本会自动将原始Cookie转换为Netscape格式

### 📁 批量下载
1. 创建 `download_list.txt` 文件
2. 每行输入一个视频链接：
   ```
   https://www.bilibili.com/video/BV1xx
   https://youtu.be/abc123
   https://v.qq.com/x/cover/xyz
   ```
3. 选择批量下载模式自动处理所有链接

### ✏️ 自定义文件名模板

支持变量：
- `%(title)s` - 视频标题
- `%(uploader)s` - 上传者名称
- `%(upload_date)s` - 上传日期 (YYYYMMDD)
- `%(ext)s` - 文件扩展名
- `%(id)s` - 视频ID
- `%(resolution)s` - 分辨率

**示例模板**：
- `%(title)s.%(ext)s` → `Python教程.mp4`
- `%(upload_date)s_%(uploader)s_%(title)s.%(ext)s` → `20250115_科技频道_Python教程.mp4`

### ⚙️ 转码选项
提供多种预设转码方案：
1. 720p MP4 (推荐)
2. 1080p MP4
3. 仅音频 MP3 (192kbps)
4. 1500k 码率 MP4
5. 自定义分辨率或码率

## 🖥 系统要求

- Python 3.8+
- FFmpeg (必须)
- yt-dlp (自动安装)
- colorama (自动安装)

## 📜 许可证

本项目采用 [MIT 许可证](LICENSE) - 您可以自由使用、修改和分发代码

---
**VDDT Downloader** © 2025 Alex  
基于强大的 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 项目构建

**让下载变得简单** - 专注于内容，而不是技术细节
