# ============================================================
# 小暖 - AI 伴侣核心服务（风格数据注入版）
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
from .style_loader import build_style_augmented_system_prompt, reload as reload_style

logger = logging.getLogger(__name__)

# OpenAI 异步客户端
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)


def _build_system_prompt(name: str = None) -> str:
    """构建带名字的风格注入系统提示"""
    n = name or COMPANION_NAME
    base_prompt = COMPANION_SYSTEM_PROMPT.replace("{name}", n)
    # 注入风格数据：将聊天风格分析注入到系统提示词中
    augmented = build_style_augmented_system_prompt(base_prompt)
    return augmented


async def chat(
    user_id: str,
    message: str,
    companion_name: str = None
) -> str:
    """与 AI 伴侣对话（非流式）"""
    name = companion_name or COMPANION_NAME
    await session_manager.add_message(user_id, "user", message)

    context = await session_manager.get_context(user_id)
    system_prompt = _build_system_prompt(name)

    messages = [{"role": "system", "content": system_prompt}] + context

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        reply = response.choices[0].message.content.strip()
        await session_manager.add_message(user_id, "assistant", reply)
        return reply
    except Exception as e:
        logger.error(f"AI 调用失败: {e}")
        fallback = "唔…我刚刚走神了一下下，能再说一遍吗？😊"
        await session_manager.add_message(user_id, "assistant", fallback)
        return fallback


async def chat_stream(
    user_id: str,
    message: str,
    companion_name: str = None
) -> AsyncGenerator[str, None]:
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
