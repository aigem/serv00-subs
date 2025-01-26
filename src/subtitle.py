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
from .config import config

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
            'subtitlesformat': 'srt',
            'subtitleslangs': ['en'],
            'ignoreerrors': True,
            'no_warnings': True,
            'extract_flat': True,
            'outtmpl': str(config.SUBTITLE_DIR / '%(id)s.%(ext)s'),
            'quiet': False,  # 临时设为False以查看更多信息
            'verbose': True  # 添加详细输出
        }
        # 使用同步队列替代异步队列
        self.log_queue = Queue()
        self.error_stats = {
            'download_errors': 0,
            'convert_errors': 0,
            'validation_errors': 0
        }
        
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
            logger.debug(f"yt-dlp 配置: {self.ydl_opts}")
            
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                try:
                    logger.info(f"正在提取视频信息: {url}")
                    info = ydl.extract_info(url, download=False)  # 先只提取信息
                    video_id = info['id']
                    logger.info(f"视频ID: {video_id}")
                    
                    # 检查是否有字幕
                    if 'subtitles' in info and lang in info['subtitles']:
                        logger.info(f"找到{lang}语言的字幕")
                    elif 'automatic_captions' in info and lang in info['automatic_captions']:
                        logger.info(f"找到{lang}语言的自动生成字幕")
                    else:
                        logger.error(f"视频没有{lang}语言的字幕")
                        return {
                            'status': 'error',
                            'code': 'SUB_NOT_FOUND',
                            'message': f'视频没有{lang}语言的字幕'
                        }
                    
                    # 下载字幕
                    logger.info("开始下载字幕文件")
                    ydl.download([url])
                    
                    sub_path = config.SUBTITLE_DIR / f"{video_id}.{lang}.srt"
                    auto_sub_path = config.SUBTITLE_DIR / f"{video_id}.{lang}.auto.srt"
                    
                    logger.debug(f"检查字幕文件: {sub_path} 或 {auto_sub_path}")
                    
                    # 检查文件是否存在
                    if sub_path.exists():
                        logger.info(f"找到字幕文件: {sub_path}")
                        target_path = sub_path
                    elif auto_sub_path.exists():
                        logger.info(f"找到自动生成的字幕文件: {auto_sub_path}")
                        target_path = auto_sub_path
                    else:
                        # 列出目录内容以便调试
                        logger.debug("目录内容:")
                        for f in config.SUBTITLE_DIR.glob('*'):
                            logger.debug(f"- {f}")
                        
                        error_msg = f"字幕文件未找到: {sub_path} 或 {auto_sub_path}"
                        self.update_error_stats('download_errors')
                        logger.error(error_msg)
                        raise FileNotFoundError(f"字幕下载失败 - {error_msg}")
                    
                    content = target_path.read_text(encoding='utf-8')
                    logger.debug(f"字幕内容长度: {len(content)} 字符")
                    
                    result = {
                        'status': 'success',
                        'url': url,
                        'video_id': video_id,
                        'path': str(target_path),
                        'content': content
                    }
                    
                    logger.info(f"字幕下载成功: {url}")
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
            for f in config.SUBTITLE_DIR.glob('*'):
                if f.stat().st_mtime < cutoff:
                    f.unlink(missing_ok=True)
            for f in config.TEMP_DIR.glob('*'):
                if f.stat().st_mtime < cutoff:
                    f.unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"清理文件失败: {str(e)}")

    def _convert_to_txt(self, input_path: Path) -> Path:
        """优化的TXT转换"""
        output_path = config.TEMP_DIR / f"{input_path.stem}.txt"
        try:
            subprocess.run([
                config.FFMPEG_PATH,
                '-loglevel', 'error',
                '-i', str(input_path),
                '-f', 'srt',
                str(output_path)
            ], check=True, capture_output=True)
            return output_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg转换失败: {str(e)}")

    def _convert_to_json(self, input_path: Path) -> Path:
        """优化的JSON转换"""
        output_path = config.TEMP_DIR / f"{input_path.stem}.json"
        
        try:
            with input_path.open('r', encoding='utf-8') as f:
                srt_content = f.read()
                
            entries = []
            current_entry = {}
            
            for line in srt_content.split('\n'):
                line = line.strip()
                if line.isdigit():
                    if current_entry:
                        entries.append(current_entry)
                    current_entry = {'index': int(line)}
                elif '-->' in line:
                    start, end = line.split(' --> ')
                    current_entry['start'] = start
                    current_entry['end'] = end
                elif line:
                    if 'text' not in current_entry:
                        current_entry['text'] = line
                    else:
                        current_entry['text'] += f'\n{line}'
                        
            if current_entry:
                entries.append(current_entry)
                
            with output_path.open('w', encoding='utf-8') as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
                
            return output_path
        except Exception as e:
            raise RuntimeError(f"JSON转换失败: {str(e)}")

    def _upload_to_cdn(self, content: str, video_id: str) -> str:
        """CDN上传实现"""
        # TODO: 实现实际的CDN上传逻辑
        return f"{config.CDN_URL}/{video_id}"

    def process_single(self, url: str, lang: str, 
                      convert_to: Optional[str] = None) -> Dict:
        """处理单个URL的字幕"""
        temp_files = []
        try:
            # 1. 下载字幕
            sub_data = self.download_subtitle(url, lang)
            if sub_data['status'] != 'success':
                return sub_data
                
            # 2. 格式转换
            if convert_to:
                try:
                    converted_path = self.convert_format(
                        sub_data['path'],
                        convert_to
                    )
                    temp_files.append(converted_path)
                    sub_data['converted_path'] = str(converted_path)
                    sub_data['converted_content'] = converted_path.read_text()
                except Exception as e:
                    self.update_error_stats('convert_errors')
                    logger.error(f"转换失败: {str(e)}")
                    sub_data['convert_error'] = str(e)
                
            return sub_data
            
        finally:
            # 清理临时文件
            for f in temp_files:
                try:
                    f.unlink(missing_ok=True)
                except Exception as e:
                    logger.error(f"清理临时文件失败: {e}")

    def convert_format(self, input_path: str, target_format: str) -> Path:
        """转换字幕格式"""
        input_path = Path(input_path)
        valid_formats = {
            'txt': self._convert_to_txt,
            'json': self._convert_to_json
        }
        
        if target_format not in valid_formats:
            raise ValueError(f"不支持的格式: {target_format}")
            
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