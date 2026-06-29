
import pytest
from Agent.llm_client import LLMResponse, ToolCall, MockLLMClient
from Agent.tools import default_tools
from Agent.agent import MorningCoachAgent

def test_happy_path_data_then_state_then_greeting():
    """
    脚本化 ReAct：取数据 → 判状态 → 出问候。
    """
    script = [
    LLMResponse(tool_calls=[ToolCall(name="get_yesterday_health_data", arguments={})]),
    LLMResponse(tool_calls=[ToolCall(name="assess_state", arguments={})]),
    LLMResponse(content="Tom，早上好 🌅\n昨晚睡眠 82 分…"),
    ]
    llm = MockLLMClient(script)
    agent = MorningCoachAgent(llm=llm, tools=default_tools())
    result = agent.run()
    assert result == "Tom，早上好 🌅\n昨晚睡眠 82 分…"   # 拿到脚本最终问候
    assert len(llm.calls) == 3                            # 循环正好 3 轮
    # 第 2 轮 LLM 看到的 messages 里应已有 tool 结果（数据真的回喂了）
    second_round_messages = llm.calls[1][0]
    assert any(m.get("role") == "tool" for m in second_round_messages)

def test_max_steps_stops_and_falls_back():
    """
    LLM 只调工具不收尾 → 不死循环，max_steps 兜住后走兜底。
    """
    only_tools = [
    LLMResponse(tool_calls=[ToolCall(name="get_yesterday_health_data", arguments={})])
    for i in range(50)
    ]
    llm = MockLLMClient(only_tools)
    agent = MorningCoachAgent(llm=llm, tools=default_tools(), max_steps=6)
    result = agent.run()
    assert len(llm.calls) == 6        # 严格停在 max_steps
    assert result                     # 返回兜底问候，而非卡死/空字符串

def test_unknown_tool_error_is_fed_back():
    """
    调不存在的工具 → 错误回喂，下一轮 messages 能看到错误。
    """
    script = [
    LLMResponse(tool_calls=[ToolCall(name="no_such_tool", arguments={})]),
    LLMResponse(content="收尾问候"),
    ]
    llm = MockLLMClient(script)
    agent = MorningCoachAgent(llm=llm, tools=default_tools())
    result = agent.run()
    assert result == "收尾问候"
    second_round_messages = llm.calls[1][0]
    assert any("未知工具" in str(m) for m in second_round_messages)

def test_llm_exception_falls_back_to_deterministic():
    """
    LLM 抛异常 → 降级确定性问候，保证永远有输出。
    """
    class BoomLLM:
        def chat(self, messages, tools=None):
            raise RuntimeError("network down")
    agent = MorningCoachAgent(llm=BoomLLM(), tools=default_tools())
    result = agent.run()
    assert result          # 不抛异常，返回兜底