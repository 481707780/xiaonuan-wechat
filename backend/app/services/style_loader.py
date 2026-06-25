# ============================================================
# 小暖 - 聊天风格数据注入服务
# 将分析好的聊天风格数据注入到 AI 系统提示词中
# ============================================================
import json
import logging
import random
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 数据文件路径
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
STYLE_PROFILE_PATH = DATA_DIR / "style_profile.json"
ALL_FEMALE_REPLIES_PATH = DATA_DIR / "all_female_replies.txt"
MY_CHAT_STYLE_PATH = DATA_DIR / "my_chat_style.txt"

# 缓存
_cached_profile = None
_cached_female_replies = []
_cached_my_style_lines = []


def _ensure_data_dir() -> bool:
    """确保数据目录存在"""
    if not DATA_DIR.exists():
        logger.warning(f"数据目录不存在: {DATA_DIR}")
        return False
    return True


def load_style_profile() -> Optional[dict]:
    """加载风格分析概要"""
    global _cached_profile
    if _cached_profile:
        return _cached_profile

    if not _ensure_data_dir():
        return None

    if not STYLE_PROFILE_PATH.exists():
        logger.warning(f"风格分析文件不存在: {STYLE_PROFILE_PATH}")
        _cached_profile = {}
        return _cached_profile

    try:
        with open(STYLE_PROFILE_PATH, "r", encoding="utf-8") as f:
            _cached_profile = json.load(f)
        logger.info(f"✅ 加载风格分析：共 {_cached_profile.get('total_messages', 0)} 条消息分析")
        return _cached_profile
    except Exception as e:
        logger.error(f"加载风格分析失败: {e}")
        _cached_profile = {}
        return _cached_profile


def load_female_replies(max_lines: int = 200) -> list:
    """加载女生真实回复示例（截取前 max_lines 行作为风格参考）"""
    global _cached_female_replies
    if _cached_female_replies:
        return _cached_female_replies[:max_lines]

    if not _ensure_data_dir():
        return []

    if not ALL_FEMALE_REPLIES_PATH.exists():
        logger.warning(f"女生回复文件不存在: {ALL_FEMALE_REPLIES_PATH}")
        _cached_female_replies = []
        return _cached_female_replies

    try:
        with open(ALL_FEMALE_REPLIES_PATH, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        _cached_female_replies = lines
        logger.info(f"✅ 加载女生回复示例：共 {len(lines)} 条")
        return lines[:max_lines]
    except Exception as e:
        logger.error(f"加载女生回复失败: {e}")
        return []


def load_my_style_lines(max_lines: int = 200) -> list:
    """加载我的聊天风格行（截取前 max_lines 行）"""
    global _cached_my_style_lines
    if _cached_my_style_lines:
        return _cached_my_style_lines[:max_lines]

    if not _ensure_data_dir():
        return []

    if not MY_CHAT_STYLE_PATH.exists():
        logger.warning(f"聊天风格文件不存在: {MY_CHAT_STYLE_PATH}")
        _cached_my_style_lines = []
        return _cached_my_style_lines

    try:
        with open(MY_CHAT_STYLE_PATH, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        _cached_my_style_lines = lines
        logger.info(f"✅ 加载个人聊天风格：共 {len(lines)} 条")
        return lines[:max_lines]
    except Exception as e:
        logger.error(f"加载聊天风格失败: {e}")
        return []


def build_style_augmented_system_prompt(base_prompt: str) -> str:
    """构建注入风格数据后的增强系统提示词"""
    profile = load_style_profile()
    female_examples = load_female_replies(200)
    my_style_lines = load_my_style_lines(100)

    # 风格注入块
    style_block_parts = []

    if profile and profile.get("profile"):
        style_block_parts.append(
            f"【你的说话风格分析】\n{profile['profile']}"
        )

    if profile and profile.get("examples"):
        # 从风格分析中挑选有代表性的例子（随机30个）
        examples = profile["examples"]
        selected = random.sample(examples, min(30, len(examples)))
        style_block_parts.append(
            "【你的说话风格例句（你学习这些句子的语气和节奏）】\n" +
            "\n".join(f"  - {ex}" for ex in selected)
        )

    if female_examples:
        # 随机挑选80条女生回复示例
        selected_female = random.sample(female_examples, min(80, len(female_examples)))
        style_block_parts.append(
            "【女生朋友的真实聊天范例（你模仿她们的语气和节奏）】\n" +
            "\n".join(f"  - {ex}" for ex in selected_female)
        )

    if my_style_lines:
        # 随机挑选50条聊天风格
        selected_style = random.sample(my_style_lines, min(50, len(my_style_lines)))
        style_block_parts.append(
            "【你的聊天风格参考（你模仿这些句子的节奏和用词）】\n" +
            "\n".join(f"  - {ex}" for ex in selected_style)
        )

    if not style_block_parts:
        # 没有数据文件时的降级提示
        style_block_parts.append(
            "【说话风格要求】\n"
            "- 说话简洁直接，像朋友聊天一样自然\n"
            "- 用短句表达态度，多用哈、啦、嘛、呗、哎等语气词\n"
            "- 有幽默感，可以哈哈哈\n"
            "- 情绪表达真实，不刻意客套"
        )

    style_section = "\n\n---\n\n".join(style_block_parts)

    # 在基础提示词末尾附加风格注入块
    augmented_prompt = f"{base_prompt}\n\n【=== 以下是你基于真实聊天数据分析出的说话风格，严格遵循 ===】\n\n{style_section}"

    return augmented_prompt


def reload():
    """强制重新加载所有数据"""
    global _cached_profile, _cached_female_replies, _cached_my_style_lines
    _cached_profile = None
    _cached_female_replies = []
    _cached_my_style_lines = []
    logger.info("🔄 风格数据缓存已清空，下次访问将重新加载")


def build_sillytavern_style_examples(max_examples=60):
    """以 SillyTavern 风格构建对话示例文本"""
    import random
    profile = load_style_profile()
    female_replies = load_female_replies(80)
    my_style = load_my_style_lines(50)

    parts = []
    if profile and profile.get("profile"):
        parts.append("【你的整体说话风格】" + chr(10) + profile["profile"])

    example_sections = []
    if profile and profile.get("examples"):
        selected = random.sample(profile["examples"], min(20, len(profile["examples"])))
        example_sections.append("=== 日常对话 ===")
        for ex in selected:
            example_sections.append("  " + ex)

    if female_replies:
        selected = random.sample(female_replies, min(25, len(female_replies)))
        example_sections.append("")
        example_sections.append("=== 和朋友聊天 ===")
        for ex in selected:
            example_sections.append("  " + ex)

    if my_style:
        selected = random.sample(my_style, min(15, len(my_style)))
        example_sections.append("")
        example_sections.append("=== 日常吐槽 ===")
        for ex in selected:
            example_sections.append("  " + ex)

    if example_sections:
        parts.append(chr(10).join(example_sections))

    return chr(10).join(parts)


def build_sillytavern_system_prompt(base_prompt):
    """构建 SillyTavern 风格的增强系统提示词"""
    examples_text = build_sillytavern_style_examples()
    if "{style_examples}" in base_prompt:
        return base_prompt.replace("{style_examples}", examples_text)
    else:
        return base_prompt + chr(10) * 2 + "【风格参考】" + chr(10) + examples_text
