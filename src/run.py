import os
from .app import app
from .config import config

if __name__ == '__main__':
    # 使用 gunicorn 启动
    if os.environ.get('PRODUCTION', 'false').lower() == 'true':
        import gunicorn.app.base

        class StandaloneApplication(gunicorn.app.base.BaseApplication):
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()

            def load_config(self):
                for key, value in self.options.items():
                    self.cfg.set(key.lower(), value)

            def load(self):
                return self.application

        options = {
            'bind': f'{config.API_HOST}:{config.API_PORT}',
            'workers': config.API_WORKERS,
            'worker_class': 'gevent',
            'timeout': 120,
            'accesslog': '-',
            'errorlog': '-'
        }

        StandaloneApplication(app, options).run()
    else:
        # 开发模式启动
        app.run(host=config.API_HOST, port=config.API_PORT, debug=True) 