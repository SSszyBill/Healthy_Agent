
"""
决策层（思考）：纯函数，把健康数据判成状态档位。
不依赖文件/IO，便于单测。配置驱动——指标由 Agent.config.METRICS 决定。
"""

from config import (
    METRICS,
    THRESHOLD_GOOD,
    THRESHOLD_OK,
    ROUND_NDIGITS,
    STATE_GOOD,
    STATE_OK,
    STATE_POOR,
)

def normalize(value, metric_cfg):
    """
    min-max 缩放到 [0,1]，再统一成 goodness（越高越好）。
    """
    lo, hi = metric_cfg["range"]
    norm = (value - lo) / (hi - lo)
    norm = max(0.0, min(1.0, norm))            # 越界裁剪
    if metric_cfg["direction"] == "higher_worse":
        norm = 1.0 - norm
    return round(norm, ROUND_NDIGITS)

def compute_score(health_data, metrics=METRICS):
    """
    各指标 goodness 加权求和，返回 [0,1] 综合分。
    """
    total = sum(
        cfg["weight"] * normalize(health_data[name], cfg)
        for name, cfg in metrics.items()
    )
    return round(total, ROUND_NDIGITS)
def hits_floor(health_data, metrics=METRICS):
    """
    保守 floor：任一维度 goodness ≤ floor_good 即「很差」。
    """
    return any(
        normalize(health_data[name], cfg) <= cfg["floor_good"]
        for name, cfg in metrics.items()
    )
def bucket(score):
    """
    综合分 → 三档。
    """
    if score >= THRESHOLD_GOOD:
        return STATE_GOOD
    if score >= THRESHOLD_OK:
        return STATE_OK
    return STATE_POOR

def assess_state(health_data, metrics=METRICS):
    """
    决策层入口：先切档，再用 floor 否决（只下压、不上抬）。
    """
    if hits_floor(health_data, metrics):
        return STATE_POOR
    return bucket(compute_score(health_data, metrics))