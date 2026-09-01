# 示例数据

## 五时点纵向追踪

文件：`data/longitudinal-panel-demo.csv`

- 180 名被试，T1—T5 五个波次；
- `subject_id` 是被试标识；
- `x1/y1` 至 `x5/y5` 是可直接映射的构念得分；
- `x_t1_i1` 等列是每个构念、每个波次的三道示例题项。

在实证中心的“纵向追踪分析”中选择 RI-CLPM，并依次映射：

| 波次 | X | Y |
|---|---|---|
| T1 | x1 | y1 |
| T2 | x2 | y2 |
| T3 | x3 | y3 |
| T4 | x4 | y4 |
| T5 | x5 | y5 |

题项级潜变量模式下，先把十组题项分别建立为 `X_T1`—`X_T5` 与
`Y_T1`—`Y_T5` 测量构念，再按波次映射。五波均映射后可运行线性或
二次 LCM-SR；请求标量/严格等值后可另行运行 ULMC 敏感性。连续题项可用 MLR/FIML；
若实际数据是有序题项，应选择 WLSMV/完整案例并检查阈值等值性。
可选的 RI-CLPM 功效分析使用研究者事前提供的最小重要效应、ICC、
信度和候选样本量；示例默认值只用于演示，不能直接作为投稿依据。

## 日记研究

文件：`data/daily-diary-demo.csv`

- 80 名被试，每人 10 天，共 800 行；
- `person_id` 是被试标识，`day` 是时间变量；
- `daily_stress`、`daily_recovery`、`daily_engagement` 分别可作为 X、M、Y；
- `intervention` 和 `age` 是被试层变量；
- 每个日水平构念另含两道示例题项。
- `purchase` 为 0/1 购买结局，`aigc_clicks` 为计数结局，`scenario` 为交叉分类场景，
  `exposure_minutes` 可作为计数模型的暴露量 offset。

基础 LMM 推荐配置：

- X：`daily_stress`
- Y：`daily_engagement`
- 中心化：人均中心化
- 时间原点：首日或研究设计中的明确零点
- 二次趋势：与线性项共同进入，并查看联合 Wald 检验
- 随机斜率：开启
- 时间残差：可分别运行独立残差与 AR(1) 作为敏感性比较
- 时间效应：可分别运行同时效应、滞后效应或两者并列
- 功效设计：按事前效应和方差设定比较“人数 × 每人测量次数”

1-1-1 多层中介配置：

- X：`daily_stress`
- M：`daily_recovery`
- Y：`daily_engagement`

两个文件均由 `scripts/generate-method-demo-data.py` 使用固定随机种子生成，可重复构建。
示例数据的依从率为 100%，因此主要用于验证模型执行；正式 ESM 数据应包含
计划提示数、实际响应和响应延迟列，才能形成依从性与有效窗口证据。

## 密集纵向与 GLMM/交叉分类

文件：`data/intensive-esm-demo.csv`

- 30 名被试、每人 25 个等间隔时点；
- `emotion` 与 `ai_trust` 可作为 Bayesian DSEM 的双向连续变量；
- `purchase` 可运行 binomial-logit GLMM；
- `aigc_clicks` 可运行 Poisson/负二项 GLMM；需要演示零膨胀或 Hurdle 时，应按理论明确选择计数过程，平台不会因零值比例自动换模；
- `scenario` 有五个交叉场景，可与被试同时作为随机截距；
- `exposure_minutes` 演示非等暴露量计数模型 offset。

Bayesian DSEM 示例使用 CWC、滞后一阶、至少两条链，并同时检查
rank-normalized/folded R-hat、bulk/tail ESS、MCSE、先验/后验预测检验和
自回归平稳性。短迭代只用于工程演示；正式研究应提高迭代数、检查迹线/
后验分布，并完成先验敏感性分析。
