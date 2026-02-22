"""
VDDT Logger Module
日志系统模块 - 提供统一的日志记录功能

改进点：
1. 支持文件日志和控制台日志
2. 支持日志级别控制
3. 支持日志文件自动轮转
4. 彩色控制台输出
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional
from colorama import Fore, Style, init

# 初始化 colorama
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    LEVEL_COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # 获取颜色
        color = self.LEVEL_COLORS.get(record.levelno, Fore.WHITE)
        
        # 格式化时间
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # 构建日志消息
        level_name = record.levelname
        message = record.getMessage()
        
        # 彩色输出
        colored_msg = f"{color}[{timestamp}] [{level_name:^8}] {message}{Style.RESET_ALL}"
        
        # 添加异常信息
        if record.exc_info:
            colored_msg += f"\n{self.formatException(record.exc_info)}"
        
        return colored_msg


class VDDTLogger:
    """VDDT 日志管理器"""
    
    _instance: Optional['VDDTLogger'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'VDDTLogger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.logger = logging.getLogger('VDDT')
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()
        
        # 日志目录
        self.log_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 当前日志文件路径
        self.log_file = os.path.join(
            self.log_dir, 
            f"vddt_{datetime.now().strftime('%Y%m%d')}.log"
        )
        
        # 默认设置
        self._setup_handlers()
    
    def _setup_handlers(self, console_level: int = logging.INFO, file_level: int = logging.DEBUG):
        """设置日志处理器"""
        # 控制台处理器（彩色）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(ColoredFormatter())
        
        # 文件处理器（带轮转，最大5MB，保留3个备份）
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        
        # 添加处理器
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def set_level(self, level: int):
        """设置日志级别"""
        self.logger.setLevel(level)
    
    def debug(self, msg: str, *args, **kwargs):
        """调试日志"""
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        """信息日志"""
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """警告日志"""
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """错误日志"""
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        """严重错误日志"""
        self.logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        """异常日志（自动包含堆栈信息）"""
        self.logger.exception(msg, *args, **kwargs)


# 全局日志实例
def get_logger() -> VDDTLogger:
    """获取全局日志实例"""
    return VDDTLogger()


# 便捷函数
def debug(msg: str):
    get_logger().debug(msg)

def info(msg: str):
    get_logger().info(msg)

def warning(msg: str):
    get_logger().warning(msg)

def error(msg: str):
    get_logger().error(msg)

def critical(msg: str):
    get_logger().critical(msg)

def exception(msg: str):
    get_logger().exception(msg)


if __name__ == '__main__':
    # 测试日志功能
    logger = get_logger()
    logger.debug("这是一条调试消息")
    logger.info("这是一条信息消息")
    logger.warning("这是一条警告消息")
    logger.error("这是一条错误消息")
    
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("捕获到异常")
    
    print(f"\n日志文件位置: {logger.log_file}")
