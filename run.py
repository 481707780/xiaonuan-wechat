#!/usr/bin/env python
"""小暖 - 生产模式启动脚本"""
import sys, os

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

if __name__ == '__main__':
    import uvicorn
    from app.config import HOST, PORT
    print('小暖正在苏醒...')
    uvicorn.run('app.main:app', host=HOST, port=PORT, reload=False)