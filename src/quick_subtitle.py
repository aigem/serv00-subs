import logging
from typing import Dict, Optional
import yt_dlp
from pathlib import Path
import xml.etree.ElementTree as ET
from .config import config

logger = logging.getLogger(__name__)

class QuickSubtitleProcessor:
    """快速字幕处理器，专门用于快速返回转换后的文本内容"""
    
    def __init__(self):
        self.ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitlesformat': 'ttml',
            'subtitleslangs': ['en'],
            'ignoreerrors': True,
            'no_warnings': True,
            'extract_flat': True,
            'outtmpl': str(config.SUBTITLE_DIR / '%(id)s.%(ext)s'),
            'quiet': True
        }

    def quick_process(self, url: str, lang: str = 'en') -> Dict:
        """快速处理单个URL的字幕并返回文本内容
        Args:
            url: YouTube URL
            lang: 字幕语言代码
        Returns:
            Dict: {
                'status': 'success' | 'error',
                'text': str,  # 转换后的文本内容
                'thumbnail': str,  # 缩略图URL
                'title': str,  # 视频标题
                'error': str  # 如果有错误
            }
        """
        try:
            # 1. 先尝试下载普通字幕
            normal_opts = self.ydl_opts.copy()
            normal_opts.update({
                'writesubtitles': True,
                'writeautomaticsub': False,
                'subtitleslangs': [lang]
            })
            
            with yt_dlp.YoutubeDL(normal_opts) as ydl:
                try:
                    logger.info(f"尝试下载普通字幕: {url}")
                    info = ydl.extract_info(url, download=True)
                    video_id = info['id']
                    title = info.get('title', '')
                    # 获取最高质量的缩略图
                    thumbnails = info.get('thumbnails', [])
                    thumbnail = thumbnails[-1]['url'] if thumbnails else info.get('thumbnail', '')
                    
                    # 检查普通字幕文件
                    possible_paths = [
                        config.SUBTITLE_DIR / f"{video_id}.{lang}.ttml",
                        config.SUBTITLE_DIR / f"{video_id}.en.ttml"
                    ]
                    
                    for sub_path in possible_paths:
                        if sub_path.exists():
                            logger.info(f"找到普通字幕: {sub_path}")
                            text_content = self._extract_text(sub_path)
                            return {
                                'status': 'success',
                                'text': text_content,
                                'thumbnail': thumbnail,
                                'title': title,
                                'type': 'normal'
                            }
                            
                except Exception as e:
                    logger.info(f"未找到普通字幕，尝试自动生成字幕: {str(e)}")
            
            # 2. 如果没有普通字幕，尝试下载自动生成的字幕
            auto_opts = self.ydl_opts.copy()
            auto_opts.update({
                'writesubtitles': False,
                'writeautomaticsub': True,
                'subtitleslangs': [lang]
            })
            
            with yt_dlp.YoutubeDL(auto_opts) as ydl:
                try:
                    logger.info(f"尝试下载自动生成字幕: {url}")
                    info = ydl.extract_info(url, download=True)
                    video_id = info['id']
                    title = info.get('title', '')
                    # 获取最高质量的缩略图
                    thumbnails = info.get('thumbnails', [])
                    thumbnail = thumbnails[-1]['url'] if thumbnails else info.get('thumbnail', '')
                    
                    # 检查自动生成的字幕文件
                    possible_auto_paths = [
                        config.SUBTITLE_DIR / f"{video_id}.{lang}.ttml",
                        config.SUBTITLE_DIR / f"{video_id}.en.ttml",
                        config.SUBTITLE_DIR / f"{video_id}.{lang}.auto.ttml"
                    ]
                    
                    for auto_sub_path in possible_auto_paths:
                        if auto_sub_path.exists():
                            logger.info(f"找到自动生成字幕: {auto_sub_path}")
                            text_content = self._extract_text(auto_sub_path)
                            return {
                                'status': 'success',
                                'text': text_content,
                                'thumbnail': thumbnail,
                                'title': title,
                                'type': 'auto'
                            }
                    
                    return {
                        'status': 'error',
                        'error': '未找到任何字幕文件',
                        'title': title,
                        'thumbnail': thumbnail
                    }
                    
                except Exception as e:
                    logger.error(f"字幕下载失败: {str(e)}")
                    return {
                        'status': 'error',
                        'error': str(e)
                    }
                    
        except Exception as e:
            logger.error(f"快速处理失败: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _extract_text(self, ttml_path: Path) -> str:
        """从TTML文件提取纯文本内容"""
        try:
            # 读取TTML文件
            with open(ttml_path, 'r', encoding='utf-8') as f:
                ttml_content = f.read()

            # 解析XML
            root = ET.fromstring(ttml_content)
            # 查找所有文本元素
            text_elements = root.findall(".//{*}p")

            # 提取并合并文本
            lines = []
            for elem in text_elements:
                text = ''.join(elem.itertext()).strip()
                if text:
                    lines.append(text)

            return '\n'.join(lines)

        except Exception as e:
            logger.error(f"文本提取失败: {e}")
            raise RuntimeError(f"文本提取失败: {str(e)}") 