"""
工具层：统一 Tool 接口 + 把四层能力包成 LLM 可调用的工具 + 注册表。

设计要点：
- 工具之间通过 ToolContext（黑板）共享数据，LLM 只决定调用顺序，
  不负责搬运数值——避免 LLM 改错睡眠/压力等关键数字。
- 加新能力 = 新写一个 Tool 并加进注册表，循环逻辑零改动（扩展接口）。
- 注册表统一捕获工具异常，把错误当作观察回喂给 LLM 自纠（健壮性）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from pathlib import Path
from Agent.perception import get_yesterday_health_data
from Agent.reasoning import assess_state
from Agent.memory import load_profile

#一次 run 内工具共享的黑板
@dataclass
class ToolContext:
  """
  LLM 决定"调用顺序"，真实数据在这里直接传递，不经 LLM 改写。
  """
  health_data: dict[str, Any] | None = None
  profile: dict[str, Any] | None = None
  state: str | None = None

# 统一 Tool 接口
class Tool:
  name: str = ""
  description: str = ""
  """
  给 LLM 看的参数 JSON schema；本项目的工具都从黑板取数，故多为空。
  """
  parameters: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
  def run(self, ctx: ToolContext, kwargs: Any) -> str:
    raise NotImplementedError
  
  def schema(self) -> dict[str, Any]:
    """
    转成 OpenAI/DeepSeek 兼容的 tool schema。
    """
    return {
    "type": "function",
    "function": {
    "name": self.name,
    "description": self.description,
    "parameters": self.parameters,
    },
    }

# 把三层能力包成工具 
class GetHealthDataTool(Tool):
  name = "get_yesterday_health_data"
  description = "读取昨天的健康数据（睡眠、压力等）。无需参数。"
  def __init__(self, path: str = "sample_data.csv") -> None:
    self.path = path

  def run(self, ctx: ToolContext, kwargs: Any) -> str:
    data = get_yesterday_health_data(Path(self.path))
    ctx.health_data = data                      # 写黑板
    return json.dumps(data, ensure_ascii=False)
  
  
class AssessStateTool(Tool):
  name = "assess_state"
  description = (
    "根据已读取的健康数据，用确定性规则判定当日基础状态"
    "（良好/一般/欠佳）。请先调用 get_yesterday_health_data。"
  )
  def run(self, ctx: ToolContext, kwargs: Any) -> str:
    if ctx.health_data is None:
      return "错误：请先调用 get_yesterday_health_data 读取数据。"
    state = assess_state(ctx.health_data)        # 确定性决策层
    ctx.state = state                            # 写黑板
    return json.dumps({"state": state}, ensure_ascii=False)

class GetUserProfileTool(Tool):
  name = "get_user_profile"
  description = "读取用户画像（姓名 name、沟通风格 style: gentle/direct）。无需参数。"

  def __init__(self, path: str = "user_profile.json") -> None:
    self.path = path  

  def run(self, ctx: ToolContext, kwargs: Any) -> str:
    profile = load_profile(Path(self.path))
    ctx.profile = profile                        # 写黑板
    return json.dumps(profile, ensure_ascii=False)    

# 工具注册表（扩展接口 + 统一调度/容错）
class ToolRegistry:
  def __init__(self, tools: list[Tool]) -> None:
    self._tools = {t.name: t for t in tools}          
  
  def schemas(self) -> list[dict[str, Any]]:
    """喂给 LLM 的工具清单。"""
    return [t.schema() for t in self._tools.values()]
  
  def run(self, name: str, ctx: ToolContext, arguments: dict[str, Any] | None) -> str:  
    tool = self._tools.get(name)
    if tool is None:
      return f"错误：未知工具 {name}"
    try:
      return tool.run(ctx, (arguments or {})) 
    except Exception as e:                       # 不让单个工具崩掉整个循环
      return f"工具 {name} 执行出错：{e}"       # 错误回喂，LLM 可重试/换路  
  
def default_tools() -> list[Tool]:
  """
  默认工具集；加新能力在这里追加即可。
  """
  return [GetHealthDataTool(), AssessStateTool(), GetUserProfileTool()]