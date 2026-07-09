# 晨间健康助手 Agent 🌅

一个每天清晨主动与你对话的 AI 健康陪伴 Agent：读取昨日健康数据 → 判断当日「基础状态」→ 用合适的语气送上一句贴合数据的晨间问候。

它是一个 **LLM 驱动的 ReAct Agent**，围绕一个**确定性内核**构建。一句话架构理念：

> **确定的逻辑钉进 workflow（纯函数、可复现、可单测）；不确定的判断才交给 LLM（工具编排 + 自然语言措辞）。**

凡是需要正确性保证的部分（状态判档、数值）一律确定性化、单测锁死；凡是需要灵活性的部分（调用顺序、共情表达）才放给 LLM——而且 LLM 只能「使用」确定性结果，不能篡改它。

---

## ✨ 核心特性

- **确定性内核 + 生成式外壳**：状态判定是确定性纯函数（可单测、可解释）；LLM 只负责动态编排与措辞，无权改写判档结果与原始数值。
- **绝对分值打分**：衡量「你今天的绝对状态」，而非「比昨天好没好」，避免把「好转中的差状态」误判为佳。
- **配置驱动的指标体系**：加一个健康指标 = 改一行 config + 加一列数据，决策逻辑零改动。
- **ReAct 架构**：能力即工具，LLM 自主决定调用顺序；支持离线 Mock 测试、零成本回归。
- **永远有输出**：LLM/网络失败时自动降级到确定性模板问候。

---

## 🏗️ 架构总览

### Hermes 四能力 → 实现映射

| Hermes 能力     | 对应实现                                    | 未来形态                   |
| --------------- | ------------------------------------------- | -------------------------- |
| 感知 Perception | `perception.get_yesterday_health_data()`  | CSV → 真实健康 API        |
| 记忆 Memory     | `memory.load_profile()`                   | 沟通风格偏好（+ 可选趋势） |
| 思考 Reasoning  | `reasoning.assess_state()`（打分 + 切档） | 确定性纯函数               |
| 行动 Action     | `prompt` + LLM 生成 / `print()`         | 控制台 → 推送/IM          |

### 确定 vs 不确定的边界


确定性能力层（确定的逻辑，写进 workflow）
perception 读数据 · reasoning 判档 · memory 读偏好 · config 阈值
↑ 每个能力被包装成一个 Tool
LLM 编排层（不确定的判断，交给 LLM）
agent ReAct 循环：决定调哪个工具/什么顺序/何时收尾 + 生成最终措辞

- **决策层是确定性的，只被包成工具**：LLM 调用 `assess_state` 工具拿权威状态，**不自己判档**。
- **数据走「黑板」(ToolContext)**：工具产出的数值不经 LLM 改写，杜绝模型「编数字」。
- **ReAct 循环**：LLM 拿到目标 + 工具表，自主决定调用顺序、观察结果、生成问候；带 `max_steps` 上限、工具报错回喂、LLM/网络失败双层兜底。

---

## 📐 状态评估算法

### 1. 归一化（min-max 缩放到 0–1）

两个指标方向相反，各自缩放后对齐为「越高越好」：


sleep_norm  = sleep  / 100      # 睡眠越高越好
stress_norm = stress / 100      # 压力越高越差
score = w_sleep  sleep_norm + w_stress  (1 - stress_norm)

默认权重 `w_sleep = w_stress = 0.5`（写入 `config.py`，可调）。

### 2. 切档阈值（偏向「多关心」，欠佳线抬高）

| score 区间              | 状态 |
| ----------------------- | ---- |
| `score >= 0.6`        | 良好 |
| `0.45 <= score < 0.6` | 一般 |
| `score < 0.45`        | 欠佳 |

### 3. Floor 规则（稳健性补丁，否决式）

平均会稀释单维极端值，故追加：**任一维度极端糟糕时直接降为「欠佳」，不论平均分**。

- 触发条件：`stress_norm >= 0.85`（压力 >= 85）**或** `sleep_norm <= 0.25`（睡眠 <= 25）
- **floor 先于切档**，且只下压不上抬；score / goodness round 到 6 位，避免浮点误差导致边界误判。

### 状态速查矩阵（仅作可解释层，代码不依赖它判断）

| 睡眠 \ 压力            | 低压力       | 中压力       | 高压力(>=85) |
| ---------------------- | ------------ | ------------ | ------------ |
| **高睡眠**       | 良好         | 良好 / 一般  | 欠佳 (floor) |
| **中睡眠**       | 良好 / 一般  | 一般         | 欠佳 (floor) |
| **低睡眠(<=25)** | 欠佳 (floor) | 欠佳 (floor) | 欠佳 (floor) |

> 设计说明：参考 Garmin Body Battery / Whoop Recovery / Oura Readiness 的共同套路——多信号 → 加权合成连续分数 → 最后一步才离散化。矩阵只用来「讲清楚」，真正判断走打分逻辑。

---

## 📁 目录结构


