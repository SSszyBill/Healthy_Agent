"""集中配置：指标表、切档阈值、floor 阈值、状态常量。
改参数只动这里，决策逻辑（morning_coach.py）不需要改。"""

from pathlib import Path

# —— 指标表：决策层遍历它，不硬编码具体指标名 
METRICS = {
    "sleep_score": {
        "range": (0, 100),            # min-max 归一化区间
        "weight": 0.5,                # 加权权重
        "direction": "higher_better",
        "floor_good": 0.25,           # goodness ≤ 0.25（≈ sleep ≤ 25）→ 视为「很差」
    },
    "stress_level": {
        "range": (0, 100),
        "weight": 0.5,
        "direction": "higher_worse",
        "floor_good": 0.15,           # goodness ≤ 0.15（≈ stress ≥ 85）→ 视为「很差」
    },
}

# —— 切档阈值（偏向「多关心」，欠佳线抬高）——
THRESHOLD_GOOD = 0.60   # score ≥ 0.60 → 良好
THRESHOLD_OK = 0.45     # 0.45 ≤ score < 0.60 → 一般；< 0.45 → 欠佳

# 计算保留小数位：稳住 0.60 / 0.45 / floor 等边界，避免浮点误差误判
ROUND_NDIGITS = 6

# —— 状态常量 ——
STATE_GOOD = "良好"
STATE_OK = "一般"
STATE_POOR = "欠佳"

ROOT_DIR = Path(__file__).resolve().parent
DATA_FILE = ROOT_DIR / "sample_data.csv"
PROFILE_FILE = ROOT_DIR / "user_profile.json"
