
"""入口：组装 agent 并运行。

- 配了 DEEPSEEK_API_KEY → 走 LLM 驱动的 ReAct agent。
- 没 key / 没装 openai → 自动降级为确定性问候，demo 仍能跑。

"""

from __future__ import annotations
from Agent.agent import MorningCoachAgent
from Agent.perception import get_yesterday_health_data   # noqa: F401  (作业要求的入口函数，对外保留)
from Agent.reasoning import assess_state
from Agent.memory import load_profile
from Agent.prompt import fallback_greeting

from Agent.llm_client import DeepSeekClient

def generate_greeting(health_data: dict, profile: dict | None = None) -> str:
    """
    兼容原始作业签名：给健康数据直接产出问候（内部补齐状态判定）。
    """
    state = assess_state(health_data)
    return fallback_greeting(health_data, state, profile or load_profile())

def _build_agent() -> MorningCoachAgent:
    """
    构造 LLM 驱动的 agent；缺 key 或缺 openai 依赖会在此抛错。
    """
    return MorningCoachAgent(llm=DeepSeekClient())

def main() -> None:
    try:
        agent = _build_agent()
    except Exception as e:
        print(f"[提示] 未启用 LLM（{e}），改用确定性兜底问候。n")
        data = get_yesterday_health_data()
        print(generate_greeting(data))
        return
    print(agent.run())
if __name__ == "__main__":
    main()