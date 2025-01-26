import os
from .app import app
from .config import config

if __name__ == '__main__':
    # 开发模式启动
    app.run(
        host=config.API_HOST, 
        port=config.API_PORT, 
        debug=os.environ.get('FLASK_ENV') != 'production'
    ) 