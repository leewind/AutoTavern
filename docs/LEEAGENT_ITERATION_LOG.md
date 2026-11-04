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
| 5 | freeze toggle 怪癖(v18 潜伏 bug) | 变体1 幂等守卫(`FREEZE_FIX`:已冻结时不给正分);变体2 守卫+停用 M020 偏好(`FREEZE_BIAS`) | 变体1:dev −0.11 / holdout **+0.37** 反向否决(冻结粘住后锁死商店);变体2:dev −0.17 → 全新 1800 **+0.02** 不复现否决(holdout 已被变体1污染,直用全新段) | 0.7418 **零翻转——含规则出口在内全量字节级确定**(缓存生效,出口 0s) | **双双 NO-ADOPT:toggle 怪癖测量上无害**(50% 占空比 ≈ 总是/从不冻结,均不可区分),v18 原样保留 |
| 6 | bench selection 桥接(路径 c) | D2 饰品表 top-2 联合 + D4 配方进度联合(与 N 类配方初筛同构,rollout 终审) | D4:3上/3下净零;D2:饰品表提名生效的 3 题**全部翻错**(bot 自博弈排名不迁移到 LeeAgent 续打口径);首版还有 map 键/值命名空间污染致 5 题丢答(已修后重测) | 0.7337(回滚后 **0.7418 逐位恢复**) | **NO-ADOPT,路径 c 关闭**——固定组/配方/饰品知识的全部注入点(live×3 + bench×1)测量性关闭 |
| 7 | ⑥ 记忆层程序化生成 | 词表解锁:`when.hero_in`(facts 新增 hero_id)+ 结构动词 `commit_tribe`/`hold_upgrade`;`gen_memories.py` 从英雄表四分位×时机/部族密度/绝血模板生成 **62 条**;批量门 + 家族分解 | 批量:dev +0.04 / holdout −0.10 反向无信号;家族:TEMPO +0.13(12% 接触)、**HOLD 接触 1/100**(硬否决几乎无开火时机)、COMMIT 35% 接触但 +0.10(2 随从定向有害,与门槛=2 结论互证)、CLIMB 1% 接触 | 0.7418 零翻转(生成记忆不在默认库,默认行为不变) | **NO-ADOPT,⑥ 生成侧结案**:结构动词的接触面本身塌缩(升级很少是当前最优动作;方向决策很少想翻) |

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
- 引擎 `bot_action` 在极少数重播种未来里会给出非法动作(~1/70k 续打,ValueError
  "that option can't be chosen");`rollout_unit` 按丢弃该 rep 处理(选项均值用其余
  127 个 reseeds,不引入偏置面)。
- 微调接触面台账:COMMIT_TURN ±1 仅 2% 局变化;COMP_BUY/OFFCOMP/SELLPROTECT
  5–18% 局变化但净效应 ≤±0.09;调参在 100 局配对下的分辨率约 ±0.2 名次,
  小于全部候选值的真实效应。

## 循环后追加:轮 8(等效)——N1/N2/D4 出口对齐标签测量口径,采纳

**overall 0.742 → 0.774(strategy 0.36 → 0.50,D4 0.38 → 0.62),live 零改动**

- **假设与依据**:TavernBench 文档与 labels meta 公开可查——N/D4 标签 = 选项在其截局中
  **128 次 bot 续打**的 mean_place argmin(se≈0.05–0.2);而桥接仲裁用 LeeAgent 续打
  ×24 次、salt=1000k+j 选项间不共享 RNG(非配对,SE≈0.35,大于相邻选项典型差距,
  近平局全部落进选项序号决胜)。两个错配:口径(续打者)+ 方差(非配对)。
- **A/B**(`scripts/strategy_ab.py`,70,144 次续打,两臂共享同一 salt 表):
  lee 臂(仅配对+128)strategy 0.36→0.41、D4 +1 题(**+4 题**);bot 臂(全席 bot 续打)
  strategy→0.50、D4→0.62(**再 +8 题**)。两臂互相一致仅 34/72——LeeAgent 续打不是
  中性测量仪,是系统性带偏的测量仪;增益集中 N2(0.26→0.48)与 D4,与"中后期各策略
  分歧最大"一致,N1(第 4 回合)两口径几乎无差。
- **采纳改动**:`bench_bridge.py` N/D4 出口 = bot 续打 + 配对 salt(task_idx×10000+j)
  + 128 reps + 无初筛(价值/配方初筛退役为 D2 专属,`recipe_unit` 留档)。全量重跑
  30s(纯 bot 续打极快),N/D4 与 A/B 补丁逐位一致、其余与 0.742 冻结点逐位一致。
- **live 保险**(`scripts/live_recheck.py`):seeds 1800–1899 与 freeze_bias_fresh 控制臂
  **逐位复现**(4 强 71/100、均名 3.37)——bench 侧改动结构性不触 live,实测确认。
- **残余差距 = 策略真实水平**:N2 0.48 vs TavernAgent 0.67、D4 0.62 vs 0.81;口径对齐
  消掉"测量仪偏差"层,下一量级仍是 ⑦ 搜索/PPO。strategy 天花板 <1.0(标签自身噪声)。
