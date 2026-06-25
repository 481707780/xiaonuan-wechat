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


@router.post("/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest):
    """非流式聊天"""
    reply = await chat(
        user_id=req.user_id,
        message=req.message.strip(),
        companion_name=req.companion_name
    )
    return ChatResponse(reply=reply, user_id=req.user_id)


@router.post("/chat/stream")
async def api_chat_stream(req: ChatRequest):
    """流式聊天（SSE）"""
    async def event_stream():
        async for token in chat_stream(
            user_id=req.user_id,
            message=req.message.strip(),
            companion_name=req.companion_name
        ):
            yield f"data: {token}\n\n"
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
