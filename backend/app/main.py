# ============================================================
# 小暖 - FastAPI 主入口（风格数据注入版）
# ============================================================
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import os

from .config import HOST, PORT, COMPANION_NAME
from .routers import chat, wechat
from .services.style_loader import load_style_profile, reload as reload_style
from .services.proactive import engine as proactive_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"💕 {COMPANION_NAME} 正在苏醒…")

    # 启动时检查风格数据注入状态
    profile = load_style_profile()
    if profile and profile.get("profile"):
        total = profile.get("total_messages", 0)
        logger.info(f"🌸 风格数据已注入：{total} 条消息分析 + {len(profile.get('examples', []))} 个风格例句")
    else:
        logger.warning("⚠️  未找到风格数据文件，将使用默认提示词")

    # 启动主动消息引擎
    asyncio.ensure_future(proactive_engine.run(interval=30))
    logger.info(f"💬 主动消息引擎已启动")

    yield

    # 停止主动引擎
    proactive_engine.stop()
    logger.info(f"💤 {COMPANION_NAME} 进入梦乡…")


app = FastAPI(
    title="小暖 - Soul Companion",
    description="你的 AI 情感伴侣，已注入真实聊天风格数据",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(chat.router)
app.include_router(wechat.router)

# 静态文件（前端）
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend")
frontend_dir = os.path.abspath(frontend_dir)
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
async def root():
    """主页 - 返回聊天界面"""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": f"💕 {COMPANION_NAME} 在线中", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok", "companion": COMPANION_NAME, "style_injected": True}


# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