```
ZoneWell/
├── morning_coach.py        # 入口：组装 llm + tools，run()
├── config.py               # 指标表 METRICS、切档/floor 阈值、状态常量
├── sample_data.csv         # 示例健康数据
├── user_profile.json       # 示例用户画像（沟通风格偏好）
├── requirements.txt        # 依赖列表
├── README.md
├── tests/
│   ├── test_decesions.py   # 决策层单测（12 个：三档边界 + floor + 归一化）
│   └── test_agent.py       # ReAct 循环单测（4 个，MockLLMClient 离线）
└── Agent/
      ├── init.py
      ├── agent.py            # MorningCoachAgent —— ReAct 循环
      ├── llm_client.py       # LLMClient 接口 + DeepSeekClient + MockLLMClient
      ├── tools.py            # Tool 接口 + 各工具 + ToolRegistry + default_tools()
      ├── prompt.py           # SYSTEM_PROMPT + 风格范例 + fallback_greeting()
      ├── perception.py       # 感知：读 CSV 最新一天
      ├── reasoning.py        # 决策：打分 + floor + 切档（确定性纯函数）
      └── memory.py           # 记忆：读取沟通风格偏好
```

---

## 🚀 快速开始

### 1. 安装


```
conda create -n morning-coach python=3.11 -y
conda activate morning-coach
pip install -r requirements.txt
```


> 依赖见 `requirements.txt`：`openai`（DeepSeek 走 OpenAI 兼容接口）、`python-dotenv`（加载 `.env`）、`pytest`（测试）。

### 2. 配置 API Key（可选，不配会走确定性兜底）

通过环境变量提供 DeepSeek key（OpenAI 兼容）：

```
export DEEPSEEK_API_KEY="你的key"
```

或写入项目根目录的 `.env`（**确保 `.env` 已在 `.gitignore` 中，切勿提交**）：

```
DEEPSEEK_API_KEY=你的key
```


### 3. 运行

```
python morning_coach.py
```

输出示例：
Tom，早上好 🌅 昨晚睡眠拿了 82 分，压力也只有 30，状态很平稳呢。
今天要不要趁这份好状态，泡杯茶或在窗边发会儿呆，给自己一个温柔的早晨？

---

## 🔀 两种运行模式

| 模式                 | 触发条件                   | 行为                                                              |
| -------------------- | -------------------------- | ----------------------------------------------------------------- |
| **LLM 模式**   | 设置了`DEEPSEEK_API_KEY` | DeepSeek 驱动 ReAct 循环：调工具取数据/判状态 → 生成自然语言问候 |
| **确定性兜底** | 无 key / LLM 调用失败      | 跳过 LLM，用确定性模板拼出问候，保证永远有输出                    |

> 决策层在两种模式下完全一致——LLM 模式下也是调 `assess_state` 工具拿状态，不自行判档。

---

## 🗂️ 数据与配置 Schema

### `sample_data.csv`（按列名解析，新增列不破坏解析）

```
date,sleep_score,stress_level
2026-06-28,82,30
```

### `user_profile.json`

```
{
"name": "Tom",
"style": "gentle",
"preferences": {},
"history": []
}
```

- `style`：`"gentle" | "direct"`，行动层选语气用。
- `preferences`：预留开放对象，未来加偏好直接加键，旧代码不受影响。
- `history`：预留给可选的趋势措辞，当前可为空。

---

## 🧪 测试

全部为离线、可重复、零成本的回归测试：

```
python -m pytest tests/ -v
```

覆盖范围：

- **决策层（12 测）**：三档边界（0.6 / 0.45）、floor 优先级与临界点（>= / <=）、归一化方向与裁剪。
- **ReAct 循环（4 测，MockLLMClient）**：
  - 正常多步路径（取数据 → 判状态 → 出问候）+ 工具结果回喂
  - `max_steps` 防死循环
  - 未知/报错工具的错误回喂
  - LLM 异常 → 降级确定性问候

---

## 🧩 扩展指南

### 加一个健康指标（如 HRV）

1. `config.py` 的 `METRICS` 加一项：

   "hrv": {"range": [0, 100], "weight": 0.3, "direction": "higher_better"}
2. `sample_data.csv` 加一列 `hrv`。
3. 完成——归一化 / 切档 / floor 逻辑**零改动**（决策层遍历 config，不硬编码指标）。

### 加一个新工具

1. 在 `tools.py` 继承 `Tool` 实现新工具（`name` / `description` / `parameters` / `run`）。
2. 在 `default_tools()` 里注册。
3. 完成——ReAct 循环逻辑不变，LLM 会自动看到并按需调用。

---

## 🧭 设计哲学

- **确定的钉死，不确定的放开**：要正确性保证的逻辑做成纯函数写进 workflow；要灵活性的判断交给 LLM。
- **提示而非命令（nudge, not a command）**：用「要不要…」式的陪伴语气，而非指令。
- **看着数据说话**：在固定句式里注入感知层的真实数值，让对话不像「念稿」。

