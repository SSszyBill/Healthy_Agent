
"""编排层：ReAct 循环（agent 的"大脑"）。

LLM 拿到 system prompt + 工具表，自己决定调哪个工具、看观察结果、
最后生成问候语。本类只依赖抽象的 LLMClient，工具/提示词都可注入（依赖注入）。
"""

from __future__ import annotations

import json
from typing import Any

from Agent.llm_client import LLMClient, LLMResponse, ToolCall
from Agent.tools import ToolContext, ToolRegistry, Tool, default_tools
from Agent.prompt import SYSTEM_PROMPT, STYLE_EXAMPLES, fallback_greeting

# 兜底路径直接用确定性能力，不经 LLM
from Agent.perception import get_yesterday_health_data
from Agent.reasoning import assess_state
from Agent.memory import load_profile

def _assistant_tool_msg(resp: LLMResponse) -> dict[str, Any]:
    """
    LLM 请求调用工具时，要把这条 assistant 消息回插进对话历史。
    """
    return {
    "role": "assistant",
    "content": resp.content or "",
    "tool_calls": [{"id": tc.id,
                    "type": "function",
                    "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments, ensure_ascii=False),},
                    }for tc in resp.tool_calls],}
def _tool_result_msg(tc: ToolCall, result: str) -> dict[str, Any]:
    """
    工具执行结果作为一条 tool 消息回喂给 LLM。
    """
    return {"role": "tool", "tool_call_id": tc.id, "content": result}



class MorningCoachAgent:
    def __init__(self, llm: LLMClient, tools: list[Tool] | None = None, system_prompt: str = SYSTEM_PROMPT, style_examples: str = STYLE_EXAMPLES, max_steps: int = 6,) -> None:
        self.llm = llm
        self.registry = ToolRegistry(tools or default_tools())
        self.system_prompt = system_prompt
        self.style_examples = style_examples
        self.max_steps = max_steps          # 循环上限，防止 LLM 绕死
    def run(self, goal: str = "请生成今天的晨间问候语。") -> str:
        ctx = ToolContext()                 # 一次 run 的共享黑板
        messages: list[dict[str, Any]] = [
        {"role": "system", "content": self.system_prompt + "\n\n" + self.style_examples},
        {"role": "user", "content": goal},
        ]
        try:
            for _ in range(self.max_steps):
                resp = self.llm.chat(messages, tools=self.registry.schemas())
                # LLM 给出最终文本（不再要工具）→ 完成
                if not resp.wants_tool:
                    if resp.content:
                        return resp.content
                    break

                #LLM 要调工具 → 执行并把观察回喂，进入下一轮
                messages.append(_assistant_tool_msg(resp))
                for tc in resp.tool_calls:
                    result = self.registry.run(tc.name, ctx, tc.arguments)
                    messages.append(_tool_result_msg(tc, result))

            #步数用尽仍没给最终答复 → 兜底
            return self._fallback(ctx)
        
        except Exception:
        # LLM/网络异常 → 降级到确定性问候，保证永远有输出
            return self._fallback(ctx)


# 兜底：不依赖 LLM 的确定性问候
    def _fallback(self, ctx: ToolContext) -> str:
        data = ctx.health_data or get_yesterday_health_data()
        state = ctx.state or assess_state(data)
        profile = ctx.profile or load_profile()
        return fallback_greeting(data, state, profile)