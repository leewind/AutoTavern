# LeeAgent 迭代日志(/loop 驱动,2026-11-04 起)

协议:每轮做一条改进(路线图 1–7 优先级序),live 改动过 dev+holdout 配对门
(+全新段复现)后跑一次 TavernBench overall,逐轮记录。种子纪律见
[LEEAGENT_ROADMAP.md](LEEAGENT_ROADMAP.md);burn 台账同步更新。

| 轮 | 项 | 改动 | 门(dev/holdout/全新) | bench overall | 判定 |
|---|---|---|---|---|---|
| 1 | ④ 通用站位 | `lookahead.universal_order`:风怒居左/嘲讽贴核心/buff 载体靠后/亡语召唤靠右;`agent.UNIVERSAL_POS` 开关 | v1(dev −0.37/holdout −0.55/1600 **+0.29** 反向)→ 修正为"仅在规则命中时动" v2(−0.19/−0.34/1700 −0.24,合并 300 局 123好/93差 p≈0.045) | 0.7065(引擎类逐位不变;rollout D4/N1/N2 净 −1 题 = 噪声) | **采纳**(live −0.26 名次;bench 无回归) |
| 2 | ③ 阈值坐标上升 | `comp_sweep2.py`:8 轴 13 候选值,dev 配对评估(每臂 100 局),采纳线 delta<−0.15 且好>差 | **全部 keep,无一采纳**;W_AFFINITY/W_DENSITY/W_HERO 六个值全部 0/0/100 零接触面;COMMIT_MIN_BOARD=2 接触 21% 净 +0.09 更差 | 0.7065(与轮 1 逐位一致,确定性二连;prompt 类 2 翻转抵消) | **NO-ADOPT**(诚实负结果:现值即 dev 局部最优) |
| 3 | bench rules 上下文 | ① R5 金色合成改确定性求解(prompt 全输入 + 引擎 `merge_golden` 公式);② deepseek 出口加固定机制附录(引擎源码提炼:金色公式/费用精确值/other-排除/战吼时序/升级价格衰减重置/合法动作空间) | bench 即门:rules 0.446→**0.696**(R5 8/8、E2 5→8、R1 +3、R3 +2),economy 0.65→0.725;E1 5→2(±3 噪声带内);引擎/rollout 类逐位不变 | **0.7065 → 0.7527**(+0.046,纯 prompt 侧,零引擎副作用) | **采纳** |
| 4 | 固定组→comp 锚定(路径 b) | `comp.PAIR_ANCHOR`(核心在场时部族方向分 +6 ≈ 2 随从亲和),配对门 dev+holdout | 接触面先测:41% 局持核心,14% 可锚定,但 **+6 锚定实际只改 2/200 局**(每集 1好/1差,98% 无变化)——核心在场时其部族多半已有板面存在或差距 >2 随从 | 0.7418(引擎类与轮 3 逐位一致;−0.011 全为出口噪声,本轮起规则出口加内容寻址缓存,抖动永久消除) | **NO-ADOPT,路径 b 测量性关闭**(PAIR_ANCHOR=0 留档) |

## 测量备忘

- **deepseek 规则出口有 run-to-run 噪声**:temperature 0 不保证复现,单次重跑
  E/R 类净翻转可达 ±3 题(≈overall ±0.008)。A/B 结论必须用引擎类
  (combat/ordering/positioning/targets 逐位比对)+ rollout 类单独归因,
  overall 差 <0.01 视为噪声。
- 站位 v1 的教训与 preview 站位同构:无规则命中的裸重排(atk_desc 类)是
  投机,同属被消融成分;规则只在"板上有对应随从"时才有信息。
- **方向决策权重是死旋钮**(轮 2):W_AFFINITY/W_DENSITY/W_HERO 在 2×权重
  幅度内不改变任何一局的成型方向——决策实际由板面部族计数字典序决定。
  今后成型模型的迭代只动结构(何时/是否承诺),不动打分权重。
- 微调接触面台账:COMMIT_TURN ±1 仅 2% 局变化;COMP_BUY/OFFCOMP/SELLPROTECT
  5–18% 局变化但净效应 ≤±0.09;调参在 100 局配对下的分辨率约 ±0.2 名次,
  小于全部候选值的真实效应。
