"""
VDDT TUI Module
终端可视化图形界面模块 - 基于 curses 实现

功能：
1. 完整的菜单导航系统
2. 下载/转码/设置功能
3. 进度条可视化
4. 日志查看

快捷键:
- 数字键: 直接选择菜单项
- 上下键/j/k: 导航
- Enter: 确认
- Q: 返回/退出
- Ctrl+C: 强制退出
"""

import os
import sys
import time
import curses
import curses.panel
import threading
import subprocess
from typing import Optional, Callable, List, Dict, Any, Tuple
from datetime import datetime

from colorama import Fore, Style

from logger import get_logger
from config import VDDTConfig, ConfigManager, get_config


# ============================================================
# 颜色定义 (curses 颜色对)
# ============================================================

COLOR_PAIRS = {
    'normal': 1,
    'title': 2,
    'menu_item': 3,
    'menu_focus': 4,
    'menu_header': 5,
    'menu_disabled': 6,
    'status': 7,
    'status_success': 8,
    'status_error': 9,
    'status_warning': 10,
    'dialog': 11,
    'dialog_title': 12,
    'button': 13,
    'button_focus': 14,
    'input': 15,
    'progress': 16,
    'progress_bg': 17,
}


def init_colors():
    """初始化颜色"""
    curses.start_color()
    curses.use_default_colors()
    
    # 定义颜色对
    curses.init_pair(1, curses.COLOR_WHITE, -1)           # normal
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLUE)  # title
    curses.init_pair(3, curses.COLOR_WHITE, -1)           # menu_item
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_CYAN)  # menu_focus
    curses.init_pair(5, curses.COLOR_CYAN, -1)            # menu_header
    curses.init_pair(6, 8, -1)                               # menu_disabled (灰色)
    curses.init_pair(7, curses.COLOR_WHITE, -1)           # status
    curses.init_pair(8, curses.COLOR_GREEN, -1)           # status_success
    curses.init_pair(9, curses.COLOR_RED, -1)             # status_error
    curses.init_pair(10, curses.COLOR_YELLOW, -1)         # status_warning
    curses.init_pair(11, curses.COLOR_WHITE, curses.COLOR_BLUE)  # dialog
    curses.init_pair(12, curses.COLOR_YELLOW, curses.COLOR_BLUE)  # dialog_title
    curses.init_pair(13, curses.COLOR_WHITE, curses.COLOR_BLUE)   # button
    curses.init_pair(14, curses.COLOR_BLACK, curses.COLOR_CYAN)   # button_focus
    curses.init_pair(15, curses.COLOR_WHITE, curses.COLOR_BLACK)  # input
    curses.init_pair(16, curses.COLOR_GREEN, -1)          # progress
    curses.init_pair(17, curses.COLOR_BLUE, -1)           # progress_bg


# ============================================================
# 对话框类
# ============================================================

