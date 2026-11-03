# LeeAgent TavernBench 全量逐题结果(2026-11-04,commit 363ebd7)

口径:`tavernbench.score`(全 368 题计分)。管线:引擎桥接(确定性)+ 配方初筛 + 规则出口(deepseek)。

| 类别 | n | acc |
|---|---|---|
| combat | 48 | 0.979 |
| economy | 40 | 0.725 |
| ordering | 40 | 0.950 |
| positioning | 40 | 0.900 |
| rules | 56 | 0.446 |
| selection | 48 | 0.583 |
| strategy | 56 | 0.393 |
| targets | 40 | 0.975 |

**overall acc 0.717**(264/368)

| id | 类别 | 场景 | 我方答案 | 标签 | 对错 | 得分 |
|---|---|---|---|---|---|---|
| B1-000 | combat | B1 | {"answer": "random"} | {"answer": "random"} | ✓ | 1.000 |
| B1-001 | combat | B1 | {"answer": "random"} | {"answer": "random"} | ✓ | 1.000 |
| B1-002 | combat | B1 | {"answer": "random"} | {"answer": "random"} | ✓ | 1.000 |
| B1-003 | combat | B1 | {"answer": "random"} | {"answer": "random"} | ✓ | 1.000 |
| B1-004 | combat | B1 | {"answer": "random"} | {"answer": "random"} | ✓ | 1.000 |
| B1-005 | combat | B1 | {"answer": "random"} | {"answer": "random"} | ✓ | 1.000 |
| B1-006 | combat | B1 | {"answer": "opponent"} | {"answer": "opponent"} | ✓ | 1.000 |
| B1-007 | combat | B1 | {"answer": "you"} | {"answer": "you"} | ✓ | 1.000 |
| B2-000 | combat | B2 | {"answer": "tie"} | {"answer": "tie"} | ✓ | 1.000 |
| B2-001 | combat | B2 | {"answer": "win"} | {"answer": "win"} | ✓ | 1.000 |
| B2-002 | combat | B2 | {"answer": "loss"} | {"answer": "loss"} | ✓ | 1.000 |
| B2-003 | combat | B2 | {"answer": "loss"} | {"answer": "loss"} | ✓ | 1.000 |
| B2-004 | combat | B2 | {"answer": "loss"} | {"answer": "loss"} | ✓ | 1.000 |
| B2-005 | combat | B2 | {"answer": "win"} | {"answer": "win"} | ✓ | 1.000 |
| B2-006 | combat | B2 | {"answer": "loss"} | {"answer": "loss"} | ✓ | 1.000 |
| B2-007 | combat | B2 | {"answer": "loss"} | {"answer": "loss"} | ✓ | 1.000 |
| B3-000 | combat | B3 | {"win": 0.7393, "tie": 0.207, "loss": 0.0537} | {"answer": {"win": 0.7539, "tie": 0.2017, "loss": 0.0444}} | ✓ | 1.000 |
| B3-001 | combat | B3 | {"win": 0.6084, "tie": 0.3096, "loss": 0.082} | {"answer": {"win": 0.6064, "tie": 0.3125, "loss": 0.0811}} | ✓ | 1.000 |
| B3-002 | combat | B3 | {"win": 0.7129, "tie": 0.0186, "loss": 0.2686} | {"answer": {"win": 0.7075, "tie": 0.0266, "loss": 0.2659}} | ✓ | 1.000 |
| B3-003 | combat | B3 | {"win": 0.0303, "tie": 0.1309, "loss": 0.8389} | {"answer": {"win": 0.031, "tie": 0.1316, "loss": 0.8374}} | ✓ | 1.000 |
| B3-004 | combat | B3 | {"win": 0.7842, "tie": 0.0996, "loss": 0.1162} | {"answer": {"win": 0.8071, "tie": 0.0901, "loss": 0.1028}} | ✓ | 1.000 |
| B3-005 | combat | B3 | {"win": 0.2295, "tie": 0.2402, "loss": 0.5303} | {"answer": {"win": 0.2544, "tie": 0.2334, "loss": 0.5122}} | ✓ | 1.000 |
| B3-006 | combat | B3 | {"win": 0.8066, "tie": 0.1611, "loss": 0.0322} | {"answer": {"win": 0.8191, "tie": 0.1519, "loss": 0.0291}} | ✓ | 1.000 |
| B3-007 | combat | B3 | {"win": 0.6328, "tie": 0.3066, "loss": 0.0605} | {"answer": {"win": 0.6279, "tie": 0.3142, "loss": 0.0579}} | ✓ | 1.000 |
| B4-000 | combat | B4 | {"answer": 6.021} | {"answer": 5.814, "tol": 0.25} | ✓ | 0.964 |
| B4-001 | combat | B4 | {"answer": 6.014} | {"answer": 5.99, "tol": 0.25} | ✓ | 0.996 |
| B4-002 | combat | B4 | {"answer": 3.66} | {"answer": 3.717, "tol": 0.25} | ✓ | 0.985 |
| B4-003 | combat | B4 | {"answer": 1.713} | {"answer": 1.745, "tol": 0.25} | ✓ | 0.982 |
| B4-004 | combat | B4 | {"answer": 12.0} | {"answer": 12.0, "tol": 0.25} | ✓ | 1.000 |
| B4-005 | combat | B4 | {"answer": 5.414} | {"answer": 5.454, "tol": 0.25} | ✓ | 0.993 |
| B4-006 | combat | B4 | {"answer": 11.02} | {"answer": 11.083, "tol": 0.25} | ✓ | 0.994 |
| B4-007 | combat | B4 | {"answer": 10.793} | {"answer": 10.877, "tol": 0.25} | ✓ | 0.992 |
| B5-000 | combat | B5 | {"answer": 0.7705} | {"answer": 0.77, "tol": 0.15} | ✓ | 1.000 |
| B5-001 | combat | B5 | {"answer": 0.9375} | {"answer": 0.93, "tol": 0.15} | ✓ | 0.993 |
| B5-002 | combat | B5 | {"answer": 0.9248} | {"answer": 0.8675, "tol": 0.15} | ✓ | 0.943 |
| B5-003 | combat | B5 | {"answer": 0.7168} | {"answer": 0.6975, "tol": 0.15} | ✓ | 0.981 |
| B5-004 | combat | B5 | {"answer": 0.6846} | {"answer": 0.6875, "tol": 0.15} | ✓ | 0.997 |
| B5-005 | combat | B5 | {"answer": 0.9102} | {"answer": 0.9, "tol": 0.15} | ✓ | 0.990 |
| B5-006 | combat | B5 | {"answer": 0.8906} | {"answer": 0.87, "tol": 0.15} | ✓ | 0.979 |
| B5-007 | combat | B5 | {"answer": 0.7188} | {"answer": 0.735, "tol": 0.15} | ✓ | 0.984 |
| B6-000 | combat | B6 | {"win": 0.2207, "tie": 0.3193, "loss": 0.46} | {"answer": {"win": 0.2117, "tie": 0.3284, "loss": 0.46}} | ✓ | 1.000 |
| B6-001 | combat | B6 | {"win": 0.5498, "tie": 0.167, "loss": 0.2832} | {"answer": {"win": 0.5388, "tie": 0.167, "loss": 0.2942}} | ✓ | 1.000 |
| B6-002 | combat | B6 | {"win": 0.7939, "tie": 0.1484, "loss": 0.0576} | {"answer": {"win": 0.8105, "tie": 0.1355, "loss": 0.054}} | ✓ | 1.000 |
| B6-003 | combat | B6 | {"win": 0.2627, "tie": 0.2881, "loss": 0.4492} | {"answer": {"win": 0.2522, "tie": 0.3081, "loss": 0.4397}} | ✓ | 1.000 |
| B6-004 | combat | B6 | {"win": 0.7061, "tie": 0.293, "loss": 0.001} | {"answer": {"win": 0.6941, "tie": 0.3054, "loss": 0.0005}} | ✓ | 1.000 |
| B6-005 | combat | B6 | {"win": 0.0234, "tie": 0.0898, "loss": 0.8867} | {"answer": {"win": 0.0166, "tie": 0.0928, "loss": 0.8906}} | ✓ | 1.000 |
| B6-006 | combat | B6 | {"win": 0.3369, "tie": 0.3369, "loss": 0.3262} | {"answer": {"win": 0.3342, "tie": 0.3354, "loss": 0.3303}} | ✗ | 1.000 |
| B6-007 | combat | B6 | {"win": 0.6182, "tie": 0.3057, "loss": 0.0762} | {"answer": {"win": 0.6025, "tie": 0.3242, "loss": 0.0732}} | ✓ | 1.000 |
| D1-000 | selection | D1 | {"answer": 1} | {"answer": 3} | ✗ | 0.000 |
| D1-001 | selection | D1 | {"answer": 2} | {"answer": 1} | ✗ | 0.000 |
| D1-002 | selection | D1 | {"answer": 0} | {"answer": 1} | ✗ | 0.000 |
| D1-003 | selection | D1 | {"answer": 0} | {"answer": 0} | ✓ | 1.000 |
| D1-004 | selection | D1 | {"answer": 3} | {"answer": 2} | ✗ | 0.000 |
| D1-005 | selection | D1 | {"answer": 1} | {"answer": 1} | ✓ | 1.000 |
| D1-006 | selection | D1 | {"answer": 3} | {"answer": 0} | ✗ | 0.000 |
| D1-007 | selection | D1 | {"answer": 3} | {"answer": 3} | ✓ | 1.000 |
| D2-000 | selection | D2 | {"answer": 2} | {"answer": 0} | ✗ | 0.000 |
| D2-001 | selection | D2 | {"answer": 0} | {"answer": 0} | ✓ | 1.000 |
| D2-002 | selection | D2 | {"answer": 3} | {"answer": 3} | ✓ | 1.000 |
| D2-003 | selection | D2 | {"answer": 3} | {"answer": 1} | ✗ | 0.000 |
| D2-004 | selection | D2 | {"answer": 0} | {"answer": 0} | ✓ | 1.000 |
| D2-005 | selection | D2 | {"answer": 2} | {"answer": 3} | ✗ | 0.000 |
| D2-006 | selection | D2 | {"answer": 3} | {"answer": 3} | ✓ | 1.000 |
| D2-007 | selection | D2 | {"answer": 0} | {"answer": 1} | ✗ | 0.000 |
| D3-000 | selection | D3 | {"answer": 1} | {"answer": 0.1885, "values": {"0": 0.0, "1": 0.1885, "2":… | ✓ | 1.000 |
| D3-001 | selection | D3 | {"answer": 1} | {"answer": 0.6006, "values": {"0": 0.4141, "1": 0.6006, "… | ✓ | 1.000 |
| D3-002 | selection | D3 | {"answer": 1} | {"answer": 0.3633, "values": {"0": 0.0, "1": 0.3633, "2":… | ✓ | 1.000 |
| D3-003 | selection | D3 | {"answer": 1} | {"answer": 0.1904, "values": {"0": 0.1055, "1": 0.1904, "… | ✓ | 1.000 |
| D3-004 | selection | D3 | {"answer": 0} | {"answer": 1.0, "values": {"0": 1.0, "1": 0.5303, "2": 0.… | ✓ | 1.000 |
| D3-005 | selection | D3 | {"answer": 0} | {"answer": 1.0, "values": {"0": 1.0, "1": 0.6689, "2": 0.… | ✓ | 1.000 |
| D3-006 | selection | D3 | {"answer": 0} | {"answer": 0.7705, "values": {"0": 0.7705, "1": 0.5752, "… | ✓ | 1.000 |
| D3-007 | selection | D3 | {"answer": 0} | {"answer": 0.2891, "values": {"0": 0.2891, "1": 0.0273, "… | ✓ | 1.000 |
| D4-000 | selection | D4 | {"answer": 0} | {"answer": 1} | ✗ | 0.000 |
| D4-001 | selection | D4 | {"answer": 1} | {"answer": 1} | ✓ | 1.000 |
| D4-002 | selection | D4 | {"answer": 2} | {"answer": 0} | ✗ | 0.000 |
| D4-003 | selection | D4 | {"answer": 1} | {"answer": 1} | ✓ | 1.000 |
| D4-004 | selection | D4 | {"answer": 0} | {"answer": 1} | ✗ | 0.000 |
| D4-005 | selection | D4 | {"answer": 2} | {"answer": 1} | ✗ | 0.000 |
| D4-006 | selection | D4 | {"answer": 1} | {"answer": 3} | ✗ | 0.000 |
| D4-007 | selection | D4 | {"answer": 1} | {"answer": 1} | ✓ | 1.000 |
| D4-008 | selection | D4 | {"answer": 0} | {"answer": 1} | ✗ | 0.000 |
| D4-009 | selection | D4 | {"answer": 2} | {"answer": 2} | ✓ | 1.000 |
| D4-010 | selection | D4 | {"answer": 0} | {"answer": 2} | ✗ | 0.000 |
| D4-011 | selection | D4 | {"answer": 1} | {"answer": 3} | ✗ | 0.000 |
| D4-012 | selection | D4 | {"answer": 0} | {"answer": 1} | ✗ | 0.000 |
| D4-013 | selection | D4 | {"answer": 1} | {"answer": 1} | ✓ | 1.000 |
| D4-014 | selection | D4 | {"answer": 0} | {"answer": 1} | ✗ | 0.000 |
| D4-015 | selection | D4 | {"answer": 0} | {"answer": 1} | ✗ | 0.000 |
| D5-000 | selection | D5 | {"answer": 2} | {"answer": 1.0, "values": {"0": 0.8691, "1": 0.668, "2": … | ✓ | 1.000 |
| D5-001 | selection | D5 | {"answer": 2} | {"answer": 0.708, "values": {"0": 0.5635, "1": 0.6221, "2… | ✓ | 1.000 |
| D5-002 | selection | D5 | {"answer": 1} | {"answer": 0.791, "values": {"0": 0.4922, "1": 0.791, "2"… | ✓ | 1.000 |
| D5-003 | selection | D5 | {"answer": 1} | {"answer": 1.0, "values": {"0": 0.0195, "1": 1.0, "2": 0.… | ✓ | 1.000 |
| D5-004 | selection | D5 | {"answer": 0} | {"answer": 0.2314, "values": {"0": 0.2314, "1": 0.0332, "… | ✓ | 1.000 |
| D5-005 | selection | D5 | {"answer": 1} | {"answer": 0.8301, "values": {"0": 0.6855, "1": 0.8301, "… | ✓ | 1.000 |
| D5-006 | selection | D5 | {"answer": 0} | {"answer": 0.752, "values": {"0": 0.752, "1": 0.6572, "2"… | ✓ | 1.000 |
| D5-007 | selection | D5 | {"answer": 2} | {"answer": 0.5781, "values": {"0": 0.4834, "1": 0.3623, "… | ✓ | 1.000 |
| E1-000 | economy | E1 | {"answer": 5} | {"answer": 5} | ✓ | 1.000 |
| E1-001 | economy | E1 | {"answer": 9} | {"answer": 9} | ✓ | 1.000 |
| E1-002 | economy | E1 | {"answer": 2} | {"answer": 2} | ✓ | 1.000 |
| E1-003 | economy | E1 | {"answer": 7} | {"answer": 7} | ✓ | 1.000 |
| E1-004 | economy | E1 | {"answer": 3} | {"answer": 3} | ✓ | 1.000 |
| E1-005 | economy | E1 | {"answer": 5} | {"answer": 9} | ✗ | 0.000 |
| E1-006 | economy | E1 | {"answer": 2} | {"answer": 3} | ✗ | 0.000 |
| E1-007 | economy | E1 | {"answer": 5} | {"answer": 5} | ✓ | 1.000 |
| E2-000 | economy | E2 | {"answer": 12} | {"answer": 12} | ✓ | 1.000 |
| E2-001 | economy | E2 | {"answer": 10} | {"answer": 0} | ✗ | 0.000 |
| E2-002 | economy | E2 | {"answer": 10} | {"answer": 10} | ✓ | 1.000 |
| E2-003 | economy | E2 | {"answer": 4} | {"answer": 6} | ✗ | 0.000 |
| E2-004 | economy | E2 | {"answer": 6} | {"answer": 6} | ✓ | 1.000 |
| E2-005 | economy | E2 | {"answer": 10} | {"answer": 10} | ✓ | 1.000 |
| E2-006 | economy | E2 | {"answer": 4} | {"answer": 6} | ✗ | 0.000 |
| E2-007 | economy | E2 | {"answer": 9} | {"answer": 9} | ✓ | 1.000 |
| E3-000 | economy | E3 | {"answer": [1, 2]} | {"answer": 0.6865, "values": {"": 0.0, "0": 0.0, "1": 0.0… | ✓ | 1.000 |
| E3-001 | economy | E3 | {"answer": [2, 4, 1]} | {"answer": 0.0889, "values": {"": 0.0, "0": 0.0, "1": 0.0… | ✓ | 0.989 |
| E3-002 | economy | E3 | {"answer": [1, 4]} | {"answer": 0.083, "values": {"": 0.0, "0": 0.0, "1": 0.0,… | ✓ | 1.000 |
| E3-003 | economy | E3 | {"answer": [2, 0]} | {"answer": 0.7646, "values": {"": 0.0, "0": 0.0273, "1": … | ✓ | 1.000 |
| E3-004 | economy | E3 | {"answer": [4, 5, 2]} | {"answer": 0.7949, "values": {"": 0.0, "0": 0.0, "1": 0.0… | ✓ | 1.000 |
| E3-005 | economy | E3 | {"answer": [2, 1]} | {"answer": 0.0957, "values": {"": 0.0, "0": 0.0, "1": 0.0… | ✓ | 1.000 |
| E3-006 | economy | E3 | {"answer": [0, 1]} | {"answer": 1.0, "values": {"": 0.0, "0": 0.0, "1": 0.501,… | ✓ | 1.000 |
| E3-007 | economy | E3 | {"answer": [3, 2, 4]} | {"answer": 0.9961, "values": {"": 0.0, "0": 0.0, "1": 0.0… | ✓ | 1.000 |
| E4-000 | economy | E4 | {"answer": "no"} | {"answer": "no"} | ✓ | 1.000 |
| E4-001 | economy | E4 | {"answer": "yes"} | {"answer": "yes"} | ✓ | 1.000 |
| E4-002 | economy | E4 | {"answer": "yes"} | {"answer": "yes"} | ✓ | 1.000 |
| E4-003 | economy | E4 | {"answer": "yes"} | {"answer": "yes"} | ✓ | 1.000 |
| E4-004 | economy | E4 | {"answer": "no"} | {"answer": "no"} | ✓ | 1.000 |
| E4-005 | economy | E4 | {"answer": "yes"} | {"answer": "no"} | ✗ | 0.000 |
| E4-006 | economy | E4 | {"answer": "yes"} | {"answer": "yes"} | ✓ | 1.000 |
| E4-007 | economy | E4 | {"answer": "no"} | {"answer": "no"} | ✓ | 1.000 |
| E5-000 | economy | E5 | {"answer": 4} | {"answer": 4} | ✓ | 1.000 |
| E5-001 | economy | E5 | {"answer": 0} | {"answer": 3} | ✗ | 0.000 |
| E5-002 | economy | E5 | {"answer": 0} | {"answer": 3} | ✗ | 0.000 |
| E5-003 | economy | E5 | {"answer": 4} | {"answer": 7} | ✗ | 0.000 |
| E5-004 | economy | E5 | (未答) | {"answer": 5} | ✗ | 0.000 |
| E5-005 | economy | E5 | (未答) | {"answer": 5} | ✗ | 0.000 |
| E5-006 | economy | E5 | {"answer": 3} | {"answer": 3} | ✓ | 1.000 |
| E5-007 | economy | E5 | {"answer": 5} | {"answer": 5} | ✓ | 1.000 |
| N1-000 | strategy | N1 | {"answer": "B"} | {"answer": "A"} | ✗ | 0.000 |
| N1-001 | strategy | N1 | {"answer": "C"} | {"answer": "B"} | ✗ | 0.000 |
| N1-002 | strategy | N1 | {"answer": "A"} | {"answer": "C"} | ✗ | 0.000 |
| N1-003 | strategy | N1 | {"answer": "D"} | {"answer": "D"} | ✓ | 1.000 |
| N1-004 | strategy | N1 | {"answer": "B"} | {"answer": "A"} | ✗ | 0.000 |
| N1-005 | strategy | N1 | {"answer": "D"} | {"answer": "B"} | ✗ | 0.000 |
| N1-006 | strategy | N1 | {"answer": "B"} | {"answer": "C"} | ✗ | 0.000 |
| N1-007 | strategy | N1 | {"answer": "C"} | {"answer": "D"} | ✗ | 0.000 |
| N1-008 | strategy | N1 | {"answer": "A"} | {"answer": "A"} | ✓ | 1.000 |
| N1-009 | strategy | N1 | {"answer": "A"} | {"answer": "B"} | ✗ | 0.000 |
| N1-010 | strategy | N1 | {"answer": "D"} | {"answer": "C"} | ✗ | 0.000 |
| N1-011 | strategy | N1 | {"answer": "C"} | {"answer": "D"} | ✗ | 0.000 |
| N1-012 | strategy | N1 | {"answer": "A"} | {"answer": "A"} | ✓ | 1.000 |
| N1-013 | strategy | N1 | {"answer": "B"} | {"answer": "B"} | ✓ | 1.000 |
| N1-014 | strategy | N1 | {"answer": "D"} | {"answer": "C"} | ✗ | 0.000 |
| N1-015 | strategy | N1 | {"answer": "A"} | {"answer": "A"} | ✓ | 1.000 |
| N1-016 | strategy | N1 | {"answer": "B"} | {"answer": "B"} | ✓ | 1.000 |
| N1-017 | strategy | N1 | {"answer": "A"} | {"answer": "C"} | ✗ | 0.000 |
| N1-018 | strategy | N1 | {"answer": "B"} | {"answer": "A"} | ✗ | 0.000 |
| N1-019 | strategy | N1 | {"answer": "D"} | {"answer": "B"} | ✗ | 0.000 |
| N1-020 | strategy | N1 | {"answer": "A"} | {"answer": "C"} | ✗ | 0.000 |
| N1-021 | strategy | N1 | {"answer": "D"} | {"answer": "A"} | ✗ | 0.000 |
| N1-022 | strategy | N1 | {"answer": "B"} | {"answer": "B"} | ✓ | 1.000 |
| N1-023 | strategy | N1 | {"answer": "D"} | {"answer": "C"} | ✗ | 0.000 |
| N1-024 | strategy | N1 | {"answer": "A"} | {"answer": "A"} | ✓ | 1.000 |
| N1-025 | strategy | N1 | {"answer": "C"} | {"answer": "C"} | ✓ | 1.000 |
| N1-026 | strategy | N1 | {"answer": "C"} | {"answer": "C"} | ✓ | 1.000 |
| N1-027 | strategy | N1 | {"answer": "D"} | {"answer": "C"} | ✗ | 0.000 |
| N1-028 | strategy | N1 | {"answer": "B"} | {"answer": "C"} | ✗ | 0.000 |
| N2-000 | strategy | N2 | {"answer": "A"} | {"answer": "A"} | ✓ | 1.000 |
| N2-001 | strategy | N2 | {"answer": "C"} | {"answer": "B"} | ✗ | 0.000 |
| N2-002 | strategy | N2 | {"answer": "C"} | {"answer": "C"} | ✓ | 1.000 |
| N2-003 | strategy | N2 | {"answer": "A"} | {"answer": "D"} | ✗ | 0.000 |
| N2-004 | strategy | N2 | {"answer": "D"} | {"answer": "A"} | ✗ | 0.000 |
| N2-005 | strategy | N2 | {"answer": "C"} | {"answer": "B"} | ✗ | 0.000 |
| N2-006 | strategy | N2 | {"answer": "C"} | {"answer": "C"} | ✓ | 1.000 |
| N2-007 | strategy | N2 | {"answer": "A"} | {"answer": "D"} | ✗ | 0.000 |
| N2-008 | strategy | N2 | {"answer": "B"} | {"answer": "A"} | ✗ | 0.000 |
| N2-009 | strategy | N2 | {"answer": "C"} | {"answer": "B"} | ✗ | 0.000 |
| N2-010 | strategy | N2 | {"answer": "A"} | {"answer": "C"} | ✗ | 0.000 |
| N2-011 | strategy | N2 | {"answer": "A"} | {"answer": "D"} | ✗ | 0.000 |
| N2-012 | strategy | N2 | {"answer": "A"} | {"answer": "A"} | ✓ | 1.000 |
| N2-013 | strategy | N2 | {"answer": "A"} | {"answer": "B"} | ✗ | 0.000 |
| N2-014 | strategy | N2 | {"answer": "A"} | {"answer": "C"} | ✗ | 0.000 |
| N2-015 | strategy | N2 | {"answer": "D"} | {"answer": "D"} | ✓ | 1.000 |
| N2-016 | strategy | N2 | {"answer": "A"} | {"answer": "A"} | ✓ | 1.000 |
| N2-017 | strategy | N2 | {"answer": "B"} | {"answer": "B"} | ✓ | 1.000 |
| N2-018 | strategy | N2 | {"answer": "C"} | {"answer": "C"} | ✓ | 1.000 |
| N2-019 | strategy | N2 | {"answer": "B"} | {"answer": "D"} | ✗ | 0.000 |
| N2-020 | strategy | N2 | {"answer": "C"} | {"answer": "A"} | ✗ | 0.000 |
| N2-021 | strategy | N2 | {"answer": "B"} | {"answer": "B"} | ✓ | 1.000 |
| N2-022 | strategy | N2 | {"answer": "B"} | {"answer": "C"} | ✗ | 0.000 |
| N2-023 | strategy | N2 | {"answer": "A"} | {"answer": "D"} | ✗ | 0.000 |
| N2-024 | strategy | N2 | {"answer": "B"} | {"answer": "B"} | ✓ | 1.000 |
| N2-025 | strategy | N2 | {"answer": "C"} | {"answer": "C"} | ✓ | 1.000 |
| N2-026 | strategy | N2 | {"answer": "C"} | {"answer": "C"} | ✓ | 1.000 |
| O1-000 | ordering | O1 | {"answer": "BDCA"} | {"answer": 0.8984, "values": {"ABCD": 0.6699, "ABDC": 0.8… | ✓ | 1.000 |
| O1-001 | ordering | O1 | {"answer": "BAC"} | {"answer": 0.3027, "values": {"ABC": 0.2314, "ACB": 0.231… | ✓ | 1.000 |
| O1-002 | ordering | O1 | {"answer": "BCAD"} | {"answer": 0.3564, "values": {"ABCD": 0.0, "ABDC": 0.0, "… | ✓ | 1.000 |
| O1-003 | ordering | O1 | {"answer": "BAC"} | {"answer": 1.0, "values": {"ABC": 0.9043, "ACB": 0.9043, … | ✓ | 1.000 |
| O1-004 | ordering | O1 | {"answer": "BCAD"} | {"answer": 0.9297, "values": {"ABCD": 0.8916, "ABDC": 0.8… | ✓ | 1.000 |
| O1-005 | ordering | O1 | {"answer": "BCAD"} | {"answer": 0.6406, "values": {"ABCD": 0.0273, "ABDC": 0.0… | ✓ | 1.000 |
| O1-006 | ordering | O1 | {"answer": "ABCD"} | {"answer": 0.9863, "values": {"ABCD": 0.9863, "ABDC": 0.9… | ✓ | 1.000 |
| O1-007 | ordering | O1 | {"answer": "ABC"} | {"answer": 0.5068, "values": {"ABC": 0.5068, "ACB": 0.344… | ✓ | 1.000 |
| O2-000 | ordering | O2 | {"answer": "BCA"} | {"answer": 0.2705, "values": {"ABC": 0.1572, "ACB": 0.178… | ✓ | 1.000 |
| O2-001 | ordering | O2 | {"answer": "CAB"} | {"answer": 0.9258, "values": {"ABC": 0.5645, "ACB": 0.897… | ✓ | 1.000 |
| O2-002 | ordering | O2 | {"answer": "BCA"} | {"answer": 0.5146, "values": {"ABC": 0.376, "ACB": 0.2881… | ✓ | 1.000 |
| O2-003 | ordering | O2 | {"answer": "BAC"} | {"answer": 0.6533, "values": {"ABC": 0.6533, "ACB": 0.612… | ✗ | 0.906 |
| O2-004 | ordering | O2 | {"answer": "CAB"} | {"answer": 0.2842, "values": {"ABC": 0.0332, "ACB": 0.226… | ✓ | 1.000 |
| O2-005 | ordering | O2 | {"answer": "CAB"} | {"answer": 0.9844, "values": {"ABC": 0.7432, "ACB": 0.859… | ✓ | 1.000 |
| O2-006 | ordering | O2 | {"answer": "ACB"} | {"answer": 0.7207, "values": {"ABC": 0.6836, "ACB": 0.720… | ✓ | 1.000 |
| O2-007 | ordering | O2 | {"answer": "CBA"} | {"answer": 0.625, "values": {"ABC": 0.6025, "ACB": 0.5156… | ✓ | 1.000 |
| O3-000 | ordering | O3 | {"answer": "ABC"} | {"answer": 0.8818, "values": {"ABC": 0.8818, "ACB": 0.695… | ✓ | 1.000 |
| O3-001 | ordering | O3 | {"answer": "ABCD"} | {"answer": 1.0, "values": {"ABCD": 1.0, "ABDC": 1.0, "ACB… | ✓ | 1.000 |
| O3-002 | ordering | O3 | {"answer": "ABC"} | {"answer": 0.2969, "values": {"ABC": 0.2754, "ACB": 0.0, … | ✓ | 0.928 |
| O3-003 | ordering | O3 | {"answer": "BAC"} | {"answer": 0.957, "values": {"ABC": 0.8535, "ACB": 0.6895… | ✓ | 1.000 |
| O3-004 | ordering | O3 | {"answer": "ABCD"} | {"answer": 0.1787, "values": {"ABCD": 0.1787, "ABDC": 0.1… | ✓ | 1.000 |
| O3-005 | ordering | O3 | {"answer": "ABCD"} | {"answer": 1.0, "values": {"ABCD": 1.0, "ABDC": 1.0, "ACB… | ✓ | 1.000 |
| O3-006 | ordering | O3 | {"answer": "BAC"} | {"answer": 0.2471, "values": {"ABC": 0.1992, "ACB": 0.007… | ✓ | 1.000 |
| O3-007 | ordering | O3 | {"answer": "BAC"} | {"answer": 0.5713, "values": {"ABC": 0.0674, "ACB": 0.018… | ✓ | 1.000 |
| O4-000 | ordering | O4 | {"answer": "CAB"} | {"answer": 0.873, "values": {"ABC": 0.3877, "ACB": 0.751,… | ✓ | 1.000 |
| O4-001 | ordering | O4 | {"answer": "ACB"} | {"answer": 0.1904, "values": {"ABC": 0.1279, "ACB": 0.190… | ✓ | 1.000 |
| O4-002 | ordering | O4 | {"answer": "ABC"} | {"answer": 0.5967, "values": {"ABC": 0.5605, "ACB": 0.596… | ✗ | 0.939 |
| O4-003 | ordering | O4 | {"answer": "CBA"} | {"answer": 0.7949, "values": {"ABC": 0.6748, "ACB": 0.723… | ✓ | 1.000 |
| O4-004 | ordering | O4 | {"answer": "ACB"} | {"answer": 0.1787, "values": {"ABC": 0.1787, "ACB": 0.156… | ✓ | 0.874 |
| O4-005 | ordering | O4 | {"answer": "BCA"} | {"answer": 0.6465, "values": {"ABC": 0.5889, "ACB": 0.587… | ✓ | 1.000 |
| O4-006 | ordering | O4 | {"answer": "ACB"} | {"answer": 0.5879, "values": {"ABC": 0.4385, "ACB": 0.587… | ✓ | 1.000 |
| O4-007 | ordering | O4 | {"answer": "CAB"} | {"answer": 0.8945, "values": {"ABC": 0.3398, "ACB": 0.806… | ✓ | 1.000 |
| O5-000 | ordering | O5 | {"answer": "BACD"} | {"answer": 0.4307, "values": {"ABCD": 0.3809, "ABDC": 0.3… | ✓ | 1.000 |
| O5-001 | ordering | O5 | {"answer": "ABCD"} | {"answer": 0.5322, "values": {"ABCD": 0.5322, "ABDC": 0.5… | ✓ | 1.000 |
| O5-002 | ordering | O5 | {"answer": "BACD"} | {"answer": 0.9414, "values": {"ABCD": 0.8105, "ABDC": 0.8… | ✓ | 1.000 |
| O5-003 | ordering | O5 | {"answer": "BACD"} | {"answer": 0.6865, "values": {"ABCD": 0.5674, "ABDC": 0.5… | ✓ | 1.000 |
| O5-004 | ordering | O5 | {"answer": "ABDC"} | {"answer": 0.4951, "values": {"ABCD": 0.0, "ABDC": 0.4951… | ✓ | 1.000 |
| O5-005 | ordering | O5 | {"answer": "BACD"} | {"answer": 0.6533, "values": {"ABCD": 0.6211, "ABDC": 0.6… | ✓ | 1.000 |
| O5-006 | ordering | O5 | {"answer": "ABC"} | {"answer": 1.0, "values": {"ABC": 1.0, "ACB": 0.3799, "BA… | ✓ | 1.000 |
| O5-007 | ordering | O5 | {"answer": "ABCD"} | {"answer": 0.874, "values": {"ABCD": 0.874, "ABDC": 0.874… | ✓ | 1.000 |
| P1-000 | positioning | P1 | {"answer": "A"} | {"answer": "A"} | ✓ | 1.000 |
| P1-001 | positioning | P1 | {"answer": "C"} | {"answer": "C"} | ✓ | 1.000 |
| P1-002 | positioning | P1 | {"answer": "C"} | {"answer": "A"} | ✗ | 0.000 |
| P1-003 | positioning | P1 | {"answer": "D"} | {"answer": "D"} | ✓ | 1.000 |
| P1-004 | positioning | P1 | {"answer": "E"} | {"answer": "E"} | ✓ | 1.000 |
| P1-005 | positioning | P1 | {"answer": "E"} | {"answer": "E"} | ✓ | 1.000 |
| P1-006 | positioning | P1 | {"answer": "E"} | {"answer": "E"} | ✓ | 1.000 |
| P1-007 | positioning | P1 | {"answer": "B"} | {"answer": "B"} | ✓ | 1.000 |
| P2-000 | positioning | P2 | {"answer": "C"} | {"answer": "C"} | ✓ | 1.000 |
| P2-001 | positioning | P2 | {"answer": "C"} | {"answer": "D"} | ✗ | 0.000 |
| P2-002 | positioning | P2 | {"answer": "E"} | {"answer": "E"} | ✓ | 1.000 |
| P2-003 | positioning | P2 | {"answer": "A"} | {"answer": "A"} | ✓ | 1.000 |
| P2-004 | positioning | P2 | {"answer": "D"} | {"answer": "D"} | ✓ | 1.000 |
| P2-005 | positioning | P2 | {"answer": "D"} | {"answer": "D"} | ✓ | 1.000 |
| P2-006 | positioning | P2 | {"answer": "A"} | {"answer": "A"} | ✓ | 1.000 |
| P2-007 | positioning | P2 | {"answer": "B"} | {"answer": "B"} | ✓ | 1.000 |
| P3-000 | positioning | P3 | {"answer": "D"} | {"answer": "D"} | ✓ | 1.000 |
| P3-001 | positioning | P3 | {"answer": "E"} | {"answer": "E"} | ✓ | 1.000 |
| P3-002 | positioning | P3 | {"answer": "E"} | {"answer": "E"} | ✓ | 1.000 |
| P3-003 | positioning | P3 | {"answer": "C"} | {"answer": "C"} | ✓ | 1.000 |
| P3-004 | positioning | P3 | {"answer": "D"} | {"answer": "D"} | ✓ | 1.000 |
| P3-005 | positioning | P3 | {"answer": "E"} | {"answer": "E"} | ✓ | 1.000 |
| P3-006 | positioning | P3 | {"answer": "B"} | {"answer": "D"} | ✗ | 0.000 |
| P3-007 | positioning | P3 | {"answer": "D"} | {"answer": "D"} | ✓ | 1.000 |
| P4-000 | positioning | P4 | {"answer": "D"} | {"answer": "D"} | ✓ | 1.000 |
| P4-001 | positioning | P4 | {"answer": "B"} | {"answer": "B"} | ✓ | 1.000 |
| P4-002 | positioning | P4 | {"answer": "D"} | {"answer": "D"} | ✓ | 1.000 |
| P4-003 | positioning | P4 | {"answer": "B"} | {"answer": "B"} | ✓ | 1.000 |
| P4-004 | positioning | P4 | {"answer": "A"} | {"answer": "A"} | ✓ | 1.000 |
| P4-005 | positioning | P4 | {"answer": "C"} | {"answer": "C"} | ✓ | 1.000 |
| P4-006 | positioning | P4 | {"answer": "B"} | {"answer": "B"} | ✓ | 1.000 |
| P4-007 | positioning | P4 | {"answer": "E"} | {"answer": "E"} | ✓ | 1.000 |
| P5-000 | positioning | P5 | {"answer": "E"} | {"answer": "E"} | ✓ | 1.000 |
| P5-001 | positioning | P5 | {"answer": "A"} | {"answer": "A"} | ✓ | 1.000 |
| P5-002 | positioning | P5 | {"answer": "D"} | {"answer": "D"} | ✓ | 1.000 |
| P5-003 | positioning | P5 | {"answer": "B"} | {"answer": "B"} | ✓ | 1.000 |
| P5-004 | positioning | P5 | {"answer": "B"} | {"answer": "B"} | ✓ | 1.000 |
| P5-005 | positioning | P5 | {"answer": "D"} | {"answer": "B"} | ✗ | 0.000 |
| P5-006 | positioning | P5 | {"answer": "C"} | {"answer": "C"} | ✓ | 1.000 |
| P5-007 | positioning | P5 | {"answer": "A"} | {"answer": "A"} | ✓ | 1.000 |
| R1-000 | rules | R1 | {"answer": ["B", "D", "F"]} | {"answer": ["B", "D", "F"]} | ✓ | 1.000 |
| R1-001 | rules | R1 | {"answer": ["A", "C", "E", "F"]} | {"answer": ["A", "C", "D", "E"]} | ✗ | 0.000 |
| R1-002 | rules | R1 | {"answer": ["D", "F"]} | {"answer": ["D", "F"]} | ✓ | 1.000 |
| R1-003 | rules | R1 | {"answer": ["A", "B", "C", "D", "E", "F"]} | {"answer": ["C", "D", "E", "F"]} | ✗ | 0.000 |
| R1-004 | rules | R1 | {"answer": ["A", "C", "D", "E", "F"]} | {"answer": ["C", "E", "F"]} | ✗ | 0.000 |
| R1-005 | rules | R1 | {"answer": ["B", "C", "E"]} | {"answer": ["B", "C", "E"]} | ✓ | 1.000 |
| R1-006 | rules | R1 | {"answer": ["A", "B", "C", "D", "F"]} | {"answer": ["B", "C", "D", "E", "F"]} | ✗ | 0.000 |
| R1-007 | rules | R1 | {"answer": ["A", "C", "E"]} | {"answer": ["A", "C"]} | ✗ | 0.000 |
| R2-000 | rules | R2 | {"answer": "win"} | {"answer": "win"} | ✓ | 1.000 |
| R2-001 | rules | R2 | {"answer": "tie"} | {"answer": "tie"} | ✓ | 1.000 |
| R2-002 | rules | R2 | {"answer": "loss"} | {"answer": "loss"} | ✓ | 1.000 |
| R2-003 | rules | R2 | {"answer": "win"} | {"answer": "win"} | ✓ | 1.000 |
| R2-004 | rules | R2 | {"answer": "win"} | {"answer": "win"} | ✓ | 1.000 |
| R2-005 | rules | R2 | {"answer": "win"} | {"answer": "win"} | ✓ | 1.000 |
| R2-006 | rules | R2 | {"answer": "win"} | {"answer": "win"} | ✓ | 1.000 |
| R2-007 | rules | R2 | {"answer": "loss"} | {"answer": "loss"} | ✓ | 1.000 |
| R3-000 | rules | R3 | {"answer": [[1, 3], [2, 1], [3, 4], [1, 1], [4, 5]]} | {"answer": [[1, 3], [3, 2], [3, 4], [1, 1], [3, 4]]} | ✗ | 0.000 |
| R3-001 | rules | R3 | {"answer": [[3, 8], [1, 4], [7, 7], [3, 3], [3, 4]]} | {"answer": [[3, 8], [2, 5], [7, 7], [3, 3], [3, 4]]} | ✗ | 0.000 |
| R3-002 | rules | R3 | {"answer": [[4, 5], [3, 2], [8, 8], [2, 8], [3, 4]]} | {"answer": [[4, 5], [4, 3], [8, 8], [3, 9], [3, 4]]} | ✗ | 0.000 |
| R3-003 | rules | R3 | {"answer": [[4, 4], [6, 8], [2, 2], [3, 6], [2, 5]]} | {"answer": [[4, 4], [7, 8], [2, 2], [3, 6], [2, 4]]} | ✗ | 0.000 |
| R3-004 | rules | R3 | {"answer": [[3, 8], [5, 6], [2, 1], [3, 3]]} | {"answer": [[3, 8], [5, 6], [2, 1], [3, 3]]} | ✓ | 1.000 |
| R3-005 | rules | R3 | {"answer": [[5, 6], [6, 6], [4, 4], [4, 8], [3, 4]]} | {"answer": [[6, 7], [6, 6], [4, 4], [4, 8], [3, 4]]} | ✗ | 0.000 |
| R3-006 | rules | R3 | {"answer": [[2, 8], [10, 10], [6, 6], [8, 8], [3, 4]]} | {"answer": [[3, 9], [10, 10], [6, 6], [8, 8], [3, 4]]} | ✗ | 0.000 |
| R3-007 | rules | R3 | {"answer": [[2, 6], [5, 5], [3, 1], [3, 4], [1, 4]]} | {"answer": [[2, 6], [5, 5], [3, 1], [3, 4], [2, 4]]} | ✗ | 0.000 |
| R4-000 | rules | R4 | {"answer": [[2, 2], [5, 4], [3, 7]]} | {"answer": [[1, 2], [5, 4], [3, 7]]} | ✗ | 0.000 |
| R4-001 | rules | R4 | {"answer": [[3, 3], [3, 3], [2, 2]]} | {"answer": [[3, 3], [4, 3], [1, 2]]} | ✗ | 0.000 |
| R4-002 | rules | R4 | {"answer": [[1, 2], [6, 8]]} | {"answer": [[1, 2], [7, 8]]} | ✗ | 0.000 |
| R4-003 | rules | R4 | {"answer": [[6, 8], [3, 4]]} | {"answer": [[6, 8], [3, 4]]} | ✓ | 1.000 |
| R4-004 | rules | R4 | (未答) | {"answer": [[2, 3], [4, 5], [2, 1]]} | ✗ | 0.000 |
| R4-005 | rules | R4 | {"answer": [[2, 3], [4, 4], [3, 5], [4, 4]]} | {"answer": [[2, 3], [4, 4], [3, 5], [4, 4]]} | ✓ | 1.000 |
| R4-006 | rules | R4 | {"answer": [[4, 4], [4, 6], [2, 4], [3, 4], [1, 4]]} | {"answer": [[6, 6], [4, 6], [2, 4], [3, 4], [1, 4]]} | ✗ | 0.000 |
| R4-007 | rules | R4 | {"answer": [[2, 2], [3, 6]]} | {"answer": [[1, 2], [4, 6]]} | ✗ | 0.000 |
| R5-000 | rules | R5 | {"answer": [8, 12]} | {"answer": [15, 15]} | ✗ | 0.000 |
| R5-001 | rules | R5 | {"answer": [8, 8]} | {"answer": [9, 9]} | ✗ | 0.000 |
| R5-002 | rules | R5 | {"answer": [4, 10]} | {"answer": [7, 15]} | ✗ | 0.000 |
| R5-003 | rules | R5 | {"answer": [10, 2]} | {"answer": [16, 6]} | ✗ | 0.000 |
| R5-004 | rules | R5 | {"answer": [2, 2]} | {"answer": [5, 9]} | ✗ | 0.000 |
| R5-005 | rules | R5 | {"answer": [8, 10]} | {"answer": [9, 13]} | ✗ | 0.000 |
| R5-006 | rules | R5 | {"answer": [14, 18]} | {"answer": [14, 19]} | ✗ | 0.000 |
| R5-007 | rules | R5 | {"answer": [8, 6]} | {"answer": [14, 12]} | ✗ | 0.000 |
| R6-000 | rules | R6 | {"answer": [[9, 6], [13, 5]]} | {"answer": [[9, 6], [13, 8]]} | ✗ | 0.000 |
| R6-001 | rules | R6 | {"answer": [[10, 8], [4, 5], [4, 8]]} | {"answer": [[10, 8], [4, 5], [4, 8]]} | ✓ | 1.000 |
| R6-002 | rules | R6 | {"answer": [[8, 7], [3, 6], [3, 2]]} | {"answer": [[8, 7], [3, 6], [3, 2]]} | ✓ | 1.000 |
| R6-003 | rules | R6 | {"answer": [[6, 7], [3, 6], [4, 6]]} | {"answer": [[8, 9], [5, 8], [6, 8]]} | ✗ | 0.000 |
| R6-004 | rules | R6 | {"answer": [[10, 10], [4, 5], [3, 2]]} | {"answer": [[10, 10], [4, 5], [3, 2]]} | ✓ | 1.000 |
| R6-005 | rules | R6 | {"answer": [[7, 7], [10, 10], [7, 15], [8, 8], [6, 5]]} | {"answer": [[22, 22], [25, 25], [22, 30], [23, 23], [21, … | ✗ | 0.000 |
| R6-006 | rules | R6 | {"answer": [[3, 3], [2, 3], [3, 2], [1, 3], [6, 3]]} | {"answer": [[3, 3], [2, 3], [3, 2], [1, 3], [6, 3]]} | ✓ | 1.000 |
| R6-007 | rules | R6 | {"answer": [[20, 20], [3, 4], [4, 4], [1, 3]]} | {"answer": [[20, 20], [3, 4], [4, 4], [1, 3]]} | ✓ | 1.000 |
| R7-000 | rules | R7 | {"answer": [7, 3]} | {"answer": [7, 3]} | ✓ | 1.000 |
| R7-001 | rules | R7 | {"answer": [4, 6]} | {"answer": [4, 6]} | ✓ | 1.000 |
| R7-002 | rules | R7 | {"answer": [7, 6]} | {"answer": [7, 6]} | ✓ | 1.000 |
| R7-003 | rules | R7 | {"answer": [1, 4]} | {"answer": [2, 4]} | ✗ | 0.000 |
| R7-004 | rules | R7 | {"answer": [5, 7]} | {"answer": [5, 7]} | ✓ | 1.000 |
| R7-005 | rules | R7 | {"answer": [3, 7]} | {"answer": [3, 7]} | ✓ | 1.000 |
| R7-006 | rules | R7 | {"answer": [4, 6]} | {"answer": [6, 9]} | ✗ | 0.000 |
| R7-007 | rules | R7 | {"answer": [7, 13]} | {"answer": [7, 13]} | ✓ | 1.000 |
| T1-000 | targets | T1 | {"answer": 3} | {"answer": 3} | ✓ | 1.000 |
| T1-001 | targets | T1 | {"answer": 0} | {"answer": 0} | ✓ | 1.000 |
| T1-002 | targets | T1 | {"answer": 2} | {"answer": 2} | ✓ | 1.000 |
| T1-003 | targets | T1 | {"answer": 4} | {"answer": 4} | ✓ | 1.000 |
| T1-004 | targets | T1 | {"answer": 2} | {"answer": 2} | ✓ | 1.000 |
| T1-005 | targets | T1 | {"answer": 4} | {"answer": 4} | ✓ | 1.000 |
| T1-006 | targets | T1 | {"answer": 0} | {"answer": 0} | ✓ | 1.000 |
| T1-007 | targets | T1 | {"answer": 0} | {"answer": 0} | ✓ | 1.000 |
| T2-000 | targets | T2 | {"answer": 3} | {"answer": 0.4697, "values": {"2": 0.1094, "3": 0.4697, "… | ✓ | 1.000 |
| T2-001 | targets | T2 | {"answer": 2} | {"answer": 0.4414, "values": {"0": 0.1182, "1": 0.1172, "… | ✓ | 1.000 |
| T2-002 | targets | T2 | {"answer": 2} | {"answer": 0.2158, "values": {"1": 0.2158, "2": 0.1719, "… | ✗ | 0.797 |
| T2-003 | targets | T2 | {"answer": 5} | {"answer": 0.6621, "values": {"0": 0.5986, "1": 0.5557, "… | ✓ | 1.000 |
| T2-004 | targets | T2 | {"answer": 2} | {"answer": 0.3936, "values": {"1": 0.2539, "2": 0.3936, "… | ✓ | 1.000 |
| T2-005 | targets | T2 | {"answer": 0} | {"answer": 0.3613, "values": {"0": 0.3613, "1": 0.0557, "… | ✓ | 1.000 |
| T2-006 | targets | T2 | {"answer": 1} | {"answer": 0.4014, "values": {"0": 0.2959, "1": 0.4014, "… | ✓ | 1.000 |
| T2-007 | targets | T2 | {"answer": 1} | {"answer": 0.1768, "values": {"0": 0.0967, "1": 0.1768, "… | ✓ | 1.000 |
| T3-000 | targets | T3 | {"answer": 3} | {"answer": 0.3984, "values": {"0": 0.2998, "1": 0.2412, "… | ✓ | 1.000 |
| T3-001 | targets | T3 | {"answer": 3} | {"answer": 0.5723, "values": {"0": 0.2949, "1": 0.4551, "… | ✓ | 1.000 |
| T3-002 | targets | T3 | {"answer": 2} | {"answer": 1.0, "values": {"0": 0.8672, "1": 0.6113, "2":… | ✓ | 1.000 |
| T3-003 | targets | T3 | {"answer": 3} | {"answer": 0.5605, "values": {"0": 0.418, "1": 0.3066, "2… | ✓ | 1.000 |
| T3-004 | targets | T3 | {"answer": 2} | {"answer": 0.4209, "values": {"0": 0.0859, "1": 0.2363, "… | ✓ | 1.000 |
| T3-005 | targets | T3 | {"answer": 2} | {"answer": 0.2793, "values": {"0": 0.1104, "1": 0.1689, "… | ✓ | 1.000 |
| T3-006 | targets | T3 | {"answer": 4} | {"answer": 0.1191, "values": {"0": 0.0225, "1": 0.0127, "… | ✓ | 1.000 |
| T3-007 | targets | T3 | {"answer": 2} | {"answer": 0.2305, "values": {"0": 0.0957, "1": 0.0186, "… | ✓ | 1.000 |
| T4-000 | targets | T4 | {"answer": 0} | {"answer": 0.708, "values": {"0": 0.708, "2": 0.5996, "3"… | ✓ | 1.000 |
| T4-001 | targets | T4 | {"answer": 2} | {"answer": 0.7031, "values": {"0": 0.3379, "1": 0.3369, "… | ✓ | 1.000 |
| T4-002 | targets | T4 | {"answer": 2} | {"answer": 0.8535, "values": {"1": 0.7617, "2": 0.8535, "… | ✓ | 1.000 |
| T4-003 | targets | T4 | {"answer": 1} | {"answer": 0.1885, "values": {"0": 0.0, "1": 0.1885, "2":… | ✓ | 1.000 |
| T4-004 | targets | T4 | {"answer": 1} | {"answer": 0.9658, "values": {"0": 0.8809, "1": 0.9658, "… | ✓ | 1.000 |
| T4-005 | targets | T4 | {"answer": 1} | {"answer": 1.0, "values": {"0": 0.7402, "1": 1.0, "2": 0.… | ✓ | 1.000 |
| T4-006 | targets | T4 | {"answer": 1} | {"answer": 1.0, "values": {"0": 0.0, "1": 1.0, "2": 0.799… | ✓ | 1.000 |
| T4-007 | targets | T4 | {"answer": 0} | {"answer": 0.5176, "values": {"0": 0.5176, "1": 0.4346, "… | ✓ | 1.000 |
| T5-000 | targets | T5 | {"answer": 2} | {"answer": 0.8213, "values": {"0": 0.2734, "1": 0.2852, "… | ✓ | 1.000 |
| T5-001 | targets | T5 | {"answer": 3} | {"answer": 0.7344, "values": {"0": 0.5254, "1": 0.6113, "… | ✓ | 1.000 |
| T5-002 | targets | T5 | {"answer": 5} | {"answer": 0.7529, "values": {"0": 0.5771, "1": 0.7188, "… | ✓ | 1.000 |
| T5-003 | targets | T5 | {"answer": 6} | {"answer": 0.7705, "values": {"0": 0.583, "1": 0.127, "2"… | ✓ | 1.000 |
| T5-004 | targets | T5 | {"answer": 0} | {"answer": 0.9785, "values": {"0": 0.9785, "1": 0.7324, "… | ✓ | 1.000 |
| T5-005 | targets | T5 | {"answer": 5} | {"answer": 0.9385, "values": {"0": 0.417, "1": 0.8848, "2… | ✓ | 1.000 |
| T5-006 | targets | T5 | {"answer": 1} | {"answer": 0.1572, "values": {"0": 0.0303, "1": 0.1572, "… | ✓ | 1.000 |
| T5-007 | targets | T5 | {"answer": 5} | {"answer": 0.168, "values": {"0": 0.0303, "1": 0.0996, "2… | ✓ | 1.000 |
