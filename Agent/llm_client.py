"""LLM 客户端层。

设计：先定义抽象接口 LLMClient，再给两个实现：
- DeepSeekClient：真实调用（DeepSeek 与 OpenAI 兼容，复用 openai SDK）。
- MockLLMClient ：测试用，按预设脚本返回，不联网、零成本。

agent 只依赖 LLMClient 这个抽象，便于依赖注入与替换。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Protocol, cast
from openai import OpenAI
from openai.types.chat import (ChatCompletionMessageParam,
ChatCompletionToolParam,
)
import uuid

@dataclass(kw_only=True)
class ToolCall:
    """
    LLM 请求执行的一次工具调用。
    """
    id: str = field(default_factory=lambda: f"call_{uuid.uuid4().hex[:8]}")
    name: str
    arguments: dict[str, Any]
    
@dataclass
class LLMResponse:
    """
    一次 chat 的结果：要么给最终文本，要么请求调用工具。
    """
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    @property
    def wants_tool(self) -> bool:
        return bool(self.tool_calls)


class LLMClient(Protocol):
    """
    聊天接口：传入消息历史 + 可用工具 schema，返回 LLMResponse。
    """
    def chat(self,messages: list[dict[str, Any]],tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse: ...
    
# 真实实现：DeepSeek（OpenAI 兼容）
class DeepSeekClient:
    """
    用 openai SDK 连 DeepSeek。需要环境变量 DEEPSEEK_API_KEY。
    """
    def __init__(self, model: str = "deepseek-chat", api_key: str | None = None, base_url: str = "https://api.deepseek.com",
    ) -> None:
        key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError(
            "缺少 DeepSeek API key：请设置环境变量 DEEPSEEK_API_KEY"
            )
        self._client = OpenAI(api_key=key, base_url=base_url)
        self.model = model
    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None,) -> LLMResponse:
        params: dict[str, Any] = {
        "model": self.model,
        "messages": messages,
    }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        resp = self._client.chat.completions.create(**params)

        msg = resp.choices[0].message
        calls = [
            ToolCall(
                id=c.id,
                name=c.function.name,
                arguments=json.loads(c.function.arguments or "{}"),
            )
            for c in (msg.tool_calls or [])
        ]
        return LLMResponse(content=msg.content, tool_calls=calls)

# 测试实现：按脚本回放，不联网
class MockLLMClient:
    """
    测试桩：依次返回预设的 LLMResponse 列表。
    用法：MockLLMClient([
    LLMResponse(tool_calls=[ToolCall("1", "get_yesterday_health_data", {})]),
    LLMResponse(content="Tom，早上好 🌅 ..."),
    ])
    self.calls 记录每次 (messages, tools)，便于断言 LLM 看到了什么。
    """
    
    def __init__(self, script: list[LLMResponse]) -> None:
        self._script = list(script)
        self.calls: list[tuple[list[dict[str, Any]], list[dict[str, Any]] | None]] = []
        
    def chat(self,messages: list[dict[str, Any]],tools: list[dict[str, Any]] | None = None,
        ) -> LLMResponse:
        self.calls.append((messages, tools))
        if not self._script:
            return LLMResponse(content="（mock 脚本已空）")
        return self._script.pop(0)