# LeeAgent

用 LLM + 本地判断模型 + 引擎验证,在 TavernGym 里玩酒馆战棋的记忆型智能体。
依托 AutoTavern 论文环境,但不复现其 entity transformer——目标是"推理时系统"路线。

## 架构

```
对局开始: 英雄二选一 ← 经验英雄表(115 英雄 × 64 局 bot 实测 = 7360 局)
对局中,每回合一次(热路径,~1s,零 API 成本):
  代码: view → facts(精确事实)→ 成型方向决策(turn 4–6 定部族,comp.py)
  代码: 合法动作打分(成型买分/外族税;引擎文本值只在承诺方向内计)
  代码: when 预筛记忆库 → ≤16 条候选
  Nimble(本地 9B): 8 条适用性 noul + 1 条优先级 choice(带概率)
  代码: 命中记忆的 bias 注入动作评分
  引擎: 站位用 combat_preview 前瞻裁决(免费、毫秒级)
  饰品选择 ← 经验饰品表(235 条,n≥10 接管 186 条,余回退文本启发)

对局结束(冷路径,每局 1 次 API):
  deepseek: 对局日志 + 现有记忆 → ≤3 条候选三元组
  验证门: 配对 A/B(同种子 ON/OFF 各 N 局),dev+holdout 双集一致 + 显著才入库
```

三层分工:**Nimble 管判断、deepseek 管生成、引擎管验证**;英雄表/饰品表/价值模型
来自环境自博弈统计与拟合(Phase 2"环境数据训练"),不是权重学习。
诚实备注:记忆层目前是二阶杠杆(bias 幅值扫描无效;蒸馏第一批 9 条候选全被门
否决)——见路线图⑥。

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
  comp.py         成型模型:部族方向决策 + 承诺感知买分
  policy.py       合法动作评分 + 记忆 bias(消费成型方向与数据表)
  agent.py        单席位驱动(其余 7 席脚本 bot)
  generate.py     冷路径:deepseek 蒸馏候选记忆
  gate.py         A/B 验证门
data/
  hero_table.json     经验英雄表(115 英雄 × 64 局 = 7360 局)
  trinket_table.json  经验饰品表(235 饰品,n≥10 接管 186 条)
  value_model.txt     LightGBM 价值模型(v2;bench 混合制:初筛 top-2 + rollout)
  trajectories.npz    自博弈轨迹(价值模型训练数据)
memories/seed.jsonl   24 条种子记忆(已过 2048-token 预算实测)
scripts/
  play_one.py phase1_run.py                 单局 / 批量对局
  hero_table.py trinket_table.py            数据表构建(96 核并行)
  trinket_gate.py run_gate.py run_gate2.py  配对验证门(per-seed 全量落盘)
  gen_trajectories.py train_value.py        价值模型管线
  synergy_gen.py synergy_table.py synergy_gate.py  协同表管线(v1 门否决,表保留)
  pair_gate.py pair_adopt_gate.py        固定组三臂实验(6 对实测,买分倾斜未过门)
  scout_boards.py scout_gate.py          合成面板侦察(⑤,门否决,池保留)
  recipe_gate.py recipe_adopt_gate.py    HSReplay 阵容映射+因果 tier 榜(接线惰性)
  bench_bridge.py                           TavernBench 桥接
  param_sweep.py comp_sweep.py calibrate.py feature_ablation.py  调参/校准/消融
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

当前状态(2026-11-03,policy v18 = v16 + 英雄表 K64 + 成型模型 + 饰品表):
前四率 **~66%**(饰品表门 ON 臂 300 局合并 65.7%;最新单次 gym 70% @ seeds
1400–1499;bot 参照 59%)。TavernBench(`tavernbench.score` 口径):
combat 0.98 / targets 0.98 / strategy **0.45**(配方初筛,2026-11-03,此前
0.34)/ selection 0.58 / overall 0.62。详细的 70%+ 演进路线(优先级/
预期增益/把握度/已证伪方向)见
[docs/LEEAGENT_ROADMAP.md](../docs/LEEAGENT_ROADMAP.md)。

- **Phase 0(已完成)**: 种子记忆 + 热路径跑通,零训练基线。
- **Phase 1(已完成)**: 校准驱动迁移 + 阈值训练,v16 前四 64%(seeds 1200–1299)。
- **Phase 2(进行中)**: 环境数据训练——① 英雄表 K64、② 饰品表、③ 成型模型
  已采纳;⑦ 价值模型 v1(bench 混合制)采纳,v2 加特征证伪(RMSE 0.516 vs
  0.506,墙是隐藏信息);观察性卡牌协同表 v1 门否决(dev +0.14 / holdout
  −0.14,产物保留);固定组两卡包测得 6 对真效应(三臂因果协议),但买分
  倾斜与冻结保牌两种注入均未过采纳门——稀疏清单 × 自然出现率改变不了
  聚合指标(详见 roadmap);⑤合成面板侦察门否决(双集强反向,快照侦察
  的对手特异性信息是承重的);记忆冷路径蒸馏第一批 9 条候选全被门否决,
  待动词词表扩展后重试。
- 评测: TavernBench 桥接(states.jsonl.gz → 局面 → LeeAgent 决策 → 答案格式)。
