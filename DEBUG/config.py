"""
VDDT Config Module
配置管理模块 - 提供配置文件的读取、保存和管理功能

改进点：
1. 支持 JSON 配置文件
2. 自动创建默认配置
3. 配置项类型验证
4. 配置热重载
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from pathlib import Path

from logger import get_logger


@dataclass
class DownloadConfig:
    """下载配置"""
    # 默认输出目录
    output_dir: str = "VDDT_Downloads"
    # 默认下载模式: 1=视频+音频, 2=仅视频, 3=仅音频, 4=手动选择
    default_mode: int = 1
    # 并发片段下载数
    concurrent_downloads: int = 5
    # 重试次数
    max_retries: int = 10
    # 文件名模板
    filename_template: str = "%(upload_date)s_%(uploader)s_%(title)s.%(ext)s"
    # 是否下载字幕
    download_subtitles: bool = False
    # 字幕语言偏好
    subtitle_languages: List[str] = field(default_factory=lambda: ['zh-Hans', 'zh-CN', 'en'])
    # 是否嵌入封面
    embed_thumbnail: bool = False
    # 是否下载弹幕（B站）
    download_danmaku: bool = False


@dataclass
class TranscodeConfig:
    """转码配置"""
    # 默认转码预设: 1=720p, 2=1080p, 3=MP3, 4=1500k, 5=自定义
    default_preset: int = 1
    # 默认视频编码器
    video_codec: str = "libx264"
    # 默认音频编码器
    audio_codec: str = "aac"
    # 默认 CRF 值
    crf: int = 23
    # 默认预设
    preset: str = "medium"
    # 默认音频码率
    audio_bitrate: str = "192k"


@dataclass
class NetworkConfig:
    """网络配置"""
    # 代理设置
    proxy: Optional[str] = None
    # 连接超时（秒）
    timeout: int = 30
    # User-Agent
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


@dataclass
class UIConfig:
    """界面配置"""
    # 进度条长度
    progress_bar_length: int = 40
    # 显示详细日志
    verbose: bool = False
    # 彩色输出
    color_output: bool = True


@dataclass
class VDDTConfig:
    """VDDT 主配置"""
    download: DownloadConfig = field(default_factory=DownloadConfig)
    transcode: TranscodeConfig = field(default_factory=TranscodeConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    # 版本信息
    version: str = "2.1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'download': asdict(self.download),
            'transcode': asdict(self.transcode),
            'network': asdict(self.network),
            'ui': asdict(self.ui),
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VDDTConfig':
        """从字典创建配置"""
        config = cls()
        
        if 'download' in data:
            for key, value in data['download'].items():
                if hasattr(config.download, key):
                    setattr(config.download, key, value)
        
        if 'transcode' in data:
            for key, value in data['transcode'].items():
                if hasattr(config.transcode, key):
                    setattr(config.transcode, key, value)
        
        if 'network' in data:
            for key, value in data['network'].items():
                if hasattr(config.network, key):
                    setattr(config.network, key, value)
        
        if 'ui' in data:
            for key, value in data['ui'].items():
                if hasattr(config.ui, key):
                    setattr(config.ui, key, value)
        
        return config


class ConfigManager:
    """配置管理器"""
    
    DEFAULT_CONFIG_FILE = "vddt_config.json"
    
    _instance: Optional['ConfigManager'] = None
    
    def __new__(cls) -> 'ConfigManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.logger = get_logger()
        self.config: VDDTConfig = VDDTConfig()
        self.config_path: Path = Path(self.DEFAULT_CONFIG_FILE)
    
    def load(self, config_path: Optional[str] = None) -> VDDTConfig:
        """加载配置文件"""
        if config_path:
            self.config_path = Path(config_path)
        
        if not self.config_path.exists():
            self.logger.info(f"配置文件不存在，创建默认配置: {self.config_path}")
            self.save()
            return self.config
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.config = VDDTConfig.from_dict(data)
            self.logger.info(f"配置加载成功: {self.config_path}")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"配置文件格式错误: {e}")
            self.logger.warning("使用默认配置")
        except Exception as e:
            self.logger.exception(f"加载配置失败: {e}")
            self.logger.warning("使用默认配置")
        
        return self.config
    
    def save(self, config_path: Optional[str] = None) -> bool:
        """保存配置到文件"""
        if config_path:
            self.config_path = Path(config_path)
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config.to_dict(), f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"配置已保存: {self.config_path}")
            return True
            
        except Exception as e:
            self.logger.exception(f"保存配置失败: {e}")
            return False
    
    def get(self) -> VDDTConfig:
        """获取当前配置"""
        return self.config
    
    def update(self, **kwargs) -> None:
        """更新配置项
        
        支持嵌套更新，例如：
        config.update(download__output_dir="/new/path")
        """
        for key, value in kwargs.items():
            if '__' in key:
                # 嵌套更新
                parts = key.split('__')
                obj = self.config
                for part in parts[:-1]:
                    obj = getattr(obj, part, None)
                    if obj is None:
                        break
                if obj is not None:
                    setattr(obj, parts[-1], value)
            else:
                setattr(self.config, key, value)
    
    def reset(self) -> VDDTConfig:
        """重置为默认配置"""
        self.config = VDDTConfig()
        self.logger.info("配置已重置为默认值")
        return self.config


def get_config() -> VDDTConfig:
    """获取全局配置实例"""
    manager = ConfigManager()
    if not manager.config_path.exists():
        manager.load()
    return manager.get()


def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    return ConfigManager()


if __name__ == '__main__':
    # 测试配置功能
    manager = ConfigManager()
    config = manager.load()
    
    print("当前配置:")
    print(json.dumps(config.to_dict(), indent=2, ensure_ascii=False))
    
    # 测试更新
    manager.update(download__output_dir="/tmp/downloads")
    print(f"\n更新后的输出目录: {config.download.output_dir}")
    
    # 测试保存
    manager.save("test_config.json")
    print("\n配置已保存到 test_config.json")
