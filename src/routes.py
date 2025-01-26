from flask import Blueprint, request, jsonify
from .subtitle import SubtitleProcessor
from .quick_subtitle import QuickSubtitleProcessor
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('api', __name__)
subtitle_processor = SubtitleProcessor()
quick_processor = QuickSubtitleProcessor()

@bp.route('/quick', methods=['POST'])
def quick_subtitle():
    """快速获取字幕文本内容的API端点"""
    try:
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