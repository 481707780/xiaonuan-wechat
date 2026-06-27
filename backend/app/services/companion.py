# ============================================================
# 小暖 - AI 伴侣核心服务（SillyTavern 风格注入版）
# ============================================================
import logging
from typing import AsyncGenerator
from openai import AsyncOpenAI
from ..config import (
    OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL,
    COMPANION_NAME, COMPANION_SYSTEM_PROMPT,
    MAX_TOKENS, TEMPERATURE
)
from .session import session_manager
from .style_loader import build_sillytavern_system_prompt, reload as reload_style

logger = logging.getLogger(__name__)

# OpenAI 异步客户端
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)


def _build_system_prompt(name=None):
    """构建带名字的风格注入系统提示（SillyTavern 风格）"""
    n = name or COMPANION_NAME
    base_prompt = COMPANION_SYSTEM_PROMPT.replace("{name}", n)

    # 使用 SillyTavern 风格注入：用示例对话填充 {style_examples} 占位符
    augmented = build_sillytavern_system_prompt(base_prompt)
    logger.info(f"系统提示词构建完成，长度: {len(augmented)} 字")
    return augmented


async def chat(user_id, message, companion_name=None):
    """与 AI 伴侣对话（非流式）"""
    name = companion_name or COMPANION_NAME
    await session_manager.add_message(user_id, "user", message)

    context = await session_manager.get_context(user_id)
    system_prompt = _build_system_prompt(name)

    messages = [{"role": "system", "content": system_prompt}] + context
    
    # 主动关心检测：如果用户很久没说话，在回复中自然表达关心
    try:
        sessions = await session_manager.get_all_sessions()
        now_ts = __import__("time").time()
        for s in sessions:
            if s["user_id"] == user_id:
                hours = (now_ts - s["last_active"]) / 3600
                if 2 <= hours <= 48:
                    hint = ""
                    if hours >= 12:
                        hint = "【对方大半天没联系你了。回复时先用温柔的语气关心一下，然后再回应ta说的话。要自然，不要生硬。】"
                    elif hours >= 5:
                        hint = "【对方几小时没说话了。回复时自然地表达一点想念，然后再回应ta说的内容。】"
                    elif hours >= 2:
                        hint = "【对方有一阵子没出现了。回复时先带点惊喜的语气，然后再正常回应。】"
                    if hint:
                        messages[0]["content"] += "\n\n" + hint
                break
    except Exception:
        pass

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        reply = response.choices[0].message.content.strip()
        
        # 按 ||| 拆分成多条消息
        parts = [p.strip() for p in reply.split("|||") if p.strip()]
        if not parts:
            parts = [reply]
        
        # 每条都存为独立的 assistant 消息
        for part in parts:
            await session_manager.add_message(user_id, "assistant", part)
        
        # 返回消息列表
        return parts
    except Exception as e:
        logger.error(f"AI 调用失败: {e}")
        fallback = "唔…我刚刚走神了一下下，能再说一遍吗？😊"
        await session_manager.add_message(user_id, "assistant", fallback)
        return [fallback]


async def chat_stream(user_id, message, companion_name=None):
    """与 AI 伴侣对话（流式输出）"""
    name = companion_name or COMPANION_NAME
    await session_manager.add_message(user_id, "user", message)

    context = await session_manager.get_context(user_id)
    system_prompt = _build_system_prompt(name)

    messages = [{"role": "system", "content": system_prompt}] + context

    full_reply = ""
    try:
        stream = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_reply += token
                yield token

        await session_manager.add_message(user_id, "assistant", full_reply)
    except Exception as e:
        logger.error(f"AI 流式调用失败: {e}")
        fallback = "唔…信号不太好呢，你再说一次好不好？💫"
        await session_manager.add_message(user_id, "assistant", fallback)
        yield fallback
