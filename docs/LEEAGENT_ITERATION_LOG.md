# LeeAgent 迭代日志(/loop 驱动,2026-11-04 起)

协议:每轮做一条改进(路线图 1–7 优先级序),live 改动过 dev+holdout 配对门
(+全新段复现)后跑一次 TavernBench overall,逐轮记录。种子纪律见
[LEEAGENT_ROADMAP.md](LEEAGENT_ROADMAP.md);burn 台账同步更新。

| 轮 | 项 | 改动 | 门(dev/holdout/全新) | bench overall | 判定 |
|---|---|---|---|---|---|
| 1 | ④ 通用站位 | `lookahead.universal_order`:风怒居左/嘲讽贴核心/buff 载体靠后/亡语召唤靠右;`agent.UNIVERSAL_POS` 开关 | v1(dev −0.37/holdout −0.55/1600 **+0.29** 反向)→ 修正为"仅在规则命中时动" v2(−0.19/−0.34/1700 −0.24,合并 300 局 123好/93差 p≈0.045) | 0.7065(引擎类逐位不变;rollout D4/N1/N2 净 −1 题 = 噪声) | **采纳**(live −0.26 名次;bench 无回归) |

## 测量备忘

- **deepseek 规则出口有 run-to-run 噪声**:temperature 0 不保证复现,单次重跑
  E/R 类净翻转可达 ±3 题(≈overall ±0.008)。A/B 结论必须用引擎类
  (combat/ordering/positioning/targets 逐位比对)+ rollout 类单独归因,
  overall 差 <0.01 视为噪声。
- 站位 v1 的教训与 preview 站位同构:无规则命中的裸重排(atk_desc 类)是
  投机,同属被消融成分;规则只在"板上有对应随从"时才有信息。
