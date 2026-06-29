
"""
记忆层：加载用户画像（沟通风格等），供行动层决定话术。
设计原则：画像是可选的——文件缺失/损坏时回退到安全默认值，不影响主流程。
"""

import copy
import json

from config import PROFILE_FILE

DEFAULT_PROFILE = {
    "name": "",
    "style": "gentle",        # gentle（温柔）| direct（直接）
    "preferences": {},        # 预留：未来的偏好（关注的指标等）
    "history": [],            # 预留：历史趋势
}

VALID_STYLES = {"gentle", "direct"}

def load_profile(path=PROFILE_FILE):
    """读取用户画像；任何异常都安全回退到默认值。"""
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return copy.deepcopy(DEFAULT_PROFILE)
    profile = copy.deepcopy(DEFAULT_PROFILE)
    profile.update(raw)                       # 文件值覆盖默认，缺失字段自动补全
    if profile["style"] not in VALID_STYLES:  # 非法风格 → 回退
        profile["style"] = DEFAULT_PROFILE["style"]
    return profile
