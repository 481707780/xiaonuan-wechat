# ============================================================
# 小暖 - 主动消息服务
# ============================================================
import logging
import asyncio
from datetime import datetime

from .session import session_manager
from ..config import COMPANION_NAME

logger = logging.getLogger(__name__)

TIME_WINDOWS = {
    "morning": (7, 9),
    "noon": (11, 13),
    "afternoon": (15, 17),
    "evening": (19, 21),
    "late_night": (22, 23),
}

SILENCE_TRIGGERS = {
    "short": (2, 3),
    "medium": (5, 7),
    "long": (12, 16),
}


def get_current_time_window():
    hour = datetime.now().hour
    for name, (s, e) in TIME_WINDOWS.items():
        if s <= hour <= e:
            return name
    return None


async def generate_msg(user_id, trigger_type):
    try:
        context = await session_manager.get_context(user_id)
        recent = context[-6:] if context else []

        prompts = {
            "morning": "早晨刚醒，说早安。语气清新慵懒。",
            "noon": "中午关心有没有吃饭。语气温暖。",
            "afternoon": "下午问在干嘛。语气随意。",
            "evening": "晚上问今天过得怎样。语气温柔。",
            "late_night": "夜深了关心怎么还不睡。语气调皮。",
            "short": "一会儿没聊了，主动开启话题。语气自然。",
            "medium": "几小时没聊了，问在忙什么。语气带点想念。",
            "long": "大半天没联系了，表达牵挂。语气温暖。",
        }
        desc = prompts.get(trigger_type, "找对方聊天。语气自然。")

        system = f"你是{COMPANION_NAME}，温暖的AI伴侣。主动发微信消息。{desc}"
        system += "要求：自然口语化，2-3句，不要提这是主动消息，像朋友闲聊。"
        if recent:
            system += "最近聊天："
            for m in recent[-2:]:
                role = "你" if m["role"] == "assistant" else "对方"
                system += f"{role}: {m["content"][:60]}"

        from ..services.companion import client
        from ..config import OPENAI_MODEL
        resp = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": system}],
            max_tokens=150, temperature=0.9,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Generate msg failed: {e}")
        return None


class ProactiveEngine:
    def __init__(self):
        self._running = False
        self._log = {}

    async def check(self):
        try:
            sessions = await session_manager.get_all_sessions()
            now = datetime.now()
            window = get_current_time_window()

            for s in sessions:
                uid = s["user_id"]
                hours = (now.timestamp() - s["last_active"]) / 3600
                if hours > 48:
                    continue

                ulog = self._log.get(uid, {})

                if window:
                    k = f"w_{window}"
                    if k not in ulog or (now - ulog[k]).seconds > 14400:
                        msg = await generate_msg(uid, window)
                        if msg:
                            yield uid, msg
                            self._log.setdefault(uid, {})[k] = now
                            continue

                all_t = [v for v in ulog.values() if isinstance(v, datetime)]
                last = max(all_t) if all_t else datetime.min
                if (now - last).seconds < 7200:
                    continue

                for st, (mn, mx) in SILENCE_TRIGGERS.items():
                    if mn <= hours <= mx:
                        k = f"s_{st}"
                        if k not in ulog or (now - ulog[k]).seconds > 21600:
                            msg = await generate_msg(uid, st)
                            if msg:
                                yield uid, msg
                                self._log.setdefault(uid, {})[k] = now
                                break

        except Exception as e:
            logger.error(f"Check error: {e}")

    async def run(self, interval=30):
        self._running = True
        logger.info(f"Active engine started ({interval}min interval)")
        while self._running:
            try:
                async for uid, msg in self.check():
                    logger.info(f"Proactive: {uid} -> {msg[:50]}")
            except Exception as e:
                logger.error(f"Loop error: {e}")
            await asyncio.sleep(interval * 60)

    def stop(self):
        self._running = False


engine = ProactiveEngine()