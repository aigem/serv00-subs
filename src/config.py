# 配置文件
import os
from pathlib import Path
import multiprocessing

class Config:
    def __init__(self):
        # 基础路径配置
        self.BASE_DIR = Path(__file__).parent.parent
        self.SUBTITLE_DIR = self.BASE_DIR / os.getenv("SUBTITLE_DIR", "subtitles")
        self.TEMP_DIR = self.BASE_DIR / os.getenv("TEMP_DIR", "temp")
        
        # 确保目录存在
        self.SUBTITLE_DIR.mkdir(exist_ok=True)
        self.TEMP_DIR.mkdir(exist_ok=True)
        
        # API配置
        self.API_HOST = os.getenv("API_HOST", "0.0.0.0")
        self.API_PORT = int(os.getenv("API_PORT", 5000))
        
        # 性能配置
        cpu_count = multiprocessing.cpu_count()
        self.MAX_CONCURRENT_DOWNLOADS = min(
            int(os.getenv("MAX_CONCURRENT_DOWNLOADS", cpu_count * 2)), 
            32
        )
        self.CLEANUP_INTERVAL = int(os.getenv("CLEANUP_INTERVAL", 3600))
        self.FILE_RETENTION_HOURS = int(os.getenv("FILE_RETENTION_HOURS", 24))
               
        # 日志配置
        self.LOG_DIR = self.BASE_DIR / 'logs'
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FORMAT = os.getenv("LOG_FORMAT", 
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

config = Config() 