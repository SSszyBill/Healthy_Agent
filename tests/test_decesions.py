"""
决策层测试（先于实现写好）——把锁定的规格翻译成断言。
运行：python -m pytest -q
"""

import pytest

from Agent.reasoning import assess_state, compute_score, normalize
from config import METRICS, STATE_GOOD, STATE_OK, STATE_POOR

def hd(sleep, stress):
    return {"sleep_score": sleep, "stress_level": stress}

@pytest.mark.parametrize("sleep, stress, expected", [
# 三档主路径
(90, 20, STATE_GOOD),    # 双优
(50, 50, STATE_OK),      # 双平 → 居中
(30, 70, STATE_POOR),    # 双差

# 切档边界（验证 ≥ 归属）
(70, 50, STATE_GOOD),    # score=0.60，恰好良好线
(40, 50, STATE_OK),      # score=0.45，恰好一般线（非欠佳）
(38, 50, STATE_POOR),    # score=0.44，刚跌破

# floor 否决：平均稀释了单维极端值
(100, 85, STATE_POOR),   # 均分0.575本是一般 → floor 压成欠佳
(80, 85, STATE_POOR),    # 压力85 恰好触发 floor

# floor 否决「良好」：讨论中发现的隐藏 case
(25, 0, STATE_POOR),     # 均分0.625本是良好 → floor 压成欠佳
])

def test_assess_state(sleep, stress, expected):
    assert assess_state(hd(sleep, stress)) == expected

def test_floor_only_lowers_never_raises():
    """
    floor 是否决式安全网：只下压、绝不上抬
    """
    assert assess_state(hd(100, 85)) == STATE_POOR   # 一般 → 欠佳
    assert assess_state(hd(25, 0)) == STATE_POOR     # 良好 → 欠佳

def test_compute_score_values():
    assert compute_score(hd(100, 0)) == 1.0
    assert compute_score(hd(0, 100)) == 0.0
    assert compute_score(hd(50, 50)) == 0.5

def test_normalize_direction_and_clip():
    sleep_cfg = METRICS["sleep_score"]
    stress_cfg = METRICS["stress_level"]
    assert normalize(100, sleep_cfg) == 1.0    # 睡眠越高越好
    assert normalize(0, sleep_cfg) == 0.0
    assert normalize(0, stress_cfg) == 1.0     # 压力越低越好（方向取反）
    assert normalize(100, stress_cfg) == 0.0
    assert normalize(120, sleep_cfg) == 1.0    # 越界裁剪到 1
    assert normalize(-10, sleep_cfg) == 0.0    # 越界裁剪到 0