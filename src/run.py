import os
from .app import app
from .config import API_HOST, API_PORT, API_WORKERS

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
            'bind': f'{API_HOST}:{API_PORT}',
            'workers': API_WORKERS,
            'worker_class': 'gevent',
            'timeout': 120,
            'accesslog': '-',
            'errorlog': '-'
        }

        StandaloneApplication(app, options).run()
    else:
        # 开发模式启动
        app.run(host=API_HOST, port=API_PORT, debug=True) 