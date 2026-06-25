#!/usr/bin/env python
"""?? - ??????"""
import sys, os

# ??????????? emoji
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ????????????
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

if __name__ == '__main__':
    import uvicorn
    from app.config import HOST, PORT
    print('??????...')
    uvicorn.run('app.main:app', host=HOST, port=PORT, reload=True)
