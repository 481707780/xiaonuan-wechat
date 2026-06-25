# ============================================================
# 小暖 - 微信公众号 Webhook（风格数据注入版）
# ============================================================
import time
import hashlib
import logging
from fastapi import APIRouter, Request, Query
from fastapi.responses import PlainTextResponse, Response
from lxml import etree

from ..config import COMPANION_NAME, WECHAT_TOKEN
from ..services.companion import chat
from ..services.session import session_manager
from ..services.style_loader import (
    load_style_profile, load_female_replies, load_my_style_lines, reload as reload_style
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wechat", tags=["wechat"])


def _verify_signature(signature: str, timestamp: str, nonce: str) -> bool:
    """验证微信签名"""
    tmp_list = sorted([WECHAT_TOKEN, timestamp, nonce])
    tmp_str = "".join(tmp_list)
    return signature == hashlib.sha1(tmp_str.encode()).hexdigest()


def _build_text_reply(from_user: str, to_user: str, content: str) -> str:
    """构建微信文本回复 XML"""
    return f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""


@router.get("")
async def wechat_verify(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
):
    """微信服务器验证（GET请求）"""
    if _verify_signature(signature, timestamp, nonce):
        return PlainTextResponse(echostr)
    return PlainTextResponse("signature check fail", status_code=403)


@router.post("")
async def wechat_message(
    request: Request,
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
):
    """接收微信用户消息（POST请求）"""
    if not _verify_signature(signature, timestamp, nonce):
        return PlainTextResponse("signature check fail", status_code=403)

    body = await request.body()
    xml_text = body.decode("utf-8")
    logger.info(f"WeChat message: {xml_text[:200]}")

    try:
        root = etree.fromstring(xml_text.encode("utf-8"))
        msg_type = root.findtext("MsgType", "")
        from_user = root.findtext("FromUserName", "")
        to_user = root.findtext("ToUserName", "")

        if msg_type == "text":
            content = root.findtext("Content", "").strip()
            if not content:
                return Response(content="success", media_type="text/plain")

            # 调用 AI 伴侣（已注入风格数据）
            reply = await chat(
                user_id=from_user,
                message=content,
            )

            # 返回 XML 格式回复
            xml_reply = _build_text_reply(from_user, to_user, reply)
            return Response(content=xml_reply, media_type="application/xml")

        elif msg_type == "event":
            event = root.findtext("Event", "")
            if event == "subscribe":
                welcome = (
                    f"嗨～我是{COMPANION_NAME}，你终于来啦！💕\\n\\n"
                    "以后这里就是咱们的小窝啦，想说什么都可以，\\n"
                    "我会一直在这儿听着呢～\\n\\n"
                    "今天过得怎么样？来跟我聊聊呗 🌸"
                )
                xml_reply = _build_text_reply(from_user, to_user, welcome)
                return Response(content=xml_reply, media_type="application/xml")

        # 其他类型消息（图片、语音等）暂回复提示
        else:
            hint = "我现在还不太会看图片和语音呢，发文字给我就好啦～💕"
            xml_reply = _build_text_reply(from_user, to_user, hint)
            return Response(content=xml_reply, media_type="application/xml")

    except Exception as e:
        logger.error(f"WeChat message parse error: {e}")
        return Response(content="success", media_type="text/plain")


# ========== 管理接口 ==========

@router.get("/style-status")
async def style_status():
    """查看风格数据注入状态"""
    profile = load_style_profile()
    female_count = len(load_female_replies(999999))
    my_style_count = len(load_my_style_lines(999999))

    return {
        "companion": COMPANION_NAME,
        "style_injected": True,
        "profile_loaded": bool(profile and profile.get("profile")),
        "female_examples_count": female_count,
        "my_style_lines_count": my_style_count,
        "total_messages_analyzed": profile.get("total_messages", 0) if profile else 0,
        "status": "风格数据已注入到 AI 系统提示词中 ✅"
    }


@router.post("/style-reload")
async def style_reload():
    """重新加载风格数据"""
    reload_style()
    return {"status": "ok", "message": "风格数据已重新加载 🔄"}
