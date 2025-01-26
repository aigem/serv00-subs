import re
import time
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import logging
from queue import Queue
import subprocess
from tenacity import retry, stop_after_attempt, wait_exponential
import yt_dlp
import webvtt
from .config import config
from functools import lru_cache
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

class SubtitleProcessor:
    # YouTube URL验证正则
    YT_REGEX = re.compile(
        r'^((?:https?:)?\/\/)?((?:www|m)\.)?'
        r'(?:youtube(-nocookie)?\.com|youtu\.be)'
        r'/(?:watch\?v=|embed/|v/|shorts/)?([\w-]{11})'
    )
    
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
            'quiet': True,
            'verbose': True  # 添加详细输出
        }
        # 使用同步队列替代异步队列
        self.log_queue = Queue()
        self.error_stats = {
            'download_errors': 0,
            'convert_errors': 0,
            'validation_errors': 0
        }
        # 缓存过期时间（分钟）
        self.cache_ttl = int(os.getenv("CACHE_TTL_MINUTES", 30))
        # 缓存结果
        self._cache = {}
        # 缓存时间戳
        self._cache_timestamps = {}
        
    def log_message(self, message: str, level: str = 'info'):
        """记录日志消息"""
        self.log_queue.put((level, message))
        self._process_logs()  # 立即处理日志
        
    def _process_logs(self):
        """处理日志队列"""
        while not self.log_queue.empty():
            try:
                level, message = self.log_queue.get_nowait()
                if level == 'error':
                    logger.error(message)
                else:
                    logger.info(message)
            except Queue.Empty:
                break

    def validate_url(self, url: str) -> bool:
        """验证YouTube URL"""
        return bool(self.YT_REGEX.match(url))
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def download_subtitle(self, url: str, lang: str) -> Dict:
        """下载字幕(带重试机制)"""
        try:
            logger.info(f"开始下载字幕: URL={url}, 语言={lang}")
            
            if not self.validate_url(url):
                error_msg = f"无效的YouTube URL: {url}"
                logger.error(error_msg)
                self.update_error_stats('validation_errors')
                raise ValueError(error_msg)
                
            self.ydl_opts['subtitleslangs'] = [lang]
            
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                try:
                    logger.info(f"正在提取视频信息: {url}")
                    info = ydl.extract_info(url, download=True)
                    video_id = info['id']
                    logger.info(f"视频ID: {video_id}")
                    
                    # 检查所有可能的字幕文件扩展名
                    for ext in ['vtt', 'ttml']:
                        sub_path = config.SUBTITLE_DIR / f"{video_id}.{lang}.{ext}"
                        auto_sub_path = config.SUBTITLE_DIR / f"{video_id}.{lang}.auto.{ext}"
                        
                        if sub_path.exists():
                            target_path = sub_path
                            break
                        elif auto_sub_path.exists():
                            target_path = auto_sub_path
                            break
                    else:
                        self.update_error_stats('download_errors')
                        raise FileNotFoundError("字幕下载失败")
                    
                    content = target_path.read_text(encoding='utf-8')
                    logger.info(f"字幕下载成功: {url}, 大小: {len(content)} 字符")
                    
                    result = {
                        'status': 'success',
                        'url': url,
                        'video_id': video_id,
                        'path': str(target_path),
                        'content': content
                    }
                    
                    return result
                    
                except yt_dlp.utils.DownloadError as e:
                    self.update_error_stats('download_errors')
                    error_msg = str(e)
                    logger.error(f"yt-dlp 下载错误: {error_msg}")
                    if 'No subtitles available' in error_msg:
                        return {'status': 'error', 'code': 'SUB_NOT_FOUND', 'message': '没有找到字幕'}
                    return {'status': 'error', 'code': 'DOWNLOAD_FAILED', 'message': f'下载失败: {error_msg}'}
                    
        except Exception as e:
            self.update_error_stats('download_errors')
            error_msg = str(e)
            logger.error(f"字幕下载过程中发生未知错误: {error_msg}")
            logger.exception("详细错误信息:")
            return {'status': 'error', 'code': 'UNKNOWN_ERROR', 'message': f'字幕下载失败: {error_msg}'}

    def process_batch(self, urls: List[str], lang: str = 'en', 
                     convert_to: Optional[str] = None) -> List[Dict]:
        """批量处理字幕下载和转换"""
        total = len(urls)
        completed = 0
        results = []
        
        with ThreadPoolExecutor(
            max_workers=config.MAX_CONCURRENT_DOWNLOADS
        ) as executor:
            future_to_url = {
                executor.submit(self.process_single, url, lang, convert_to): url 
                for url in urls
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.update_error_stats('process_errors')
                    logger.error(f"处理URL失败: {url}, 错误: {str(e)}")
                    results.append({
                        'status': 'error',
                        'url': url,
                        'code': 'PROCESS_FAILED',
                        'message': str(e)
                    })
                finally:
                    completed += 1
                    self.log_message(
                        f"处理进度: {completed}/{total} ({completed/total*100:.1f}%)"
                    )
        
        return results

    def _clean_old_files(self):
        """清理过期文件"""
        try:
            cutoff = time.time() - (config.FILE_RETENTION_HOURS * 3600)
            # 清理字幕目录
            for f in config.SUBTITLE_DIR.glob('*'):
                if f.stat().st_mtime < cutoff:
                    f.unlink(missing_ok=True)
                    logger.debug(f"清理过期字幕文件: {f}")
            
            # 清理临时目录
            for f in config.TEMP_DIR.glob('*'):
                if f.stat().st_mtime < cutoff:
                    f.unlink(missing_ok=True)
                    logger.debug(f"清理过期临时文件: {f}")
                    
        except Exception as e:
            logger.error(f"清理文件失败: {str(e)}")

    def _convert_to_txt(self, input_path: Path) -> Path:
        """使用 webvtt-py 将字幕文件转换为纯文本格式"""
        output_path = config.TEMP_DIR / f"{input_path.stem}.txt"
        try:
            # 读取 WebVTT 文件
            captions = webvtt.read(str(input_path))
            
            # 提取纯文本并处理
            lines = []
            for caption in captions:
                # 移除多余的空白字符并分割多行
                text_lines = [line.strip() for line in caption.text.split('\n')]
                # 过滤空行并添加到结果中
                lines.extend(line for line in text_lines if line)
            
            # 写入纯文本文件
            text_content = '\n'.join(lines)
            with output_path.open('w', encoding='utf-8') as f:
                f.write(text_content)
            
            return output_path
        except webvtt.errors.MalformedFileError as e:
            logger.error(f"WebVTT 文件格式错误: {e}")
            raise RuntimeError(f"WebVTT 解析失败: {str(e)}")
        except Exception as e:
            logger.error(f"文本转换失败: {e}")
            raise RuntimeError(f"文本转换失败: {str(e)}")

    def _convert_to_json(self, input_path: Path) -> Path:
        """使用 webvtt-py 将字幕文件转换为 JSON 格式"""
        output_path = config.TEMP_DIR / f"{input_path.stem}.json"
        try:
            # 读取 WebVTT 文件
            captions = webvtt.read(str(input_path))
            
            # 转换为 JSON 格式
            entries = []
            for i, caption in enumerate(captions, 1):
                entry = {
                    'index': i,
                    'start': caption.start,
                    'end': caption.end,
                    'text': caption.text.strip()
                }
                entries.append(entry)
            
            # 写入 JSON 文件
            with output_path.open('w', encoding='utf-8') as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
            
            return output_path
        except webvtt.errors.MalformedFileError as e:
            logger.error(f"WebVTT 文件格式错误: {e}")
            raise RuntimeError(f"WebVTT 解析失败: {str(e)}")
        except Exception as e:
            logger.error(f"JSON 转换失败: {e}")
            raise RuntimeError(f"JSON 转换失败: {str(e)}")

    def _convert_to_srt(self, input_path: Path) -> Path:
        """将 WebVTT 转换为 SRT 格式"""
        output_path = config.TEMP_DIR / f"{input_path.stem}.srt"
        try:
            # 读取 WebVTT 文件
            captions = webvtt.read(str(input_path))
            
            # 转换为 SRT 格式
            srt_lines = []
            for i, caption in enumerate(captions, 1):
                # 添加序号
                srt_lines.append(str(i))
                
                # 转换时间格式从 HH:MM:SS.mmm 到 HH:MM:SS,mmm
                start = caption.start.replace('.', ',')
                end = caption.end.replace('.', ',')
                srt_lines.append(f"{start} --> {end}")
                
                # 添加字幕文本
                srt_lines.append(caption.text.strip())
                
                # 添加空行
                srt_lines.append('')
            
            # 写入 SRT 文件
            srt_content = '\n'.join(srt_lines)
            with output_path.open('w', encoding='utf-8') as f:
                f.write(srt_content)
            
            return output_path
        except webvtt.errors.MalformedFileError as e:
            logger.error(f"WebVTT 文件格式错误: {e}")
            raise RuntimeError(f"WebVTT 解析失败: {str(e)}")
        except Exception as e:
            logger.error(f"SRT 转换失败: {e}")
            raise RuntimeError(f"SRT 转换失败: {str(e)}")

    def _upload_to_cdn(self, content: str, video_id: str) -> str:
        """CDN上传实现"""
        # TODO: 实现实际的CDN上传逻辑
        return f"{config.CDN_URL}/{video_id}"

    def _get_cache_key(self, url: str, lang: str, convert_to: Optional[str] = None) -> str:
        """生成缓存键"""
        return f"{url}:{lang}:{convert_to}"
        
    def _get_from_cache(self, url: str, lang: str, convert_to: Optional[str] = None) -> Optional[Dict]:
        """从缓存获取结果"""
        cache_key = self._get_cache_key(url, lang, convert_to)
        if cache_key in self._cache:
            # 检查是否过期
            timestamp = self._cache_timestamps.get(cache_key)
            if timestamp and datetime.now() - timestamp < timedelta(minutes=self.cache_ttl):
                logger.info(f"从缓存获取结果: {url}")
                return self._cache[cache_key]
            else:
                # 删除过期缓存
                self._cache.pop(cache_key, None)
                self._cache_timestamps.pop(cache_key, None)
        return None
        
    def _save_to_cache(self, url: str, lang: str, convert_to: Optional[str], result: Dict):
        """保存结果到缓存"""
        cache_key = self._get_cache_key(url, lang, convert_to)
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = datetime.now()
        
        # 清理过期缓存
        self._clean_expired_cache()
        
    def _clean_expired_cache(self):
        """清理过期缓存"""
        now = datetime.now()
        expired_keys = [
            key for key, timestamp in self._cache_timestamps.items()
            if now - timestamp >= timedelta(minutes=self.cache_ttl)
        ]
        for key in expired_keys:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
            
    def process_single(self, url: str, lang: str, 
                      convert_to: Optional[str] = None) -> Dict:
        """处理单个URL的字幕
        Args:
            url: YouTube URL
            lang: 字幕语言代码
            convert_to: 转换格式，可选值：txt, json, srt, None（默认不转换）
        """
        try:
            # 1. 检查缓存
            cached_result = self._get_from_cache(url, lang, convert_to)
            if cached_result:
                return cached_result
                
            # 2. 下载字幕
            sub_data = self.download_subtitle(url, lang)
            if sub_data['status'] != 'success':
                return sub_data
                
            # 3. 格式转换（如果指定了转换格式）
            if convert_to and convert_to.lower() in ['txt', 'json', 'srt']:
                try:
                    converted_path = self.convert_format(
                        sub_data['path'],
                        convert_to.lower()
                    )
                    sub_data['converted_path'] = str(converted_path)
                    sub_data['converted_content'] = converted_path.read_text(encoding='utf-8')
                except Exception as e:
                    self.update_error_stats('convert_errors')
                    logger.error(f"转换失败: {str(e)}")
                    sub_data['convert_error'] = str(e)
            
            # 4. 保存到缓存
            self._save_to_cache(url, lang, convert_to, sub_data)
            return sub_data
            
        except Exception as e:
            logger.error(f"处理单个URL失败: {str(e)}")
            return {
                'status': 'error',
                'code': 'PROCESS_FAILED',
                'message': str(e)
            }

    def convert_format(self, input_path: str, target_format: str) -> Path:
        """转换字幕格式
        Args:
            input_path: 输入文件路径
            target_format: 目标格式，支持：txt, json, srt
        Returns:
            转换后的文件路径
        Raises:
            ValueError: 不支持的格式
        """
        input_path = Path(input_path)
        target_format = target_format.lower()
        valid_formats = {
            'txt': self._convert_to_txt,
            'json': self._convert_to_json,
            'srt': self._convert_to_srt
        }
        
        if target_format not in valid_formats:
            raise ValueError(f"不支持的格式: {target_format}，支持的格式: {', '.join(valid_formats.keys())}")
            
        return valid_formats[target_format](input_path)

    def update_error_stats(self, error_type: str):
        """更新错误统计"""
        if error_type in self.error_stats:
            self.error_stats[error_type] += 1
            if self.error_stats[error_type] % 10 == 0:
                self.log_message(
                    f"错误统计: {self.error_stats}", 
                    'error'
                ) 