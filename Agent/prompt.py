
"""提示词层：system prompt + 风格范例 + 确定性兜底模板。

- SYSTEM_PROMPT：把"先调工具、再生成"的工作流和硬约束写给 LLM。
- 风格范例：原话术升级为 few-shot，教 LLM 语气，而非让它照抄。
- fallback_greeting：LLM/网络不可用时的确定性兜底，保证永远能出结果。
"""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """你是「晨间健康助手」，每天早晨用一段简短的话陪伴用户开启一天。
你可以调用以下工具来了解情况（自行决定调用顺序）：
get_yesterday_health_data：读取昨天的睡眠、压力等数据
assess_state：根据数据判定当日基础状态（良好/一般/欠佳）。这是权威判定，请直接采用，不要自己改判
get_user_profile：读取用户姓名与沟通风格（gentle 温柔 / direct 直接）
工作流程：
先调用工具，拿到「健康数据」「基础状态」「用户画像」。
再生成最终问候语，必须满足：
称呼用户姓名；语气匹配其沟通风格（gentle 温柔体贴 / direct 简洁直接）。
至少引用一个真实数值（如昨晚睡眠分、压力值），让用户感到「你在看着我的数据说话」。
提示而非命令（nudge, not command）：可鼓励、可提问，但不发号施令、不给医疗建议。
结尾抛出一个轻量的晨间问题。
只输出问候语本身，不要输出思考过程、工具名或多余解释。
"""

STYLE_EXAMPLES = """语气参考示例（理解风格即可，不要照搬）：
[gentle / 良好] 小明，早上好 🌅 昨晚睡了 82 分，压力只有 30，状态很稳呢。今天想先做点让自己开心的小事吗？
[direct / 欠佳] 小明，早。昨晚睡眠只有 40 分、压力 72，身体在亮黄灯。今天给自己留点缓冲，第一件事想先处理什么？
"""


_FALLBACK_FEEDBACK = {
"良好": {
"gentle": "昨晚睡眠 {sleep} 分、压力 {stress}，状态很稳，真为你高兴。",
"direct": "昨晚睡眠 {sleep} 分、压力 {stress}，状态不错。",
},
"一般": {
"gentle": "昨晚睡眠 {sleep} 分、压力 {stress}，还算可以，记得多歇一歇。",
"direct": "昨晚睡眠 {sleep} 分、压力 {stress}，一般，留意节奏。",
},
"欠佳": {
"gentle": "昨晚睡眠 {sleep} 分、压力 {stress}，身体有点累了，今天慢一点也没关系。",
"direct": "昨晚睡眠 {sleep} 分、压力 {stress}，状态偏差，今天减负。",
},
}

_FALLBACK_QUESTION = {
"良好": {"gentle": "今天想先做点让自己开心的事吗？", "direct": "今天第一件想推进的事是什么？"},
"一般": {"gentle": "今天有什么想优先照顾好的吗？", "direct": "今天最该先处理的一件事是什么？"},
"欠佳": {"gentle": "今天想先给自己留点什么缓冲呢？", "direct": "今天想先砍掉哪件事来减压？"},
}
def fallback_greeting(health_data: dict[str, Any], state: str, profile: dict[str, Any] | None = None,) -> str:
    """
    LLM/网络不可用时的确定性兜底问候，保证永远能跑。
    """
    profile = profile or {}
    name = profile.get("name") or "朋友"
    style = profile.get("style", "gentle")
    
    if style not in ("gentle", "direct"):
        style = "gentle"
    
    sleep = int(health_data.get("sleep_score", 0))
    stress = int(health_data.get("stress_level", 0))
    feedback = _FALLBACK_FEEDBACK[state][style].format(sleep=sleep, stress=stress)
    question = _FALLBACK_QUESTION[state][style]
    return f"{name}，早上好 🌅\n{feedback}\n{question}"