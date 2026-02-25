# Vertex Cover 元启发式算法对比（Python）

本项目针对 **Vertex Cover** 问题，仅使用元启发式算法进行系统化比较分析，满足以下要求：
- 三种性质不同的元启发算法：
  - Simulated Annealing (SA)
  - Genetic Algorithm (GA)
  - Ant Colony Optimization (ACO)
- 5 类输入实例，每类 20 个样本（共 100 个实例）
- 所有随机实验重复 5 次，记录平均值与方差
- 指标涵盖：运行时间、解质量（相对匹配下界差距）、稳定性/收敛速度
- 自动导出 CSV 结果与可视化图表到 `result/`（默认依赖见 requirements.txt）

## 1. 问题定义
给定无向图 \(G=(V,E)\)，求最小顶点覆盖集合 \(C \subseteq V\)，使得任意边 \((u,v)\in E\) 至少有一个端点在 \(C\) 中。

### 实际意义
- 网络监控部署（节点监控覆盖通信边）
- 测试点选择（覆盖依赖关系）
- 生物网络干预（覆盖关键相互作用）

## 2. 算法说明（元启发）
### SA（模拟退火）
- 状态：当前顶点集
- 目标：`|C| + penalty * uncovered_edges`
- 邻域：随机增删节点，接受概率随温度下降
- 优点：实现简单，局部跳出能力强
- 瓶颈：温度与惩罚参数对表现敏感

### GA（遗传算法）
- 个体：候选顶点覆盖
- 机制：锦标赛选择 + 交叉 + 变异 + 修复
- 优点：全局搜索能力较好
- 瓶颈：种群规模/代数影响耗时，早熟风险

### ACO（蚁群）
- 由蚂蚁按信息素和启发式（度数/未覆盖贡献）构造解
- 每轮挥发 + 最优个体强化
- 优点：对结构化图有较强构造能力
- 瓶颈：每轮构造成本较高，参数较多

## 3. 理论复杂度（单次运行粗略上界）
设 \(n=|V|, m=|E|\)：
- SA：`O(I * (n + m))`，空间 `O(n+m)`
- GA：`O(G * P * (n + m))`，空间 `O(P*n + m)`
- ACO：`O(T * A * (n + m))`，空间 `O(n + m)`

其中：
- `I` 为 SA 迭代次数
- `G` 为 GA 代数，`P` 为种群大小
- `T` 为 ACO 轮数，`A` 为蚂蚁数

> 项目中质量评估采用相对最大匹配下界的差距（gap to lower bound），并报告均值与方差。

## 4. 输入实例集（5 类）
在 `graph_utils.py` 中构建：
1. `ER_sparse`: Erdős–Rényi 稀疏图
2. `ER_dense`: Erdős–Rényi 稠密图
3. `BA_scale_free`: BA 无标度图
4. `WS_small_world`: WS 小世界图
5. `Grid_structured`: 规则网格图

每类 20 个实例，共 100 个。

## 5. 运行方法
```bash
pip install -r requirements.txt
python experiment.py
python analysis.py
# 快速验证
python experiment.py --samples-per-group 2 --runs 2
```

输出文件在 `result/`：
- `raw_runs.csv`：每次重复实验的原始数据
- `summary.csv`：按算法与实例类别聚合后的均值/方差
- `bar_time_mean.png` / `bar_cover_mean.png` / `bar_gap_mean.png`（本地运行生成，不纳入仓库）
- `trend_time_vs_edges.png`（本地运行生成，不纳入仓库）

## 6. 目录结构
```text
.
├── README.md
├── algorithms.py
├── graph_utils.py
├── experiment.py
├── analysis.py
└── result/
```

## 7. 可扩展建议
- 增加显著性检验（t-test / Wilcoxon）
- 加入置信区间与误差带可视化
- 建立性能预测模型（回归拟合时间-规模关系）
- 对大规模图接入并行策略
