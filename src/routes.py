from flask import Blueprint, request, jsonify
from .subtitle import SubtitleProcessor
from .quick_subtitle import QuickSubtitleProcessor
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('api', __name__)
subtitle_processor = SubtitleProcessor()
quick_processor = QuickSubtitleProcessor()

@bp.route('/quick', methods=['GET', 'POST'])
def quick_subtitle():
    """快速获取字幕文本内容的API端点"""
    try:
        # 如果是 GET 请求，返回使用说明
        if request.method == 'GET':
            return jsonify({
                'status': 'info',
                'message': '这是字幕快速获取API，请使用POST方法，参数示例：',
                'example': {
                    'url': 'https://www.youtube.com/watch?v=xxxxx',
                    'lang': 'en'
                },
                'response_format': {
                    'status': 'success/error',
                    'text': '字幕文本内容',
                    'thumbnail': '视频缩略图URL',
                    'title': '视频标题',
                    'type': 'normal/auto'
                }
            })

        # POST 请求处理
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({
                'status': 'error',
                'message': '缺少必要的参数'
            }), 400

        url = data['url']
        lang = data.get('lang', 'en')
        
        logger.info(f"收到快速字幕请求: {data}")
        
        result = quick_processor.quick_process(url, lang)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"处理请求失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 