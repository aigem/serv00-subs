from flask import Flask, request, jsonify
from .subtitle import SubtitleProcessor
from .config import config
import logging
import atexit
import shutil
from pathlib import Path
import os
from .routes import bp

# 确保日志目录存在
log_dir = Path(__file__).parent.parent / 'logs'
log_dir.mkdir(exist_ok=True, parents=True)

# 设置日志文件路径
log_file = log_dir / 'service.log'

# 配置根日志器
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8', mode='a'),
        logging.StreamHandler()
    ]
)

# 获取根日志器
logger = logging.getLogger()
logger.setLevel(getattr(logging, config.LOG_LEVEL))

# 移除所有现有的处理器
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# 添加新的处理器
file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
stream_handler = logging.StreamHandler()

# 设置格式器
formatter = logging.Formatter(config.LOG_FORMAT)
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# 添加处理器到根日志器
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# 创建Flask应用
app = Flask(__name__)

# 注册Blueprint
app.register_blueprint(bp, url_prefix='/')

# 添加CORS支持
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

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
def batch_download():
    """批量字幕处理接口"""
    try:
        data = request.get_json()
        # 记录请求信息时排除内容数据
        log_data = {
            'urls': data.get('urls'),
            'lang': data.get('lang'),
            'convert': data.get('convert')
        }
        logger.info(f"收到字幕下载请求: {log_data}")
        
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
        
        logger.info(f"开始处理URLs: {urls}, 语言: {lang}, 转换格式: {convert_to}")
        results = subtitle_processor.process_batch(urls, lang, convert_to)
        
        # 记录结果时排除内容数据
        log_results = []
        for result in results:
            log_result = result.copy()
            if 'content' in log_result:
                log_result['content'] = f"<{len(log_result['content'])} chars>"
            if 'converted_content' in log_result:
                log_result['converted_content'] = f"<{len(log_result['converted_content'])} chars>"
            log_results.append(log_result)
            
        logger.info(f"处理完成，结果: {log_results}")
        
        return jsonify({
            'status': 'success',
            'results': results
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"处理请求失败: {error_msg}")
        return jsonify({
            'status': 'error',
            'message': error_msg
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

if __name__ == '__main__':
    app.run(
        host=config.API_HOST,
        port=config.API_PORT,
        debug=True
    ) 