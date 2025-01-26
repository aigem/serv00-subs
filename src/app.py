from flask import Flask, request, jsonify
from flask_caching import Cache
from flask_compress import Compress
from .subtitle import SubtitleProcessor
from .config import config
import logging
import atexit
import shutil

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOG_DIR / 'service.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

# 配置缓存
app.config['CACHE_TYPE'] = config.CACHE_TYPE
app.config['CACHE_DEFAULT_TIMEOUT'] = config.CACHE_TTL
cache = Cache(app)

# 配置压缩，禁用 Brotli，只使用 gzip
app.config['COMPRESS_ALGORITHM'] = ['gzip']
app.config['COMPRESS_MIMETYPES'] = [
    'text/html',
    'text/css',
    'text/xml',
    'application/json',
    'application/javascript',
    'text/plain'
]
Compress(app)

# 创建字幕处理器实例
subtitle_processor = SubtitleProcessor()

def cleanup_temp_files():
    """清理临时文件"""
    try:
        shutil.rmtree(config.TEMP_DIR)
        config.TEMP_DIR.mkdir(exist_ok=True)
    except Exception as e:
        logging.error(f"清理临时文件失败: {e}")

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'message': 'Service is running'
    })

@app.route('/batch_subs', methods=['POST'])
@cache.memoize(timeout=config.CACHE_TTL)
def batch_download():
    """批量字幕处理接口"""
    try:
        data = request.get_json()
        
        if not data or 'urls' not in data:
            return jsonify({
                'status': 'error',
                'message': '缺少必要的URLs参数'
            }), 400
            
        urls = data.get('urls', [])
        if isinstance(urls, str):
            urls = [urls]
            
        if not isinstance(urls, list):
            return jsonify({
                'status': 'error',
                'message': 'URLs必须是字符串或列表'
            }), 400
            
        lang = data.get('lang', 'en')
        convert_to = data.get('convert')
        
        results = subtitle_processor.process_batch(urls, lang, convert_to)
        
        return jsonify({
            'status': 'success',
            'results': results
        })
        
    except Exception as e:
        logging.error(f"处理请求失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'status': 'error',
        'message': '未找到请求的资源'
    }), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({
        'status': 'error',
        'message': '服务器内部错误'
    }), 500

def shutdown_handler():
    """优雅关闭处理"""
    try:
        # 等待当前任务完成
        if hasattr(app, 'executor'):
            app.executor.shutdown(wait=True)
        # 清理临时文件
        cleanup_temp_files()
    except Exception as e:
        logging.error(f"关闭时发生错误: {e}")

atexit.register(shutdown_handler) 