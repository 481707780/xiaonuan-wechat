# ============================================================
# 小暖 - 微信 API 客户端（客服消息推送）
# ============================================================
import logging
import httpx
from ..config import WECHAT_APP_ID, WECHAT_APP_SECRET

logger = logging.getLogger(__name__)

TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
SEND_URL = "https://api.weixin.qq.com/cgi-bin/message/custom/send"


class WeChatClient:
    """微信客服消息客户端"""
    def __init__(self):
        self._access_token = None
        self._token_expires = 0

    async def _get_access_token(self):
        import time
        if self._access_token and time.time() < self._token_expires - 300:
            return self._access_token
        if not WECHAT_APP_ID or not WECHAT_APP_SECRET:
            return None
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(TOKEN_URL, params={"grant_type":"client_credential","appid":WECHAT_APP_ID,"secret":WECHAT_APP_SECRET})
                d = r.json()
                if "access_token" in d:
                    self._access_token = d["access_token"]
                    self._token_expires = time.time() + d["expires_in"]
                    return self._access_token
                logger.error(f"Token err: {d}")
                return None
        except Exception as e:
            logger.error(f"Get token fail: {e}")
            return None

    async def send_text(self, open_id, text):
        """发送客服文本消息"""
        token = await self._get_access_token()
        if not token:
            return False
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(f"{SEND_URL}?access_token={token}", json={"touser":open_id,"msgtype":"text","text":{"content":text}})
                d = r.json()
                if d.get("errcode") == 0:
                    logger.info(f"Sent to {open_id}: {text[:30]}")
                    return True
                logger.error(f"Send err: {d}")
                return False
        except Exception as e:
            logger.error(f"Send fail: {e}")
            return False


wechat_client = WeChatClient()