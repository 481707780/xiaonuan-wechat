# ============================================================
# Soul Companion - 聊天 API 路由
# ============================================================
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from ..services.companion import chat, chat_stream
from ..services.session import session_manager

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    user_id: str = Field(..., description="用户唯一标识（微信OpenID等）")
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    companion_name: str = Field(default="小暖", description="伴侣名字")


class ChatResponse(BaseModel):
    reply: str
    user_id: str


class ClearRequest(BaseModel):
    user_id: str


@router.post("/chat")
async def api_chat(req: ChatRequest):
    """非流式聊天，支持分多条回复"""
    replies = await chat(
        user_id=req.user_id,
        message=req.message.strip(),
        companion_name=req.companion_name
    )
    return {"reply": replies[0], "extra_replies": replies[1:], "user_id": req.user_id}


@router.post("/chat/stream")
async def api_chat_stream(req: ChatRequest):
    """流式聊天（SSE），多条消息时只流式输出第一条"""
    async def event_stream():
        # 非流式调用 chat() 取第一条流式输出
        replies = await chat(
            user_id=req.user_id,
            message=req.message.strip(),
            companion_name=req.companion_name
        )
        first = replies[0] if replies else ""
        # 逐字输出（模拟流式效果）
        for token in first:
            yield f"data: {token}\n\n"
            await __import__("asyncio").sleep(0.02)
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/chat/clear")
async def api_clear(req: ClearRequest):
    """清除对话历史"""
    await session_manager.clear(req.user_id)
    return {"status": "ok", "message": "对话历史已清除"}


@router.get("/chat/history")
async def api_history(user_id: str):
    """获取对话历史"""
    context = await session_manager.get_context(user_id)
    return {"user_id": user_id, "messages": context, "count": len(context)}


@router.get("/chat/proactive-poll/{user_id}")
async def proactive_poll(user_id: str):
    """轮询主动消息（web前端用）"""
    from ..services.proactive import generate_msg, get_current_time_window
    from ..services.session import session_manager
    
    # 检查是否需要主动发消息
    sessions = await session_manager.get_all_sessions()
    now = __import__("datetime").datetime.now()
    
    for s in sessions:
        if s["user_id"] != user_id:
            continue
        hours = (now.timestamp() - s["last_active"]) / 3600
        if hours > 48:
            return {"proactive": False, "message": None}
        
        window = get_current_time_window()
        if window:
            msg = await generate_msg(user_id, window)
            if msg:
                return {"proactive": True, "message": msg, "trigger": window}
        
        # 沉默检测
        from ..services.proactive import SILENCE_TRIGGERS
        for st, (mn, mx) in SILENCE_TRIGGERS.items():
            if mn <= hours <= mx:
                msg = await generate_msg(user_id, st)
                if msg:
                    return {"proactive": True, "message": msg, "trigger": st}
    
    return {"proactive": False, "message": None}