class Dialog:
    """对话框基类"""
    
    def __init__(self, stdscr, title: str, width: int = 50, height: int = 10):
        self.stdscr = stdscr
        self.title = title
        self.width = min(width, curses.COLS - 4)
        self.height = min(height, curses.LINES - 4)
        self.x = (curses.COLS - self.width) // 2
        self.y = (curses.LINES - self.height) // 2
        self.result = None
    
    def draw_box(self):
        """绘制对话框边框"""
        try:
            # 创建窗口
            self.win = curses.newwin(self.height, self.width, self.y, self.x)
            self.win.keypad(True)
            
            # 绘制边框
            self.win.border()
            
            # 绘制标题
            title_text = f" {self.title[:self.width-4]} "
            self.win.attron(curses.color_pair(COLOR_PAIRS['dialog_title']))
            self.win.addstr(0, (self.width - len(title_text)) // 2, title_text)
            self.win.attroff(curses.color_pair(COLOR_PAIRS['dialog_title']))
        except curses.error:
            pass
    
    def show(self) -> Any:
        """显示对话框，返回结果"""
        self.draw_box()
        return self.result
    
    def _center_text(self, text: str, y: int):
        """居中显示文本"""
        # 截断超长文本
        if len(text) > self.width - 4:
            text = text[:self.width - 7] + "..."
        x = (self.width - len(text)) // 2
        try:
            self.win.addstr(y, max(1, x), text)
        except curses.error:
            pass


class MessageDialog(Dialog):
    """消息对话框"""
    
    def __init__(self, stdscr, title: str, message: str, style: str = 'info'):
        # 计算合适的高度和宽度
        lines = message.split('\n')
        max_line = max(len(line) for line in lines) if lines else 0
        height = min(len(lines) + 6, curses.LINES - 4)
        width = min(max(max_line + 6, len(title) + 6, 40), curses.COLS - 4)
        super().__init__(stdscr, title, width, height)
        self.message = message
        self.style = style
    
    def show(self) -> bool:
        self.draw_box()
        
        # 显示消息（按行显示）
        lines = self.message.split('\n')
        y = 2
        for line in lines[:self.height - 5]:  # 保留空间给按钮
            # 截断超长行
            display_line = line[:self.width - 4] if len(line) > self.width - 4 else line
            try:
                self.win.addstr(y, 2, display_line)
            except curses.error:
                pass
            y += 1
        
        # 确定按钮
        btn_text = "[ 确定 ]"
        btn_x = (self.width - len(btn_text)) // 2
        try:
            self.win.attron(curses.color_pair(COLOR_PAIRS['button_focus']))
            self.win.addstr(self.height - 2, btn_x, btn_text)
            self.win.attroff(curses.color_pair(COLOR_PAIRS['button_focus']))
        except curses.error:
            pass
        
        self.win.refresh()
        
        # 等待按键
        while True:
            key = self.win.getch()
            if key in (ord('\n'), ord('\r'), 10, 13, ord(' '), ord('q'), ord('Q')):
                break
        
        return True


class InputDialog(Dialog):
    """输入对话框"""
    
    def __init__(self, stdscr, title: str, prompt: str, default: str = ""):
        height = 9
        width = min(max(len(prompt) + 10, len(title) + 6, 50), curses.COLS - 4)
        super().__init__(stdscr, title, width, height)
        self.prompt = prompt[:width-6] if len(prompt) > width-6 else prompt
        self.default = default
        self.value = default
    
    def show(self) -> Optional[str]:
        try:
            self.draw_box()
            
            # 显示提示
            self.win.addstr(2, 2, self.prompt)
            
            # 输入框
            input_width = self.width - 4
            input_win = curses.newwin(1, input_width, self.y + 3, self.x + 2)
            input_win.attron(curses.color_pair(COLOR_PAIRS['input']))
            
            # 显示默认值
            self.value = self.default[:input_width] if len(self.default) > input_width else self.default
            input_win.addstr(0, 0, self.value)
            input_win.refresh()
            
            # 启用输入
            curses.echo()
            curses.curs_set(1)
            
            try:
                input_win.move(0, len(self.value))
                input_win.refresh()
                
                # 简单的输入处理
                result = list(self.value)
                pos = len(self.value)
                
                while True:
                    key = input_win.getch()
                    
                    if key in (ord('\n'), ord('\r'), 10, 13):
                        # 回车确认
                        break
                    elif key in (ord('q'), ord('Q')):  # 使用 Q 取消
                        curses.noecho()
                        curses.curs_set(0)
                        return None
                    elif key in (curses.KEY_BACKSPACE, 127, 8):
                        # 退格
                        if pos > 0:
                            pos -= 1
                            result = result[:pos]
                            input_win.move(0, 0)
                            input_win.clrtoeol()
                            text = ''.join(result)
                            input_win.addstr(0, 0, text)
                    elif 32 <= key <= 126:
                        # 可打印字符
                        if pos < input_width:
                            result.append(chr(key))
                            pos += 1
                            text = ''.join(result)
                            input_win.addstr(0, 0, text)
                            input_win.move(0, pos)
                    
                    input_win.refresh()
                
                self.value = ''.join(result) if result else self.default
                
            finally:
                curses.noecho()
                curses.curs_set(0)
            
            # 按钮提示
            self.win.addstr(5, 2, "Enter=确定  Q=取消")
            self.win.refresh()
            
            return self.value if self.value else None
            
        except curses.error:
            return None


class ConfirmDialog(Dialog):
    """确认对话框"""
    
    def __init__(self, stdscr, title: str, message: str):
        height = 7
        width = min(max(len(message) + 6, len(title) + 6, 40), curses.COLS - 4)
        super().__init__(stdscr, title, width, height)
        self.message = message[:width-6] if len(message) > width-6 else message
    
    def show(self) -> bool:
        try:
            self.draw_box()
            
            # 显示消息
            self._center_text(self.message, 2)
            
            # 按钮
            btn_yes = "[ Y 是 ]"
            btn_no = "[ N 否 ]"
            btn_x = (self.width - len(btn_yes) - len(btn_no) - 4) // 2
            
            self.win.addstr(4, btn_x, btn_yes)
            self.win.addstr(4, btn_x + len(btn_yes) + 4, btn_no)
            
            self.win.refresh()
            
            # 等待按键
            while True:
                key = self.win.getch()
                if key in (ord('y'), ord('Y')):
                    return True
                elif key in (ord('n'), ord('N'), ord('q'), ord('Q')):
                    return False
        except curses.error:
            return False


class FileBrowserDialog(Dialog):
    """可视化文件/文件夹浏览器对话框"""
    
    def __init__(self, stdscr, title: str, start_path: str = "."):
        # 统一的对话框尺寸
        width = min(60, curses.COLS - 4)
        height = min(20, curses.LINES - 4)
        super().__init__(stdscr, title, width, height)
        
        self.current_path = os.path.abspath(start_path)
        self.selected = 0
        self.items = []
        self.scroll_offset = 0
        self._refresh_items()
    
    def _refresh_items(self):
        """刷新当前路径下的文件列表"""
        try:
            entries = os.listdir(self.current_path)
            # 分离目录和文件，并排序
            dirs = sorted([e for e in entries if os.path.isdir(os.path.join(self.current_path, e))])
            files = sorted([e for e in entries if os.path.isfile(os.path.join(self.current_path, e))])
            
            # 组合列表：上级目录 + 目录 + 文件
            self.items = [(".. [返回上级]", "..")]
            self.items.extend([(f"📁 {d}/", d) for d in dirs])
            self.items.extend([(f"📄 {f}", f) for f in files])
            
            self.selected = 0
            self.scroll_offset = 0
        except Exception:
            self.items = [(".. [返回上级]", ".."), ("无法访问该目录", "")]
    
    def show(self) -> Optional[str]:
        try:
            self.draw_box()
            self.win.timeout(100) # 非阻塞
            
            visible_count = self.height - 6
            
            while True:
                self.stdscr.touchwin() # 确保父窗口不干扰
                self.win.erase()
                self.win.border()
                
                # 绘制标题
                title_text = f" {self.title} "
                self.win.attron(curses.color_pair(COLOR_PAIRS['dialog_title']))
                self.win.addstr(0, (self.width - len(title_text)) // 2, title_text[:self.width-2])
                self.win.attroff(curses.color_pair(COLOR_PAIRS['dialog_title']))
                
                # 绘制当前路径
                display_path = f"路径: ...{self.current_path[-self.width+10:]}" if len(self.current_path) > self.width-10 else f"路径: {self.current_path}"
                self.win.addstr(1, 2, display_path[:self.width-4], curses.color_pair(COLOR_PAIRS['menu_header']))
                
                # 绘制列表
                for i in range(visible_count):
                    idx = self.scroll_offset + i
                    if idx >= len(self.items):
                        break
                    
                    text, name = self.items[idx]
                    y = 2 + i
                    
                    if idx == self.selected:
                        self.win.attron(curses.color_pair(COLOR_PAIRS['menu_focus']))
                        self.win.addstr(y, 2, f"→ {text}"[:self.width-4])
                        self.win.attroff(curses.color_pair(COLOR_PAIRS['menu_focus']))
                    else:
                        self.win.addstr(y, 2, f"  {text}"[:self.width-4])
                
                # 底部提示
                hint = "Enter:进入/选定 Q:取消 S:确认当前目录"
                self.win.addstr(self.height - 2, 2, hint[:self.width-4])
                
                self.win.refresh()
                key = self.win.getch()
                
                if key == -1: continue
                
                if key == curses.KEY_UP or key == ord('k'):
                    self.selected = (self.selected - 1) % len(self.items)
                    if self.selected < self.scroll_offset:
                        self.scroll_offset = self.selected
                elif key == curses.KEY_DOWN or key == ord('j'):
                    self.selected = (self.selected + 1) % len(self.items)
                    if self.selected >= self.scroll_offset + visible_count:
                        self.scroll_offset = self.selected - visible_count + 1
                elif key in (ord('\n'), ord('\r'), 10, 13):
                    name = self.items[self.selected][1]
                    if not name: continue
                    
                    new_path = os.path.abspath(os.path.join(self.current_path, name))
                    if os.path.isdir(new_path):
                        self.current_path = new_path
                        self._refresh_items()
                    else:
                        # 选择了文件
                        return new_path
                elif key in (ord('s'), ord('S')):
                    # 确认选择当前目录
                    return self.current_path
                elif key in (ord('q'), ord('Q')):
                    return None
                    
        except curses.error:
            return None


class SelectDialog(Dialog):
    """选择对话框 - 居中显示，统一大小"""
    
    # 统一的对话框尺寸
    DEFAULT_WIDTH = 50
    MIN_HEIGHT = 8
    MAX_HEIGHT = 15
    
    def __init__(self, stdscr, title: str, options: List[Tuple[str, Any]]):
        # 计算高度：选项数 + 边框和按钮空间
        height = min(len(options) + 5, self.MAX_HEIGHT)
        height = max(height, self.MIN_HEIGHT)
        height = min(height, curses.LINES - 4)
        
        # 计算宽度：基于最长选项文本
        width = self.DEFAULT_WIDTH
        for text, _ in options:
            width = max(width, len(text) + 12)  # 文本 + 序号 + 边距
        width = max(width, len(title) + 6)  # 至少能显示标题
        width = min(width, curses.COLS - 4)
        
        super().__init__(stdscr, title, width, height)
        self.options = options
        self.selected = 0
        self.result = None
        self.scroll_offset = 0  # 支持滚动
    
    def show(self) -> Any:
        try:
            self.draw_box()
            self.win.timeout(100) # 非阻塞
            
            # 计算可见选项数
            visible_count = self.height - 5  # 减去边框、标题、底部提示
            
            while True:
                self.stdscr.touchwin() # 强制标记父窗口为脏，确保完全重绘
                # 清除选项区域
                self.win.erase()
                self.win.border()
                
                # 绘制标题
                title_text = f" {self.title} "
                self.win.attron(curses.color_pair(COLOR_PAIRS['dialog_title']))
                self.win.addstr(0, (self.width - len(title_text)) // 2, title_text[:self.width-2])
                self.win.attroff(curses.color_pair(COLOR_PAIRS['dialog_title']))
                
                # 绘制可见选项
                for i in range(visible_count):
                    opt_idx = self.scroll_offset + i
                    if opt_idx >= len(self.options):
                        break
                    
                    text, value = self.options[opt_idx]
                    y = 2 + i
                    display = f"{opt_idx+1}. {text}"[:self.width-6]
                    
                    if opt_idx == self.selected:
                        self.win.attron(curses.color_pair(COLOR_PAIRS['menu_focus']))
                        self.win.addstr(y, 2, f"→ {display}")
                        self.win.attroff(curses.color_pair(COLOR_PAIRS['menu_focus']))
                    else:
                        self.win.addstr(y, 2, f"  {display}")
                
                # 底部提示
                hint = "↑↓:选择 Enter:确认 Q:取消"
                if len(self.options) > visible_count:
                    hint = f"↑↓:选择 ({self.selected+1}/{len(self.options)}) Enter:确认 Q:取消"
                self.win.addstr(self.height - 2, 2, hint[:self.width-4])
                
                self.win.refresh()
                
                # 处理按键
                key = self.win.getch()
                
                if key == curses.KEY_UP or key == ord('k'):
                    self.selected = (self.selected - 1) % len(self.options)
                    # 更新滚动
                    if self.selected < self.scroll_offset:
                        self.scroll_offset = self.selected
                elif key == curses.KEY_DOWN or key == ord('j'):
                    self.selected = (self.selected + 1) % len(self.options)
                    # 更新滚动
                    if self.selected >= self.scroll_offset + visible_count:
                        self.scroll_offset = self.selected - visible_count + 1
                elif key in (ord('\n'), ord('\r'), 10, 13):
                    self.result = self.options[self.selected][1]
                    break
                elif key in (ord('q'), ord('Q')):  # 使用 Q 取消
                    break
                elif ord('1') <= key <= ord('9'):
                    idx = key - ord('1')
                    if idx < len(self.options):
                        self.result = self.options[idx][1]
                        break
            
            return self.result
        except curses.error:
            return None


# ============================================================
# 主应用类
# ============================================================

class VDDTApp:
    """VDDT 终端应用"""
    
    def __init__(self, stdscr, config: VDDTConfig = None):
        self.stdscr = stdscr
        self.config = config or get_config()
        self.logger = get_logger()
        self.config_manager = ConfigManager()
        
        # 初始化
        init_colors()
        curses.curs_set(0)  # 隐藏光标
        self.stdscr.keypad(True)
        self.stdscr.timeout(100)  # 设置 100ms 超时，使 getch 非阻塞
        
        # 状态
        self.running = True
        self.current_menu = "main"
        self.menu_index = 0
        self.status_msg = "就绪"
        self.status_level = 'info'
        self.progress = 0.0
        self.progress_label = ""
        
        # 菜单定义
        self.menus = {
            'main': {
                'title': 'VDDT 多功能视频下载器 v2.1.0',
                'items': [
                    ('📥 下载功能', None, 'header'),
                    ('  下载单个视频', self._on_single_download, 'item', '1'),
                    ('  批量下载', self._on_batch_download, 'item', '2'),
                    ('', None, 'divider'),
                    ('🔧 工具', None, 'header'),
                    ('  离线转码', self._on_offline_transcode, 'item', '3'),
                    ('  查看日志', self._on_view_logs, 'item', '4'),
                    ('', None, 'divider'),
                    ('⚙ 设置', None, 'header'),
                    ('  下载设置', self._on_settings_download, 'item', '5'),
                    ('  网络设置', self._on_settings_network, 'item', '6'),
                    ('', None, 'divider'),
                    ('ℹ 其他', None, 'header'),
                    ('  关于 VDDT', self._on_about, 'item', 'A'),
                    ('  退出程序', self._on_quit, 'item', 'Q'),
                ]
            }
        }
    
    def run(self):
        """运行应用"""
        while self.running:
            self._draw()
            # _handle_input 内部会等待或超时
            self._handle_input()
        
        self._cleanup()
    
    def _cleanup(self):
        """清理资源"""
        self.config_manager.save()
    
    def _draw(self):
        """绘制界面"""
        try:
            h, w = self.stdscr.getmaxyx()
            
            if h < 10 or w < 40:
                self.stdscr.erase()
                self.stdscr.addstr(0, 0, "窗口太小".center(w-1)[:w-1])
                self.stdscr.refresh()
                return
            
            self.stdscr.erase()  # 使用 erase 减少闪烁
            
            # 标题栏
            title = self.menus[self.current_menu]['title']
            title_line = f"╔{'═' * (w - 4)}╗"
            title_text = f"║{title.center(w - 4)}║"
            title_bottom = f"╚{'═' * (w - 4)}╝"
            
            self.stdscr.attron(curses.color_pair(COLOR_PAIRS['title']))
            self.stdscr.addstr(0, 0, title_line[:w-1])
            self.stdscr.addstr(1, 0, title_text[:w-1])
            self.stdscr.addstr(2, 0, title_bottom[:w-1])
            self.stdscr.attroff(curses.color_pair(COLOR_PAIRS['title']))
            
            # 菜单项
            items = self.menus[self.current_menu]['items']
            selectable_indices = []
            
            y = 4
            for i, item in enumerate(items):
                if y >= h - 4:
                    break
                    
                text, callback, item_type = item[0], item[1], item[2]
                shortcut = item[3] if len(item) > 3 else None
                
                if item_type == 'header':
                    self.stdscr.attron(curses.color_pair(COLOR_PAIRS['menu_header']))
                    self.stdscr.addstr(y, 2, text[:w-4])
                    self.stdscr.attroff(curses.color_pair(COLOR_PAIRS['menu_header']))
                elif item_type == 'divider':
                    self.stdscr.addstr(y, 2, '─' * min(w - 4, 50))
                elif item_type == 'item':
                    selectable_indices.append(i)
                    display_text = f"{text}"
                    if shortcut:
                        display_text = f"({shortcut}) {text}"
                    
                    if selectable_indices.index(i) == self.menu_index:
                        self.stdscr.attron(curses.color_pair(COLOR_PAIRS['menu_focus']))
                        # 确保不写到屏幕最右下角字符
                        try:
                            self.stdscr.addstr(y, 2, f"→ {display_text}"[:w-4])
                        except curses.error: pass
                        self.stdscr.attroff(curses.color_pair(COLOR_PAIRS['menu_focus']))
                    else:
                        try:
                            self.stdscr.addstr(y, 2, f"  {display_text}"[:w-4])
                        except curses.error: pass
                
                y += 1
            
            self._selectable_indices = selectable_indices
            
            # 状态栏 (倒数第三行)
            status_y = h - 3
            try:
                self.stdscr.attron(curses.color_pair(COLOR_PAIRS['progress_bg']))
                self.stdscr.addstr(status_y, 0, ' ' * (w - 1))
                self.stdscr.attroff(curses.color_pair(COLOR_PAIRS['progress_bg']))
            except curses.error: pass
            
            # 进度条
            if self.progress > 0:
                progress_width = w - 10
                filled = int(progress_width * self.progress / 100)
                bar = '█' * filled + '░' * (progress_width - filled)
                progress_text = f"{self.progress_label} {self.progress:.1f}%"
                
                try:
                    self.stdscr.attron(curses.color_pair(COLOR_PAIRS['progress']))
                    self.stdscr.addstr(status_y, 2, bar[:progress_width])
                    self.stdscr.attroff(curses.color_pair(COLOR_PAIRS['progress']))
                    # 显示进度数值
                    self.stdscr.addstr(status_y, w - len(progress_text) - 2, progress_text)
                except curses.error: pass
            
            # 状态消息 (倒数第二行)
            status_style = {
                'info': COLOR_PAIRS['status'],
                'success': COLOR_PAIRS['status_success'],
                'error': COLOR_PAIRS['status_error'],
                'warning': COLOR_PAIRS['status_warning'],
            }.get(self.status_level, COLOR_PAIRS['status'])
            
            try:
                self.stdscr.attron(curses.color_pair(status_style))
                display_status = f" {self.status_msg} "
                self.stdscr.addstr(h - 2, 0, display_status.ljust(w - 1)[:w-1])
                self.stdscr.attroff(curses.color_pair(status_style))
            except curses.error: pass
            
            # 快捷键提示 (最后一行)
            try:
                help_text = " H:帮助 | Q:返回/取消/退出 | Ctrl+C:强制退出 "
                self.stdscr.addstr(h - 1, 0, help_text.center(w - 1)[:w-1])
            except curses.error: pass
            
            self.stdscr.refresh()
        except curses.error:
            pass
    
    def _handle_input(self):
        """处理输入"""
        key = self.stdscr.getch()
        
        # 处理 -1 (timeout)
        if key == -1:
            return
            
        items = self.menus[self.current_menu]['items']
        selectable = self._selectable_indices
        
        if key == curses.KEY_UP or key == ord('k'):
            if selectable:
                self.menu_index = (self.menu_index - 1) % len(selectable)
        elif key == curses.KEY_DOWN or key == ord('j'):
            if selectable:
                self.menu_index = (self.menu_index + 1) % len(selectable)
        elif key in (ord('\n'), ord('\r'), 10, 13):
            # 回车选择
            if selectable:
                idx = selectable[self.menu_index]
                callback = items[idx][1]
                if callback:
                    callback()
        elif key == ord('q') or key == ord('Q'):
            # Q 键返回或退出
            if self.current_menu == 'main':
                self._on_quit()
            else:
                self._back_to_main()
        elif key == ord('h') or key == ord('H'):
            self._show_help()
        elif key == ord('1'):
            self._quick_select(0)
        elif key == ord('2'):
            self._quick_select(1)
        elif key == ord('3'):
            self._quick_select(2)
        elif key == ord('4'):
            self._quick_select(3)
        elif key == ord('5'):
            self._quick_select(4)
        elif key == ord('6'):
            self._quick_select(5)
        elif key == ord('a') or key == ord('A'):
            self._quick_select(7)  # 关于
    
    def _quick_select(self, index: int):
        """快速选择菜单项"""
        items = self.menus[self.current_menu]['items']
        selectable = self._selectable_indices
        
        if index < len(selectable):
            idx = selectable[index]
            callback = items[idx][1]
            if callback:
                callback()
    
    def _set_status(self, msg: str, level: str = 'info'):
        """设置状态消息"""
        self.status_msg = msg
        self.status_level = level
    
    def _set_progress(self, value: float, label: str = ""):
        """设置进度"""
        self.progress = value
        self.progress_label = label
    
    def _back_to_main(self):
        """返回主菜单"""
        self.current_menu = 'main'
        self.menu_index = 0
    
    # ============================================================
    # 菜单回调
    # ============================================================
    
    def _on_single_download(self):
        """下载单个视频 - 显示二级菜单"""
        options = [
            ("自动下载 (最高画质)", 'auto'),
            ("选择画质后下载", 'select'),
            ("仅下载音频 (MP3)", 'audio'),
        ]
        
        select = SelectDialog(self.stdscr, "下载单个视频", options)
        mode = select.show()
        
        if mode is None:
            return
        
        dialog = InputDialog(self.stdscr, "下载视频", "请输入视频链接:")
        url = dialog.show()
        
        if not url:
            return
        
        self._set_status(f"准备下载: {url[:40]}...", 'info')
        self._set_progress(0, "下载中")
        
        # 实际下载逻辑
        def download_task():
            try:
                import yt_dlp
                
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'ignoreerrors': True,
                    'nocheckcertificate': True,
                    'outtmpl': os.path.join(self.config.download.output_dir, '%(title)s.%(ext)s'),
                }
                
                if mode == 'auto':
                    ydl_opts['format'] = 'bestvideo+bestaudio/best'
                    ydl_opts['merge_output_format'] = 'mp4'
                elif mode == 'audio':
                    ydl_opts['format'] = 'bestaudio'
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192'
                    }]
                elif mode == 'select':
                    # 先获取格式列表
                    ydl_opts['format'] = 'bestvideo+bestaudio/best'
                    ydl_opts['merge_output_format'] = 'mp4'
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                self._set_status("下载完成!", 'success')
                self._set_progress(100, "完成")
                
            except Exception as e:
                self.logger.exception(f"下载失败: {e}")
                self._set_status(f"下载失败: {str(e)[:30]}", 'error')
        
        threading.Thread(target=download_task, daemon=True).start()
    
    def _on_batch_download(self):
        """批量下载 - 显示二级菜单"""
        options = [
            ("从文件读取链接", 'file'),
            ("查看批量下载说明", 'help'),
        ]
        
        select = SelectDialog(self.stdscr, "批量下载", options)
        mode = select.show()
        
        if mode is None:
            return
        
        if mode == 'help':
            help_text = """批量下载说明:
1. 创建 download_list.txt 文件
2. 每行一个视频链接
3. 以 # 开头的行会被忽略
4. 选择"从文件读取链接"开始下载"""
            MessageDialog(self.stdscr, "批量下载说明", help_text, 'info').show()
            return
        
        dialog = InputDialog(self.stdscr, "批量下载", "请输入链接文件路径:", "download_list.txt")
        filepath = dialog.show()
        
        if filepath:
            if not os.path.exists(filepath):
                MessageDialog(self.stdscr, "错误", f"文件不存在: {filepath}", 'error').show()
                return
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    links = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                
                if not links:
                    MessageDialog(self.stdscr, "提示", "文件中没有有效链接", 'warning').show()
                    return
                
                # 选择下载模式
                mode_options = [
                    ("最高画质", 'best'),
                    ("仅音频", 'audio'),
                ]
                mode_select = SelectDialog(self.stdscr, "选择下载模式", mode_options)
                dl_mode = mode_select.show()
                
                if dl_mode is None:
                    return
                
                self._set_status(f"批量下载: {len(links)} 个链接", 'info')
                
                def batch_task():
                    try:
                        import yt_dlp
                        
                        ydl_opts = {
                            'quiet': True,
                            'no_warnings': True,
                            'ignoreerrors': True,
                            'nocheckcertificate': True,
                            'outtmpl': os.path.join(self.config.download.output_dir, '%(title)s.%(ext)s'),
                        }
                        
                        if dl_mode == 'audio':
                            ydl_opts['format'] = 'bestaudio'
                            ydl_opts['postprocessors'] = [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'mp3',
                                'preferredquality': '192'
                            }]
                        else:
                            ydl_opts['format'] = 'bestvideo+bestaudio/best'
                            ydl_opts['merge_output_format'] = 'mp4'
                        
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            for i, url in enumerate(links, 1):
                                self._set_status(f"[{i}/{len(links)}] 下载中...", 'info')
                                self._set_progress(i / len(links) * 100, f"下载 {i}/{len(links)}")
                                try:
                                    ydl.download([url])
                                except Exception as e:
                                    self.logger.error(f"下载失败 {url}: {e}")
                        
                        self._set_status("批量下载完成!", 'success')
                        self._set_progress(100, "完成")
                        
                    except Exception as e:
                        self.logger.exception(f"批量下载失败: {e}")
                        self._set_status(f"批量下载失败: {str(e)[:30]}", 'error')
                
                threading.Thread(target=batch_task, daemon=True).start()
                
            except Exception as e:
                MessageDialog(self.stdscr, "错误", f"读取文件失败: {e}", 'error').show()
    
    def _on_offline_transcode(self):
        """离线转码 - 先选文件/目录，再选格式"""
        # 1. 使用可视化文件浏览器选择文件或目录
        default_path = self.config.download.output_dir
        if not os.path.exists(default_path):
            try: os.makedirs(default_path, exist_ok=True)
            except: pass
            
        browser = FileBrowserDialog(self.stdscr, "选择待转码文件/目录", default_path)
        path = browser.show()
        
        if not path:
            return
            
        selected_files = []
        
        # 2. 处理选中的路径
        if os.path.isdir(path):
            video_exts = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.m4v', '.webm', '.ts', '.mp3', '.aac', '.flac', '.wav', '.m4a']
            files = sorted([f for f in os.listdir(path) 
                          if os.path.splitext(f)[1].lower() in video_exts])
            
            if not files:
                MessageDialog(self.stdscr, "提示", "文件夹中没有找到支持的视频文件", 'warning').show()
                return
            
            # 添加“所有文件”选项
            file_options = [("--- 处理文件夹内所有视频 ---", 'all')]
            file_options.extend([(f, os.path.join(path, f)) for f in files])
            
            file_select = SelectDialog(self.stdscr, "选择要转码的文件", file_options)
            choice = file_select.show()
            
            if choice is None:
                return
                
            if choice == 'all':
                selected_files = [os.path.join(path, f) for f in files]
            else:
                selected_files = [choice]
        else:
            selected_files = [path]
            
        if not selected_files:
            return

        # 3. 选择转码格式
        format_options = [
            ("原样复制 (Copy/Remux)", 'copy'),
            ("AMV 格式 (MP4播放器专用)", 'amv'),
            ("720p MP4 (H.264)", '720p'),
            ("1080p MP4 (H.264)", '1080p'),
            ("仅提取音频 (MP3 192k)", 'mp3'),
            ("自定义参数...", 'custom'),
        ]
        
        select = SelectDialog(self.stdscr, f"转码格式 ({len(selected_files)}个文件)", format_options)
        format_type = select.show()
        
        if format_type is None:
            return
        
        # 自定义参数处理
        custom_params = {}
        if format_type == 'custom':
            custom_params = self._get_custom_transcode_params()
            if not custom_params:
                return
        
        self._set_status(f"准备转码: {len(selected_files)} 个任务...", 'info')
        self._set_progress(0, "准备中")
        
        # 4. 执行转码逻辑
        def transcode_task():
            success_count = 0
            total = len(selected_files)
            
            try:
                from ffmpeg_progress_yield import FfmpegProgress
            except ImportError:
                FfmpegProgress = None

            for i, file_path in enumerate(selected_files, 1):
                try:
                    base_name = os.path.splitext(file_path)[0]
                    file_name = os.path.basename(file_path)
                    self._set_status(f"[{i}/{total}] 正在转码: {file_name[:30]}...", 'info')
                    
                    if format_type == 'copy':
                        ext = os.path.splitext(file_path)[1]
                        output = f"{base_name}_[VDDT]{ext if ext else '.mp4'}"
                        cmd = ["ffmpeg", "-i", file_path, "-c", "copy", output, "-y"]
                    elif format_type == "720p":
                        output = f"{base_name}_[VDDT]_720p.mp4"
                        cmd = ["ffmpeg", "-i", file_path, "-vf", "scale=-2:720", "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", output, "-y"]
                    elif format_type == "1080p":
                        output = f"{base_name}_[VDDT]_1080p.mp4"
                        cmd = ["ffmpeg", "-i", file_path, "-vf", "scale=-2:1080", "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", output, "-y"]
                    elif format_type == "mp3":
                        output = f"{base_name}_[VDDT].mp3"
                        cmd = ["ffmpeg", "-i", file_path, "-vn", "-acodec", "libmp3lame", "-b:a", "192k", output, "-y"]
                    elif format_type == "amv":
                        output = f"{base_name}_[VDDT].amv"
                        cmd = ["ffmpeg", "-i", file_path, "-s", "160x112", "-r", "30", "-c:v", "amv", "-c:a", "adpcm_ima_amv", output, "-y"]
                    elif format_type == "custom":
                        output_ext = custom_params.get('output_ext', 'mp4')
                        output = f"{base_name}_[VDDT]_custom.{output_ext}"
                        cmd = ["ffmpeg", "-i", file_path]
                        if custom_params.get('video_codec'): cmd.extend(["-c:v", custom_params['video_codec']])
                        if custom_params.get('resolution'): cmd.extend(["-vf", f"scale={custom_params['resolution']}"])
                        if custom_params.get('video_bitrate'): cmd.extend(["-b:v", custom_params['video_bitrate']])
                        if custom_params.get('crf'): cmd.extend(["-crf", str(custom_params['crf'])])
                        if custom_params.get('preset'): cmd.extend(["-preset", custom_params['preset']])
                        if custom_params.get('audio_codec'): cmd.extend(["-c:a", custom_params['audio_codec']])
                        if custom_params.get('audio_bitrate'): cmd.extend(["-b:a", custom_params['audio_bitrate']])
                        if custom_params.get('audio_only'): cmd.extend(["-vn"])
                        cmd.extend([output, "-y"])
                    
                    # 使用 FfmpegProgress 进行实时进度更新
                    if FfmpegProgress:
                        fp_runner = FfmpegProgress(cmd)
                        for progress in fp_runner.run_command_with_progress():
                            # 计算总进度: (已完成文件数 + 当前文件进度/100) / 总文件数
                            total_progress = ((i - 1) + (progress / 100.0)) / total * 100
                            self._set_progress(total_progress, f"文件 {i}/{total} - {progress:.1f}%")
                    else:
                        # 退回到普通执行
                        subprocess.run(cmd, capture_output=True, check=True)
                        self._set_progress(i / total * 100, f"进度 {i}/{total}")
                    
                    success_count += 1
                    
                except Exception as e:
                    self.logger.error(f"文件 {file_path} 转码失败: {e}")
            
            self._set_progress(100, "完成")
            if success_count == total:
                self._set_status(f"成功完成 {total} 个文件的转码任务", 'success')
            else:
                self._set_status(f"转码结束: 成功 {success_count}/{total}", 'warning')
        
        threading.Thread(target=transcode_task, daemon=True).start()
    
    def _get_custom_transcode_params(self) -> dict:
        """获取自定义转码参数"""
        params = {}
        
        # 选择输出格式
        format_options = [
            ("MP4 视频", 'mp4'),
            ("MKV 视频", 'mkv'),
            ("WebM 视频", 'webm'),
            ("MP3 音频", 'mp3'),
            ("AAC 音频", 'aac'),
        ]
        
        select = SelectDialog(self.stdscr, "输出格式", format_options)
        output_ext = select.show()
        
        if output_ext is None:
            return {}
        
        params['output_ext'] = output_ext
        
        # 视频参数（仅视频格式）
        if output_ext in ['mp4', 'mkv', 'webm']:
            # 视频编码器
            codec_options = [
                ("H.264 (libx264)", 'libx264'),
                ("H.265 (libx265)", 'libx265'),
                ("VP9 (libvpx-vp9)", 'libvpx-vp9'),
                ("复制原编码", 'copy'),
            ]
            
            select = SelectDialog(self.stdscr, "视频编码器", codec_options)
            codec = select.show()
            
            if codec is None:
                return {}
            
            params['video_codec'] = codec
            
            if codec != 'copy':
                # 分辨率
                res_options = [
                    ("保持原分辨率", None),
                    ("480p (854x480)", "-2:480"),
                    ("720p (1280x720)", "-2:720"),
                    ("1080p (1920x1080)", "-2:1080"),
                    ("自定义", 'custom'),
                ]
                
                select = SelectDialog(self.stdscr, "分辨率", res_options)
                res = select.show()
                
                if res is None:
                    return {}
                
                if res == 'custom':
                    dialog = InputDialog(self.stdscr, "分辨率", "输入分辨率 (如 1920:1080):")
                    custom_res = dialog.show()
                    if custom_res:
                        params['resolution'] = custom_res
                elif res:
                    params['resolution'] = res
                
                # CRF 质量
                crf_options = [
                    ("默认 (23)", 23),
                    ("高质量 (18)", 18),
                    ("较好质量 (20)", 20),
                    ("较小文件 (28)", 28),
                    ("自定义 CRF", 'custom'),
                ]
                
                select = SelectDialog(self.stdscr, "视频质量 (CRF)", crf_options)
                crf = select.show()
                
                if crf is None:
                    return {}
                
                if crf == 'custom':
                    dialog = InputDialog(self.stdscr, "CRF 值", "输入 CRF (0-51, 越小质量越高):", "23")
                    custom_crf = dialog.show()
                    if custom_crf and custom_crf.isdigit():
                        params['crf'] = int(custom_crf)
                elif crf:
                    params['crf'] = crf
                
                # 预设
                preset_options = [
                    ("默认 (medium)", 'medium'),
                    ("快速 (fast)", 'fast'),
                    ("更快速 (faster)", 'faster'),
                    ("慢速 (slow)", 'slow'),
                ]
                
                select = SelectDialog(self.stdscr, "编码预设", preset_options)
                preset = select.show()
                
                if preset:
                    params['preset'] = preset
        
        # 音频参数
        audio_options = [
            ("AAC 192kbps", ('aac', '192k')),
            ("AAC 256kbps", ('aac', '256k')),
            ("MP3 192kbps", ('libmp3lame', '192k')),
            ("复制原音频", ('copy', None)),
        ]
        
        select = SelectDialog(self.stdscr, "音频设置", audio_options)
        audio = select.show()
        
        if audio:
            params['audio_codec'] = audio[0]
            if audio[1]:
                params['audio_bitrate'] = audio[1]
        
        # 仅音频模式
        if output_ext in ['mp3', 'aac']:
            params['audio_only'] = True
            params['audio_codec'] = 'libmp3lame' if output_ext == 'mp3' else 'aac'
        
        return params
    
    def _on_view_logs(self):
        """查看日志 - 显示二级菜单"""
        options = [
            ("查看最新日志", 'latest'),
            ("选择日志文件", 'select'),
            ("清空日志文件", 'clear'),
        ]
        
        select = SelectDialog(self.stdscr, "查看日志", options)
        mode = select.show()
        
        if mode is None:
            return
        
        log_dir = os.path.join(os.getcwd(), 'logs')
        
        if mode == 'latest':
            if not os.path.exists(log_dir):
                MessageDialog(self.stdscr, "提示", "日志目录不存在", 'info').show()
                return
            
            log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
            if not log_files:
                MessageDialog(self.stdscr, "提示", "没有日志文件", 'info').show()
                return
            
            log_files.sort(reverse=True)
            filepath = os.path.join(log_dir, log_files[0])
            
        elif mode == 'select':
            if not os.path.exists(log_dir):
                MessageDialog(self.stdscr, "提示", "日志目录不存在", 'info').show()
                return
            
            log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
            if not log_files:
                MessageDialog(self.stdscr, "提示", "没有日志文件", 'info').show()
                return
            
            log_files.sort(reverse=True)
            file_options = [(f, f) for f in log_files]
            
            file_select = SelectDialog(self.stdscr, "选择日志文件", file_options)
            selected = file_select.show()
            
            if selected is None:
                return
            
            filepath = os.path.join(log_dir, selected)
            
        elif mode == 'clear':
            confirm = ConfirmDialog(self.stdscr, "确认", "确定要清空所有日志文件吗?")
            if confirm.show():
                if os.path.exists(log_dir):
                    for f in os.listdir(log_dir):
                        if f.endswith('.log'):
                            try:
                                os.remove(os.path.join(log_dir, f))
                            except:
                                pass
                MessageDialog(self.stdscr, "完成", "日志文件已清空", 'success').show()
            return
        
        # 显示日志内容
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 选择显示方式
            view_options = [
                ("最后 50 行", -50),
                ("最后 100 行", -100),
                ("全部内容", 0),
            ]
            
            view_select = SelectDialog(self.stdscr, "查看方式", view_options)
            view_mode = view_select.show()
            
            if view_mode is None:
                return
            
            if view_mode == 0:
                content = ''.join(lines)
            else:
                content = ''.join(lines[view_mode:])
            
            # 截断显示
            if len(content) > 2000:
                content = content[-2000:] + "\n...(内容过长，已截断)"
            
            MessageDialog(self.stdscr, f"日志: {os.path.basename(filepath)}", content, 'info').show()
            
        except Exception as e:
            MessageDialog(self.stdscr, "错误", f"读取日志失败: {e}", 'error').show()
    
    def _on_settings_download(self):
        """下载设置"""
        options = [
            (f"输出目录: {self.config.download.output_dir}", 'output_dir'),
            (f"并发下载数: {self.config.download.concurrent_downloads}", 'concurrent'),
            (f"最大重试次数: {self.config.download.max_retries}", 'max_retries'),
            (f"下载字幕: {'是' if self.config.download.download_subtitles else '否'}", 'subtitles'),
            (f"嵌入封面: {'是' if self.config.download.embed_thumbnail else '否'}", 'thumbnail'),
            (f"下载弹幕: {'是' if self.config.download.download_danmaku else '否'}", 'danmaku'),
        ]
        
        while True:
            select = SelectDialog(self.stdscr, "下载设置 (选择要修改的项)", options)
            selected = select.show()
            
            if selected is None:
                break
            
            if selected == 'output_dir':
                dialog = InputDialog(self.stdscr, "输出目录", "请输入输出目录:", 
                                    self.config.download.output_dir)
                new_val = dialog.show()
                if new_val:
                    self.config.download.output_dir = new_val
                    self._set_status("已更新输出目录", 'success')
                    
            elif selected == 'concurrent':
                dialog = InputDialog(self.stdscr, "并发下载数", "请输入并发数 (1-10):", 
                                    str(self.config.download.concurrent_downloads))
                new_val = dialog.show()
                if new_val and new_val.isdigit():
                    self.config.download.concurrent_downloads = min(10, max(1, int(new_val)))
                    self._set_status("已更新并发数", 'success')
            
            elif selected == 'max_retries':
                dialog = InputDialog(self.stdscr, "最大重试次数", "请输入重试次数 (1-20):", 
                                    str(self.config.download.max_retries))
                new_val = dialog.show()
                if new_val and new_val.isdigit():
                    self.config.download.max_retries = min(20, max(1, int(new_val)))
                    self._set_status("已更新最大重试次数", 'success')
                    
            elif selected == 'subtitles':
                self.config.download.download_subtitles = not self.config.download.download_subtitles
                self._set_status(f"下载字幕: {'开启' if self.config.download.download_subtitles else '关闭'}", 'success')
                
            elif selected == 'thumbnail':
                self.config.download.embed_thumbnail = not self.config.download.embed_thumbnail
                self._set_status(f"嵌入封面: {'开启' if self.config.download.embed_thumbnail else '关闭'}", 'success')
                
            elif selected == 'danmaku':
                self.config.download.download_danmaku = not self.config.download.download_danmaku
                self._set_status(f"下载弹幕: {'开启' if self.config.download.download_danmaku else '关闭'}", 'success')
            
            # 更新选项显示
            options = [
                (f"输出目录: {self.config.download.output_dir}", 'output_dir'),
                (f"并发下载数: {self.config.download.concurrent_downloads}", 'concurrent'),
                (f"最大重试次数: {self.config.download.max_retries}", 'max_retries'),
                (f"下载字幕: {'是' if self.config.download.download_subtitles else '否'}", 'subtitles'),
                (f"嵌入封面: {'是' if self.config.download.embed_thumbnail else '否'}", 'thumbnail'),
                (f"下载弹幕: {'是' if self.config.download.download_danmaku else '否'}", 'danmaku'),
            ]
    
    def _on_settings_network(self):
        """网络设置"""
        options = [
            (f"代理地址: {self.config.network.proxy or '未设置'}", 'proxy'),
            (f"超时时间: {self.config.network.timeout}秒", 'timeout'),
            (f"User-Agent: {self.config.network.user_agent[:30]}...", 'user_agent'),
        ]
        
        while True:
            select = SelectDialog(self.stdscr, "网络设置 (选择要修改的项)", options)
            selected = select.show()
            
            if selected is None:
                break
            
            if selected == 'proxy':
                dialog = InputDialog(self.stdscr, "代理设置", "请输入代理地址 (留空不使用):", 
                                    self.config.network.proxy or "")
                new_val = dialog.show()
                if new_val is not None:
                    self.config.network.proxy = new_val if new_val else ""
                    self._set_status("已更新代理设置", 'success')
                    
            elif selected == 'timeout':
                dialog = InputDialog(self.stdscr, "超时设置", "请输入超时时间(秒):", 
                                    str(self.config.network.timeout))
                new_val = dialog.show()
                if new_val and new_val.isdigit():
                    self.config.network.timeout = int(new_val)
                    self._set_status("已更新超时时间", 'success')
                    
            elif selected == 'user_agent':
                dialog = InputDialog(self.stdscr, "User-Agent", "请输入 User-Agent:", 
                                    self.config.network.user_agent)
                new_val = dialog.show()
                if new_val:
                    self.config.network.user_agent = new_val
                    self._set_status("已更新 User-Agent", 'success')
            
            # 更新选项显示
            options = [
                (f"代理地址: {self.config.network.proxy or '未设置'}", 'proxy'),
                (f"超时时间: {self.config.network.timeout}秒", 'timeout'),
                (f"User-Agent: {self.config.network.user_agent[:30]}...", 'user_agent'),
            ]
    
    def _on_about(self):
        """关于 - 显示二级菜单"""
        options = [
            ("关于 VDDT", 'about'),
            ("功能特点", 'features'),
            ("依赖信息", 'deps'),
            ("开源协议", 'license'),
        ]
        
        select = SelectDialog(self.stdscr, "关于", options)
        mode = select.show()
        
        if mode is None:
            return
        
        if mode == 'about':
            about_text = """
VDDT 多功能视频下载器

版本: 2.1.0
作者: Alex
引擎: yt-dlp + FFmpeg

基于强大的 yt-dlp 项目构建
让下载变得简单
"""
            MessageDialog(self.stdscr, "关于 VDDT", about_text.strip(), 'info').show()
            
        elif mode == 'features':
            features_text = """
功能特点:

• 支持 1000+ 网站下载
• 自动合并最高画质
• 字幕/封面/弹幕下载
• 批量下载支持
• 离线转码功能
• Cookie 登录支持
• 自定义文件名模板
• 多种转码预设
• TUI 图形界面
"""
            MessageDialog(self.stdscr, "功能特点", features_text.strip(), 'info').show()
            
        elif mode == 'deps':
            deps_text = """
依赖信息:

核心依赖:
• Python 3.8+
• yt-dlp (下载引擎)
• FFmpeg (合并/转码)

可选依赖:
• colorama (彩色输出)
• tqdm (进度条)
• requests (网络请求)
"""
            MessageDialog(self.stdscr, "依赖信息", deps_text.strip(), 'info').show()
            
        elif mode == 'license':
            license_text = """
开源协议: MIT License

Copyright (c) 2025 Alex

Permission is hereby granted, free of charge...
(详细协议内容请查看 LICENSE 文件)
"""
            MessageDialog(self.stdscr, "开源协议", license_text.strip(), 'info').show()
    
    def _show_help(self):
        """显示帮助"""
        help_text = """
快捷键帮助:

导航:
  ↑/k     上移
  ↓/j     下移
  Enter   选择
  Q       返回/取消/退出
  
全局:
  H       显示帮助
  1-6     快速选择菜单
  Ctrl+C  强制退出
"""
        MessageDialog(self.stdscr, "帮助", help_text.strip(), 'info').show()
    
    def _on_quit(self):
        """退出 - 显示二级菜单"""
        options = [
            ("退出程序", 'quit'),
            ("保存配置并退出", 'save_quit'),
            ("取消", 'cancel'),
        ]
        
        select = SelectDialog(self.stdscr, "退出确认", options)
        mode = select.show()
        
        if mode == 'quit':
            self.running = False
        elif mode == 'save_quit':
            self.config_manager.save()
            self._set_status("配置已保存", 'success')
            self.running = False


# ============================================================
# 入口函数
# ============================================================

def check_tui_support() -> Tuple[bool, str]:
    """检查 TUI 支持情况"""
    # 检查是否是交互式终端
    if not sys.stdout.isatty():
        return False, "TUI 需要交互式终端，请直接运行而不是通过管道"
    
    return True, ""


def run_tui(config: VDDTConfig = None) -> None:
    """运行 TUI 界面"""
    supported, error = check_tui_support()
    
    if not supported:
        print(f"{Fore.RED}[错误]{Style.RESET_ALL} {error}")
        return
    
    logger = get_logger()
    
    def main(stdscr):
        try:
            app = VDDTApp(stdscr, config)
            app.run()
        except Exception as e:
            logger.exception(f"TUI 运行时错误: {e}")
            raise
    
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        logger.info("用户中断退出")
    except Exception as e:
        logger.exception(f"TUI 启动失败: {e}")
        print(f"{Fore.RED}[错误]{Style.RESET_ALL} TUI 启动失败: {e}")


# ============================================================
# 测试
# ============================================================

if __name__ == '__main__':
    print("启动 VDDT TUI 界面...")
    run_tui()