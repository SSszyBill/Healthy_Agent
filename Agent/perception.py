"""感知层（输入）：从 CSV 读取最近一天的健康数据。
- 按列名读取（DictReader），不依赖列顺序；新增列不破坏解析。
- 只把 config.METRICS 声明的指标列转成数值，其余列原样保留。"""

import csv

from config import METRICS, DATA_FILE

def get_yesterday_health_data(path=DATA_FILE):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    
    if not rows:
        raise ValueError(f"{path} 里没有数据")
    latest = max(rows, key=lambda r: r["date"])   # 日期最大的一行 = 最近一天
    data = {"date": latest["date"]}
    
    for name in METRICS:                            # 配置驱动：读哪些指标由 config 决定
        if name not in latest:
            raise KeyError(f"CSV 缺少列：{name}")
        data[name] = float(latest[name])
    return data
