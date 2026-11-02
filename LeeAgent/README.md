# LeeAgent

用 LLM + 本地判断模型 + 引擎验证,在 TavernGym 里玩酒馆战棋的记忆型智能体。
依托 AutoTavern 论文环境,但不复现其 entity transformer——目标是"推理时系统"路线。

## 架构

```
对局中,每回合一次(热路径,~1s,零 API 成本):
  代码: view → facts(精确事实) → when 预筛记忆库 → ≤16 条候选
  Nimble(本地 9B): 8 条适用性 noul + 1 条优先级 choice(带概率)
  代码: 命中记忆的 bias 注入动作评分 → 合法动作打分
  引擎: 站位用 combat_preview 前瞻裁决(免费、毫秒级)

对局结束(冷路径,每局 1 次 API):
  deepseek: 对局日志 + 现有记忆 → ≤3 条候选三元组
  验证门: 新旧记忆集各打 N 局(同种子),均值提升 ≥ 阈值才入库
```

三层分工:**Nimble 管判断、deepseek 管生成、引擎管验证**。不训练任何权重;
"训练"指阈值调优(config.json)与记忆内容的门控迭代。

## 记忆三元组

```json
{
  "id": "M08",
  "kind": "comp",
  "when":   { "tribe_min": { "BEAST": 2 }, "shop_tribe_min": { "BEAST": 1 } },
  "situation": "Shop offers a Beast and board already commits to Beasts",
  "action": "Buy the Beast over a higher-stat off-tribe minion",
  "rationale": "Tribe commitment compounds",
  "bias": { "prefer_buy_tribe": "BEAST" },
  "provenance": { "status": "seed", "ab_gain": null, "n_games": 0 }
}
```

- `when` 由代码精确匹配(零 token);`situation` 是语义残留,由 Nimble 判适用。
- `bias` 是策略可执行的机器指令(词表见 `policy.py`)。
- `provenance.status`: `seed → candidate → verified / rejected`(验证门维护)。

## 目录

```
leeagent/
  config.py       路径与可调阈值(config.json 覆盖默认值)
  facts.py        view → facts / 紧凑状态文本
  memory.py       三元组 schema、when 匹配、预筛、jsonl 存取
  nimble.py       System One 客户端(自动拆分超限问题)
  retrieval.py    热路径:预筛 → Nimble 批量判适用
  lookahead.py    combat_preview 站位前瞻
  policy.py       合法动作评分 + 记忆 bias
  agent.py        单席位驱动(其余 7 席脚本 bot)
  generate.py     冷路径:deepseek 蒸馏候选记忆
  gate.py         A/B 验证门
memories/seed.jsonl   24 条种子记忆(已过 2048-token 预算实测)
scripts/play_one.py   跑一局,打印每回合命中与成本
scripts/run_gate.py   A/B 验证门跑批
tests/                纯逻辑测试 + (可选)Nimble 联测
```

## 快速开始

```bash
# 仓库根目录的 venv
../.venv/bin/python scripts/play_one.py --seed 1
../.venv/bin/python scripts/play_one.py --seed 1 --no-nimble   # 纯代码基线(对照用)
../.venv/bin/python -m pytest ../LeeAgent/tests -q             # 或从仓库根目录跑
```

冷路径(需要 ~/.tavernbench.env 已配置 deepseek):

```bash
../.venv/bin/python scripts/play_one.py --seed 1 --distill     # 对局后蒸馏候选
../.venv/bin/python scripts/run_gate.py --b memories/candidates.jsonl --n 40
```

## 路线图

- **Phase 0(当前)**: 种子记忆 + 热路径跑通,量出零训练基线(名次/成本/延迟)。
- **Phase 1**: Nimble 判断校准(known-label 集合)与阈值扫描(`min_apply_prob` 等)。
- **Phase 2**: 冷路径迭代:蒸馏 → 门 → 入库,观察记忆库增长与对局胜率的关系。
- 评测: TavernBench 桥接(states.jsonl.gz → 局面 → LeeAgent 决策 → 答案格式)。
